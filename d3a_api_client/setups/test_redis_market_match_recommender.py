import logging
import json
from time import sleep
from d3a_api_client.redis_aggregator import RedisAggregator
from d3a_api_client.redis_market import RedisMarketClient

FLOATING_POINT_TOLERANCE = 0.00001


class AutoRecomendation(RedisAggregator):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_finished = False
        self.fee_cents_per_kwh = 0

    def on_tick(self, tick_info):
        print(f'tick_info_area_uuid: {tick_info}')
        print(f'self.device_uuid_list: {self.device_uuid_list}')
        for content in tick_info["content"]:
            print(f'--KEYS-- {content["id"]}')
            # if content["id"] not in self.device_uuid_list:
            #     continue
            # print(f'--BIDS--: {content["bids"]}')
            # print(f'--OFFERS--: {content["offers"]}')
            offer_list = content["offers"]['offers']
            sorted_offers = sorted(offer_list, key=lambda x: x['energy_rate'])
            # print(f'sorted_offers: {sorted_offers}')
            bid_list = content["bids"]["bids"]
            sorted_bids = sorted(bid_list, key=lambda x: x['energy_rate'], reverse=True)
            # print(f'sorted_bids: {sorted_bids}')

            already_selected_bids = set()
            offer_bid_pairs = []
            for offer in sorted_offers:
                for bid in sorted_bids:
                    if bid['id'] not in already_selected_bids and \
                            (offer['energy_rate'] - bid['energy_rate']) <= \
                            FLOATING_POINT_TOLERANCE and offer['seller'] != bid['buyer']:
                        already_selected_bids.add(bid['id'])
                        offer_bid_pairs.append(tuple((bid, offer)))
                        break

            print(f'offer_bid_pairs: {offer_bid_pairs}')

            self.add_to_batch_commands.match_recommend(content['area_uuid'], offer_bid_pairs)

        self.execute_batch_commands()
            # self.redis_db.publish(f'{}/list_stocks', json.dumps(offer_bid_pairs))


aggregator = AutoRecomendation(aggregator_name="market_recommendation_aggregator")
print(f'aggregator: {aggregator}')

house_2 = RedisMarketClient("house-2")
selected = house_2.select_aggregator(aggregator.aggregator_uuid, is_blocking=True)
print(f"SELECTED: {selected}")

while not aggregator.is_finished:
    sleep(0.5)
