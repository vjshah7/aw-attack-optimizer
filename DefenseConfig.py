import logging
import json


class SectionConfig:
    _nodes: list
    _sequence_num: int
    _side_num: int

    def __init__(self, nodes: list, sequence_num: int, side_num: int = -1):
        self._nodes = nodes
        self._sequence_num = sequence_num
        self._side_num = side_num

    def get_nodes(self) -> list:
        return self._nodes.copy()

    def get_sequence_num(self) -> int:
        return self._sequence_num

    def get_side_num(self) -> int:
        return self._side_num


def is_valid_side_num(side_num: int) -> bool:
    return side_num >= 0


class DefenseConfig:
    _data: dict[str, SectionConfig]

    def __init__(self, config_data: dict[str, SectionConfig] = None):
        if config_data:
            self._data = config_data
        else:
            self._data = {}

    def add_section(self, section_name: str, section_config: SectionConfig):
        if section_name in self._data:
            logging.error("Already have a section named {}".format(section_name))
            raise ValueError("Duplicate section name")

        self._data[section_name] = section_config

    def get_all_sections(self) -> list:
        return list(self._data.keys())

    def get_section(self, section_name: str) -> SectionConfig:
        if section_name not in self._data:
            logging.error("No section found named {}".format(section_name))
            raise ValueError("Unknown section name")

        return self._data[section_name]


def load_defense_config_from_file(filename: str) -> DefenseConfig:
    defense_config = DefenseConfig()
    with open(filename) as f:
        json_data = json.load(f)

    for section_name in json_data:
        nodes = json_data[section_name]['nodes']
        sequence_num = json_data[section_name]['sequence_num']
        if 'side_num' in json_data[section_name]:
            side_num = json_data[section_name]['side_num']
            defense_config.add_section(section_name, SectionConfig(nodes, sequence_num, side_num))
        else:
            defense_config.add_section(section_name, SectionConfig(nodes, sequence_num))

    return defense_config


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(levelname)-8s %(funcName)s:%(message)s',
                        level=logging.INFO,
                        datefmt='%Y-%m-%d %H:%M:%S')

    for fname in ["dc-1.json", "dc-2.json"]:
        print("file {}".format(fname))
        print("")
        dc = load_defense_config_from_file(fname)
        for sn in dc.get_all_sections():
            print("section name: {}".format(sn))
            s = dc.get_section(sn)
            print("nodes: {}".format(s.get_nodes()))
            print("sequence num: {}".format(s.get_sequence_num()))
            print("side num: {}".format(s.get_side_num()))
            print("")
        print("")
