import logging
import json
from redis import StrictRedis
from d3a_interface.utils import wait_until_timeout_blocking


class RedisMarketClient:
    def __init__(self, area_id, redis_url='redis://localhost:6379'):
        self.area_id = area_id
        self.redis_db = StrictRedis.from_url(redis_url)
        self.pubsub = self.redis_db.pubsub()
        self._subscribe_to_response_channels()
        self._blocking_command_responses = {}

    def _generate_command_response_callback(self, command_type):
        def _command_received(msg):
            try:
                message = json.loads(msg["data"])
            except Exception as e:
                logging.error(f"Received incorrect response on command {command_type}. "
                              f"Response {msg}. Error {e}.")
                return
            logging.debug(f"Command {command_type} received response: {message}")
            if 'error' in message:
                logging.error(f"Error when receiving {command_type} command response."
                              f"Error output: {message}" )
                return
            else:
                self._blocking_command_responses[command_type] = message
        return _command_received

    @property
    def _market_stats_channel(self):
        return f"market_stats/{self.area_id}"

    def _subscribe_to_response_channels(self):
        channel_subs = {f"{self._market_stats_channel}/response":
                        self._generate_command_response_callback("list_market_stats")}
        self.pubsub.subscribe(**channel_subs)
        self.pubsub.run_in_thread(daemon=True)

    def _wait_and_consume_command_response(self, command_type):
        logging.info(f"Command {command_type} waiting for response...")
        wait_until_timeout_blocking(lambda: command_type in self._blocking_command_responses, timeout=120)
        command_output = self._blocking_command_responses.pop(command_type)
        logging.info(f"Command {command_type} got response {command_output}")
        return command_output

    def list_market_stats(self, market_slot_list):
        logging.debug(f"Client tries to read market_stats.")
        self.redis_db.publish(self._market_stats_channel, json.dumps({"market_slots": market_slot_list}))
        return self._wait_and_consume_command_response("list_market_stats")