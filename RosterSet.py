import logging
import json


class RosterSet:
    _roster_data: list

    def __init__(self, roster_data: list = None):
        if roster_data:
            self._roster_data = roster_data
        else:
            self._roster_data = []

    def get_all_roster_ids(self) -> list:
        return list(range(len(self._roster_data)))

    def get_roster(self, roster_id: int) -> list:
        if roster_id not in range(len(self._roster_data)):
            logging.error("invalid roster id {}".format(roster_id))
            raise ValueError("unknown roster id")

        return self._roster_data[roster_id].copy()

    def add_roster(self, champs: list):
        self._roster_data.append(champs)


def load_roster_set_from_file(filename: str) -> RosterSet:
    roster_set = RosterSet()
    with open(filename) as f:
        json_data = json.load(f)

    for roster in json_data['rosters']:
        roster_set.add_roster(roster)

    return roster_set


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(levelname)-8s %(funcName)s:%(message)s',
                        level=logging.INFO,
                        datefmt='%Y-%m-%d %H:%M:%S')

    test_roster_data = [
        [2, 11, 26, 28, 31, 35, 36, 37, 41, 49, 65, 85, 87, 89, 92, 97, 103],
        [2, 10, 11, 23, 24, 25, 36, 59, 82, 97, 98, 104, 120, 128, 132, 135],
        [9, 10, 11, 14, 17, 40, 42, 44, 46, 51, 55, 56, 58, 70, 86, 94, 101]
    ]
    rs = RosterSet(test_roster_data)
    print("roster ids: {}".format(rs.get_all_roster_ids()))
    for r in rs.get_all_roster_ids():
        print("roster {}: {}".format(r, rs.get_roster(r)))

    print("adding new roster")
    rs.add_roster([5, 6, 12, 14, 17, 23, 26, 32, 38, 39, 47, 51, 55, 56, 60, 76, 79, 80, 83])
    print("new roster contents: {}".format(rs.get_roster(3)))

    rs2 = load_roster_set_from_file("rosterset-1.json")
    print("imported rosterset:")
    for r in rs2.get_all_roster_ids():
        print("roster {}: {}".format(r, rs2.get_roster(r)))
