from zsim.sim_progress.Character.character import Character
from abc import ABC, abstractmethod


class Summons(ABC):
    @abstractmethod
    def __init__(self, ownner_obj: Character):
        """召唤物基类"""
        self.owner: Character = ownner_obj
        self.sim_instance = None

    @abstractmethod
    def check_myself(self):
        pass

    @abstractmethod
    def active(self):
        pass
