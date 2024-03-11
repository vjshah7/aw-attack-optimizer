import logging


class AWConfig:
    _num_champions: int
    _num_rosters: int
    _team_size: int

    def __init__(self, num_champions: int, num_rosters: int = 10, team_size: int = 3):
        self._num_champions = num_champions
        self._num_rosters = num_rosters
        self._team_size = team_size

    def get_num_champions(self) -> int:
        return self._num_champions

    def get_all_champions(self) -> list:
        return list(range(1, self._num_champions + 1))

    def get_num_rosters(self) -> int:
        return self._num_rosters

    def get_team_size(self) -> int:
        return self._team_size


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(levelname)-8s %(funcName)s:%(message)s',
                        level=logging.INFO,
                        datefmt='%Y-%m-%d %H:%M:%S')

    aw_config = AWConfig(10, 2, 3)
    print("aw config: num champs: {}, num rosters: {}, team size: {}\n".format(
        aw_config.get_num_champions(), aw_config.get_num_rosters(), aw_config.get_team_size()))
