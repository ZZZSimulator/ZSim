from dataclasses import dataclass
from .AnomalyBarClass import AnomalyBar


@dataclass
class PhysicalAnomaly(AnomalyBar):
    def __post_init__(self):
        super().__post_init__()
        self.element_type = 0
        self.accompany_debuff = ["Buff-异常-畏缩"]
        self.max_duration = 0
        self.duration_buff_list = ["Buff-角色-简-核心被动-啮咬触发器"]
        self.basic_max_duration = 600
        self.duration_buff_key_list = [
            "畏缩时间延长",
            "所有异常时间延长",
            "畏缩时间延长百分比",
            "所有异常时间延长百分比",
        ]


@dataclass
class FireAnomaly(AnomalyBar):
    def __post_init__(self):
        super().__post_init__()  # 调用父类的初始化方法
        self.accompany_dot = "灼烧"
        self.element_type = 1  # 火属性
        self.basic_max_duration = 600
        self.duration_buff_list = ["Buff-角色-柏妮思-组队被动-延长灼烧"]
        self.max_duration = 0
        self.duration_buff_key_list = [
            "灼烧时间延长",
            "所有异常时间延长",
            "灼烧时间延长百分比",
            "所有异常时间延长百分比",
        ]


@dataclass
class IceAnomaly(AnomalyBar):
    def __post_init__(self):
        super().__post_init__()  # 调用父类的初始化方法
        self.element_type = 2  # 冰属性
        self.accompany_debuff = ["Buff-异常-霜寒"]
        self.accompany_dot = "冻结"
        self.basic_max_duration = 600
        self.max_duration = 0
        self.duration_buff_key_list = [
            "霜寒时间延长",
            "所有异常时间延长",
            "霜寒时间延长百分比",
            "所有异常时间延长百分比",
        ]
        # 冻结时间可以延长失衡


@dataclass
class ElectricAnomaly(AnomalyBar):
    def __post_init__(self):
        super().__post_init__()  # 调用父类的初始化方法
        self.element_type = 3  # 电属性
        self.accompany_dot = "感电"
        self.basic_max_duration = 600
        self.duration_buff_list = ["Buff-角色-丽娜-组队被动-延长感电"]
        self.max_duration = 0
        self.duration_buff_key_list = [
            "感电时间延长",
            "所有异常时间延长",
            "感电时间延长百分比",
            "所有异常时间延长百分比",
        ]


@dataclass
class EtherAnomaly(AnomalyBar):
    def __post_init__(self):
        super().__post_init__()  # 调用父类的初始化方法
        self.element_type = 4  # 以太属性
        self.accompany_dot = "侵蚀"
        self.basic_max_duration = 600
        self.max_duration = 0
        self.duration_buff_key_list = [
            "侵蚀时间延长",
            "所有异常时间延长",
            "侵蚀时间延长百分比",
            "所有异常时间延长百分比",
        ]


@dataclass
class FrostAnomaly(AnomalyBar):
    def __post_init__(self):
        super().__post_init__()  # 调用父类的初始化方法
        self.element_type = 5  # 烈霜属性（星见雅专属）
        self.accompany_dot = "冻结"
        self.basic_max_duration = 1200
        self.accompany_debuff = ["Buff-异常-烈霜霜寒", "Buff-角色-雅-核心被动-霜灼"]
        self.max_duration = 0
        self.duration_buff_key_list = [
            "烈霜霜寒时间延长",
            "所有异常时间延长",
            "烈霜霜寒时间延长百分比",
            "所有异常时间延长百分比",
        ]


@dataclass
class AuricInkAnomaly(AnomalyBar):
    def __post_init__(self):
        super().__post_init__()  # 调用父类的初始化方法
        self.element_type = 6  # 玄墨侵蚀的属性也是以太
        self.accompany_dot = "玄墨侵蚀"
        self.basic_max_duration = 600
        self.max_duration = 0
        self.duration_buff_key_list = [
            "玄墨侵蚀时间延长",
            "所有异常时间延长",
            "玄墨侵蚀时间延长百分比",
            "所有异常时间延长百分比",
        ]
