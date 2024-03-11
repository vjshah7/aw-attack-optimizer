import logging
import json


class DefenderCounterConfig:
    _data: dict[int, list]

    def __init__(self, valid_counters: dict[int, list] = None):
        if valid_counters:
            self._data = valid_counters
        else:
            self._data = {}

    def add_counters(self, node_id: int, counters: list):
        if node_id in self._data.keys():
            logging.error("Already have data for node {}".format(node_id))
            raise ValueError("Duplicate node id")

        self._data[node_id] = counters

    def get_node_ids(self) -> list:
        return list(self._data.keys())

    def get_node_counters(self, node_id: int) -> list:
        if node_id not in self._data.keys():
            logging.error("No such node id {}".format(node_id))
            raise ValueError("Unknown node id")

        return self._data[node_id].copy()


def load_counters_from_file(filename: str) -> DefenderCounterConfig:
    defender_counter_config = DefenderCounterConfig()
    with open(filename) as f:
        json_data = json.load(f)

    counter_data = json_data['defender_counters']
    for counter_entry in counter_data:
        node_id = int(counter_entry['node_id'])
        counter_list = counter_entry['counters']
        defender_counter_config.add_counters(node_id, counter_list)

    return defender_counter_config


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(levelname)-8s %(funcName)s:%(message)s',
                        level=logging.INFO,
                        datefmt='%Y-%m-%d %H:%M:%S')

    dcc = load_counters_from_file('defendercounter-1.json')
    for node in dcc.get_node_ids():
        print("node {}: {}".format(node, dcc.get_node_counters(node)))
