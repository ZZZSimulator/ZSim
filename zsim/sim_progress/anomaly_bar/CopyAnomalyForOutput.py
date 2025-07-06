import uuid
from typing import TYPE_CHECKING

from .AnomalyBarClass import AnomalyBar

if TYPE_CHECKING:
    from zsim.simulator.simulator_class import Simulator


class Disorder(AnomalyBar):
    """
    紊乱类，当这个类被创建，将会在__init__方法中自动调用__dict__方法，立刻复制父类的所有状态。
    注意，语法上，在创建Disorder实例时，需要在括号里传入需要复制的父类实例。
    Disorder会打开自身的is_disorder
    """

    def __init__(self, Output_bar: AnomalyBar, sim_instance: "Simulator", **kwargs):
        super().__init__(sim_instance=sim_instance)
        self.__dict__.update(Output_bar.__dict__)
        self.sim_instance = sim_instance
        self.is_disorder = True
        activate_by = kwargs.get("active_by", None)
        self.activate_by = activate_by
        # 复制父类的所有属性，主要是快照、积蓄总值、属性类型。
        self.source_uuid = self.UUID
        self.UUID = uuid.uuid4()

    def __hash__(self):
        """使对象可哈希"""
        return hash(self.UUID)


class NewAnomaly(AnomalyBar):
    """
    普通的异常类，仅用于非紊乱的属性异常更新。
    """

    def __init__(self, Output_bar: AnomalyBar, active_by, sim_instance: "Simulator"):
        super().__init__(sim_instance=sim_instance)
        self.__dict__.update(Output_bar.__dict__)
        self.sim_instance = sim_instance
        self.activate_by = active_by
        self.source_uuid = self.UUID
        self.UUID = uuid.uuid4()

    def __hash__(self):
        """使对象可哈希"""
        return hash(self.UUID)


class PolarityDisorder(Disorder):
    """
    柳的极性紊乱（不含核心被动的紊乱基础倍率增加）
    极性紊乱的计算公式为：
    极性紊乱伤害 = 紊乱伤害 * 本次极性紊乱倍率（解锁2命后可变）+ 附加3200% * 精通的伤害
    构造时，不仅需要提供被复制的异常条，还需要提供连击次数（用来计算极性紊乱比例），还需要提供触发者ID（CID或者enemy）
    """

    def __init__(
        self,
        Output_bar: AnomalyBar,
        _polarity_disorder_ratio,
        active_by,
        sim_instance: "Simulator",
    ):
        super().__init__(Output_bar, active_by=active_by, sim_instance=sim_instance)
        self.__dict__.update(Output_bar.__dict__)
        self.sim_instance = sim_instance
        self.is_disorder = True
        self.polarity_disorder_ratio = (
            _polarity_disorder_ratio  # 极性紊乱对比紊乱的缩放比例（已经考虑连击次数）
        )
        self.additional_dmg_ap_ratio = 32  # 精通附加伤害的倍率！
        self.activate_by = active_by
        self.source_uuid = self.UUID
        self.UUID = uuid.uuid4()

    def __hash__(self):
        """使对象可哈希"""
        return hash(self.UUID)


class DirgeOfDestinyAnomaly(AnomalyBar):
    """薇薇安的核心被动「命运悲歌」会重复触发一次异常伤害，
    该伤害具有属性异常的全部相同参数，同时具有一个缩放倍率。"""

    def __init__(self, Output_bar: AnomalyBar, active_by, sim_instance: "Simulator"):
        super().__init__(sim_instance=sim_instance)
        self.__dict__.update(Output_bar.__dict__)
        self.sim_instance = sim_instance
        self.activate_by = active_by
        self.anomaly_dmg_ratio = 0  # 属性异常伤害的缩放倍率
        self.source_uuid = self.UUID
        self.UUID = uuid.uuid4()

    def __hash__(self):
        """使对象可哈希"""
        return hash(self.UUID)
