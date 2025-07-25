from zsim.sim_progress.Preload import SkillNode

from .character import Character
from .utils.filters import _skill_node_filter


class Qingyi(Character):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.__MAX_VOLTAGE: int = 10000
        self.__QUAN_VOLTAGE: float = (
            self.__MAX_VOLTAGE / 100 * (1.3 if self.cinema >= 1 else 1)
        )
        self.__FLASH_THRESHOLD: float = self.__MAX_VOLTAGE * 0.75
        self.VOLTAGE_MAP: dict = {
            "1251_NA_3_NFC": self.__QUAN_VOLTAGE * 4.6875,
            "1251_NA_3_FC": self.__QUAN_VOLTAGE * 4.6875 * 16,
            "1251_SNA": self.__QUAN_VOLTAGE * 1.94,
            "1251_NA_4": self.__QUAN_VOLTAGE * 7.7,
            "1251_CA": self.__QUAN_VOLTAGE * 16.08,
            "1251_BH_Aid": self.__QUAN_VOLTAGE * 6.08,
            "1251_Assault_Aid": self.__QUAN_VOLTAGE * 14.89,
            "1251_E": self.__QUAN_VOLTAGE * 2.83,
            "1251_E_EX_NFC": self.__QUAN_VOLTAGE * 22.29,
            "1251_E_EX_FC": self.__QUAN_VOLTAGE * 30,
            "1251_QTE": self.__QUAN_VOLTAGE * 25,
            "1251_Q": self.__QUAN_VOLTAGE * 80,
        }

        self.flash_connect_voltage: int = (
            0 if self.cinema == 0 else self.__MAX_VOLTAGE
        )  # 闪络电压，初始化为0
        self.flash_connect: bool = False if self.cinema == 0 else True  # 闪络状态
        self.rush_attack_available_times: int = 5  # 醉花月云转-突进攻击可用次数

    def special_resources(self, *args, **kwargs) -> None:
        """模拟青衣的闪络电压机制"""
        skill_nodes: list[SkillNode] = _skill_node_filter(*args, **kwargs)
        for node in skill_nodes:
            # 闪络电压增加逻辑
            if self.flash_connect_voltage < self.__MAX_VOLTAGE:
                skill_tag = node.skill_tag
                self.flash_connect_voltage += self.VOLTAGE_MAP.get(skill_tag, 0)
            # 闪络电压不能超过最大值
            self.flash_connect_voltage = min(
                self.flash_connect_voltage, self.__MAX_VOLTAGE
            )
            # 闪络电压超过75%时，进入闪络状态
            if self.flash_connect_voltage - self.__FLASH_THRESHOLD >= 1e-5:
                self.flash_connect = True
                self.rush_attack_available_times = 5
            if self.flash_connect:
                # 闪络状态执行逻辑
                if node.skill_tag == "1251_SNA_1":
                    self.flash_connect_voltage = 0
                    self.rush_attack_available_times -= 1
                    self.flash_connect = False
            else:
                # 非闪络状态执行逻辑
                if node.skill_tag == "1251_SNA_1":
                    # 醉花月云转-突进攻击可用次数减一
                    if self.rush_attack_available_times in [0, 5]:
                        print(
                            f"WTF APL is doing? rush_attack_available_times is {self.rush_attack_available_times}"
                        )
                    self.rush_attack_available_times -= 1

    def get_resources(self, *args, **kwargs) -> tuple[str, float]:
        result = self.flash_connect_voltage / self.__MAX_VOLTAGE * 100
        return "闪络电压", result

    def get_special_stats(self, *args, **kwargs) -> dict[str | None, object | None]:
        return {
            "闪络电压": self.flash_connect_voltage / self.__MAX_VOLTAGE,  # 返回一个比例
            "闪络状态": self.flash_connect,
            "醉花月云转可用次数": self.rush_attack_available_times,
        }
