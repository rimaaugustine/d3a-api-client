import json
import logging
import traceback

from integration_tests.test_aggregator_base import TestAggregatorBase
from d3a_api_client.redis_device import RedisDeviceClient
from d3a_api_client.redis_market import RedisMarketClient


class BatchAggregator(TestAggregatorBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.updated_house2_grid_fee_cents_kwh = 5
        self.updated_offer_bid_price = 60
        self.events_or_responses = set()

    def _setup(self):
        load = RedisDeviceClient('load')
        pv = RedisDeviceClient('pv')

        load.select_aggregator(self.aggregator_uuid)
        pv.select_aggregator(self.aggregator_uuid)

        self.redis_market = RedisMarketClient('house-2')
        self.redis_market.select_aggregator(self.aggregator_uuid)

    def on_market_cycle(self, market_info):
        logging.info(f"market_info: {market_info}")
        try:

            for area_uuid, area_dict in self.latest_grid_tree_flat.items():
                if area_uuid == self.redis_market.area_uuid:
                    self.add_to_batch_commands.grid_fees(area_uuid=self.redis_market.area_uuid,
                                                         fee_cents_kwh=self.updated_house2_grid_fee_cents_kwh)
                    self.add_to_batch_commands.last_market_dso_stats(self.redis_market.area_uuid)
                if not area_dict.get("asset_info"):
                    continue
                asset_info = area_dict["asset_info"]
                if self._can_place_offer(asset_info):
                    self.add_to_batch_commands.offer_energy(
                        area_uuid=area_uuid,
                        price=1.1,
                        energy=asset_info['available_energy_kWh'] / 4,
                        replace_existing=False
                    ).offer_energy(
                        area_uuid=area_uuid,
                        price=2.2,
                        energy=asset_info['available_energy_kWh'] / 4,
                        replace_existing=False
                    ).offer_energy(
                        area_uuid=area_uuid,
                        price=3.3,
                        energy=asset_info['available_energy_kWh'] / 4,
                        replace_existing=True
                    ).offer_energy(
                        area_uuid=area_uuid,
                        price=4.4,
                        energy=asset_info['available_energy_kWh'] / 4,
                        replace_existing=False
                    ).list_offers(area_uuid=area_uuid)

                if self._can_place_bid(asset_info):
                    self.add_to_batch_commands.bid_energy(
                        area_uuid=area_uuid,
                        price=27,
                        energy=asset_info['energy_requirement_kWh'] / 4,
                        replace_existing=False
                    ).bid_energy(
                        area_uuid=area_uuid,
                        price=28,
                        energy=asset_info['energy_requirement_kWh'] / 4,
                        replace_existing=False
                    ).bid_energy(
                        area_uuid=area_uuid,
                        price=29,
                        energy=asset_info['energy_requirement_kWh'] / 4,
                        replace_existing=True
                    ).bid_energy(
                        area_uuid=area_uuid,
                        price=30,
                        energy=asset_info['energy_requirement_kWh'] / 4,
                        replace_existing=False
                    ).list_bids(
                        area_uuid=area_uuid)

            if self.commands_buffer_length:
                transaction = self.execute_batch_commands()
                if transaction is None:
                    self.errors += 1
                else:
                    for response in transaction["responses"].values():
                        for command_dict in response:
                            if command_dict["status"] == "error":
                                self.errors += 1
                logging.info(f"Batch command placed on the new market")

                # Make assertions about the bids, if they happened during this slot
                bid_requests = self._filter_commands_from_responses(
                    transaction['responses'], 'bid')
                if bid_requests:
                    # All bids in the batch have been issued
                    assert len(bid_requests) == 4
                    # All bids have been successfully received and processed
                    assert all(bid.get('status') == 'ready' for bid in bid_requests)

                    list_bids_requests = self._filter_commands_from_responses(
                        transaction['responses'], 'list_bids')

                    # The list_bids command has been issued once
                    assert len(list_bids_requests) == 1

                    # The bid list only contains two bids (the other two have been deleted)
                    current_bids = list_bids_requests[0]['bid_list']
                    assert len(current_bids) == 2

                    issued_bids = [json.loads(bid_request['bid']) for bid_request in bid_requests]

                    # The bids have been issued in the correct order
                    assert [
                               bid['original_bid_price'] for bid in issued_bids
                           ] == [27, 28, 29, 30]

                    # The only two bids left are the last ones that have been issued
                    assert [bid['id'] for bid in current_bids] == \
                           [bid['id'] for bid in issued_bids[-2:]]

                    self._has_tested_bids = True

                # Make assertions about the offers, if they happened during this slot
                offer_requests = self._filter_commands_from_responses(
                    transaction['responses'], 'offer')
                if offer_requests:
                    # All offers in the batch have been issued
                    assert len(offer_requests) == 4
                    # All offers have been successfully received and processed
                    assert all(offer.get('status') == 'ready' for offer in offer_requests)

                    list_offers_requests = self._filter_commands_from_responses(
                        transaction['responses'], 'list_offers')

                    # The list_offers command has been issued once
                    assert len(list_offers_requests) == 1

                    # The offers list only contains two offers (the other two have been deleted)
                    current_offers = list_offers_requests[0]['offer_list']
                    assert len(current_offers) == 2

                    issued_offers = [
                        json.loads(offer_request['offer']) for offer_request in offer_requests]

                    # The offers have been issued in the correct order
                    assert [
                               offer['original_offer_price'] for offer in issued_offers
                           ] == [1.1, 2.2, 3.3, 4.4]

                    # The only two offers left are the last ones that have been issued
                    assert [offer['id'] for offer in current_offers] == \
                           [offer['id'] for offer in issued_offers[-2:]]

                    self._has_tested_offers = True

        except Exception as ex:
            logging.error(f'Raised exception: {ex}. Traceback: {traceback.format_exc()}')
            self.errors += 1

    def on_event_or_response(self, message):
        if "event" in message:
            self.events_or_responses.add(message["event"])
        if "command" in message:
            self.events_or_responses.add(message["command"])
