import logging
from time import sleep

from d3a_interface.utils import key_in_dict_and_not_none_and_greater_than_zero

from d3a_api_client.aggregator import Aggregator
from d3a_api_client.rest_device import RestDeviceClient
from d3a_api_client.rest_market import RestMarketClient
from d3a_api_client.utils import get_area_uuid_from_area_name_and_collaboration_id, \
    get_sim_id_and_domain_names


class TestAggregator(Aggregator):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_finished = False

    def on_market_cycle(self, market_info):
        """
        Places a bid or an offer whenever a new market is created. The amount of energy
        for the bid/offer depends on the available energy of the PV, or on the required
        energy of the load.
        :param market_info: Incoming message containing the newly-created market info
        :return: None
        """
        if self.is_finished is True:
            return

        market_uuid = self.get_uuid_from_area_name("House")
        for area_uuid, area_dict in self.latest_grid_tree_flat.items():
            logging.info(
                f"current_market_fee: "
                f"{self.grid_fee_calculation.calculate_grid_fee(area_uuid, market_uuid)}")
            if not area_dict.get("asset_info"):
                if area_uuid == market_uuid:
                    self.add_to_batch_commands.last_market_dso_stats(area_uuid=area_uuid). \
                        grid_fees(area_uuid=area_uuid, fee_cents_kwh=5)
            else:
                if key_in_dict_and_not_none_and_greater_than_zero(area_dict["asset_info"],
                                                                  "available_energy_kWh"):
                    energy = area_dict["asset_info"]["available_energy_kWh"] / 2
                    self.add_to_batch_commands.offer_energy(area_uuid=area_uuid, price=1,
                                                            energy=energy)

                if key_in_dict_and_not_none_and_greater_than_zero(area_dict["asset_info"],
                                                                  "energy_requirement_kWh"):
                    energy = area_dict["asset_info"]["energy_requirement_kWh"] / 2
                    self.add_to_batch_commands.bid_energy(area_uuid=area_uuid, price=30,
                                                          energy=energy)

        response = self.execute_batch_commands()
        logging.info(f"Batch command placed on the new market: {response}")

    def on_tick(self, tick_info):
        logging.debug(f'Progress information on the device: {tick_info}')

    def on_trade(self, trade_info):
        logging.debug(f'Trade info: {trade_info}')

    def on_finish(self, finish_info):
        self.is_finished = True


simulation_id, domain_name, websockets_domain_name = get_sim_id_and_domain_names()

aggr = TestAggregator(aggregator_name='test_aggr')

load1_uuid = get_area_uuid_from_area_name_and_collaboration_id(
    simulation_id, 'Load', domain_name)
load1 = RestDeviceClient(load1_uuid)

pv1_uuid = get_area_uuid_from_area_name_and_collaboration_id(
    simulation_id, 'PV', domain_name)
pv1 = RestDeviceClient(pv1_uuid)

load1.select_aggregator(aggr.aggregator_uuid)
pv1.select_aggregator(aggr.aggregator_uuid)

house_uuid = get_area_uuid_from_area_name_and_collaboration_id(
    simulation_id, "House", domain_name)
house_market = RestMarketClient(house_uuid)
house_market.select_aggregator(aggr.aggregator_uuid)

while not aggr.is_finished:
    sleep(0.5)
