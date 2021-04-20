from enum import Enum


class Commands(Enum):
    OFFER = 1
    BID = 2
    DELETE_OFFER = 3
    DELETE_BID = 4
    LIST_OFFERS = 5
    LIST_BIDS = 6
    DEVICE_INFO = 7
    UPDATE_OFFER = 8
    UPDATE_BID = 9
    GRID_FEES = 10
    MARKET_STATS = 11
    DSO_MARKET_STATS = 12
    MATCH_RECOMMEND = 13


command_enum_to_command_name_dict = {
    Commands.OFFER: "offer",
    Commands.UPDATE_OFFER: "update_offer",
    Commands.BID: "bid",
    Commands.UPDATE_BID: "update_bid",
    Commands.DELETE_OFFER: "delete_offer",
    Commands.DELETE_BID: "delete_bid",
    Commands.LIST_OFFERS: "list_offers",
    Commands.LIST_BIDS: "list_bids",
    Commands.DEVICE_INFO: "device_info",
    Commands.GRID_FEES: "grid_fees",
    Commands.MARKET_STATS: "market_stats",
    Commands.DSO_MARKET_STATS: "dso_market_stats",
    Commands.MATCH_RECOMMEND: "match_recommend"
}


def command_enum_to_command_name(command: Commands) -> str:
    return command_enum_to_command_name_dict[command]
