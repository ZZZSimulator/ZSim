import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from ...define import ELEMENT_TYPE_MAPPING

if TYPE_CHECKING:
    from zsim.sim_progress.Preload import SkillNode
    from zsim.simulator.simulator_class import Simulator
    from zsim.sim_progress.data_struct.single_hit import SingleHit


@dataclass
class AnomalyBar:
    """
    这是属性异常类的基类。其中包含了属性异常的基本属性，以及几个基本方法。
    """

    sim_instance: "Simulator"
    element_type: int = 0  # 属性种类编号(1~5)
    is_disorder: bool = False  # 是否是紊乱实例
    current_ndarray: np.ndarray | None = None  # 当前快照总和
    current_anomaly: np.float64 | None = None  # 当前已经累计的积蓄值
    current_effective_anomaly: np.float64 | None = None     # 有效积蓄值（参与快照的）
    anomaly_times: int = 0  # 迄今为止触发过的异常次数
    cd: int = 180  # 属性异常的内置CD，
    last_active: int = 0  # 上一次属性异常的时间
    max_anomaly: int | None = None  # 最大积蓄值
    ready: bool = True  # 内置CD状态
    accompany_debuff: list | None = None  # 是否在激活时伴生debuff的index
    accompany_dot: str | None = None  # 是否在激活时伴生dot的index
    active: bool | None = (
        None  # 当前异常条是否激活，这一属性和enemy下面的异常开关同步。
    )
    max_duration: int | None = None
    duration_buff_list: list | None = None  # 影响当前异常状态最大时长的buff名
    duration_buff_key_list: list | None = (
        None  # 影响当前异常状态最大时长的buff效果关键字
    )
    basic_max_duration: int = 0  # 基础最大时间
    UUID: uuid.UUID | None = None
    activated_by = None
    ndarray_box: list[tuple] | None = None

    def __post_init__(self):
        self.current_ndarray: np.ndarray = np.zeros((1, 1), dtype=np.float64)
        self.current_anomaly: np.float64 = np.float64(0)
        self.UUID = uuid.uuid4()

    @property
    def is_full(self):
        return self.current_anomaly >= self.max_anomaly

    def remaining_tick(self):
        timetick = self.sim_instance.tick
        remaining_tick = max(self.max_duration - self.duration(timetick), 0)
        return remaining_tick

    def duration(self, timetick: int):
        duration = timetick - self.last_active
        if self.max_duration is not None:
            assert duration <= self.max_duration, "该异常早就结束了！不应该触发紊乱！"
        else:
            assert False, "该异常的max_duration为None，无法判断是否过期！"
        return duration

    def update_snap_shot(self, new_snap_shot: tuple, single_hit: "SingleHit"):
        """
        该函数是更新快照的核心函数。但是并不具备识别属性种类的功能。
        所以需要在外部嵌套一个总函数，根据属性种类来执行不同属性的update函数。
        """
        if not isinstance(new_snap_shot[2], np.ndarray):
            raise TypeError("所传入的快照元组的第3个元素应该是np.ndarray！")
        #
        # new_ndarray = new_snap_shot[2].reshape(1, -1)  # 将数据重塑为一行多列的形式
        build_up_value = new_snap_shot[1]  # 获取积蓄值
        #
        # assert self.current_ndarray is not None, "当前快照数组为None！"
        # if self.current_ndarray.shape[1] != new_ndarray.shape[1]:
        #     # 扩展 current_ndarray 列数，保持已有数据，新增的部分会填充为零
        #     if self.current_ndarray.shape[1] < new_ndarray.shape[1]:
        #         # 扩展 current_ndarray 列数，增加零列
        #         new_shape = (1, new_ndarray.shape[1])
        #         extended_ndarray = np.zeros(new_shape, dtype=np.float64)
        #         # 将已有的数据复制到新的 ndarray 中
        #         extended_ndarray[:, : self.current_ndarray.shape[1]] = (
        #             self.current_ndarray
        #         )
        #         self.current_ndarray = extended_ndarray
        #     else:
        #         # 如果 current_ndarray 列数大于 new_ndarray 列数，直接裁剪 current_ndarray
        #         raise ValueError(
        #             f"传入的快照数组列数为{new_ndarray.shape[1]}，小于快照缓存的列数！"
        #         )
        #
        # cal_result_1 = build_up_value * new_ndarray
        # self.current_ndarray += cal_result_1
        self.current_anomaly += build_up_value

        # print(f"测试：{self.sim_instance.tick}tick：{single_hit.skill_tag}命中！积蓄了{build_up_value}点{ELEMENT_TYPE_MAPPING[new_snap_shot[0]]}属性积蓄！当前积蓄值为：{self.current_anomaly}")
        if single_hit.effective_anomlay_buildup():
            # 只有有效积蓄才会累计快照
            if self.ndarray_box is None:
                self.ndarray_box = []
            self.ndarray_box.append(new_snap_shot)

    def ready_judge(self, timenow):
        if timenow - self.last_active >= self.cd:
            self.ready = True

    def check_myself(self, timenow: int):
        assert self.max_duration is not None, (
            "该异常的max_duration为None，无法判断是否过期！"
        )
        if self.active and (self.last_active + self.max_duration < timenow):
            self.active = False
            return True
        return False

    def change_info_cause_active(self, timenow: int, **kwargs):
        """
        属性异常激活时，必要的信息更新
        """
        dynamic_buff_dict = kwargs.get("dynamic_buff_dict")
        skill_node = kwargs.get("skill_node")
        char_cid = int(skill_node.skill_tag.strip().split("_")[0])
        self.ready = False
        self.anomaly_times += 1
        self.last_active = timenow
        self.active = True
        self.activated_by: "SkillNode" = skill_node
        self.__get_max_duration(dynamic_buff_dict, char_cid)
        self.sim_instance.schedule_data.change_process_state()
        print(f"{skill_node.char_name}的技能【{self.activated_by.skill_tag}】激活了【{ELEMENT_TYPE_MAPPING[self.element_type]}】属性的异常状态！")

    def reset_current_info_cause_output(self):
        """
        重置和属性积蓄条以及快照相关的信息。
        该函数通常位于抛出异常实例之前调用，
        """
        self.current_effective_anomaly = np.float64(0)
        self.current_anomaly = np.float64(0)
        self.current_ndarray = np.zeros(
            (1, self.current_ndarray.shape[0]), dtype=np.float64
        )
        self.ndarray_box = []

    def get_buildup_pct(self):
        if self.max_anomaly is None:
            return 0
        if self.is_full:
            return 1
        pct = self.current_anomaly / self.max_anomaly
        return pct

    def reset_myself(self):
        self.current_ndarray = None
        self.current_anomaly = None
        self.anomaly_times = 0
        self.last_active = 0
        self.ready = True
        self.active = False
        self.max_anomaly = None
        self.ndarray_box = None

    def __get_max_duration(self, dynamic_buff_list, anomaly_from: int | str) -> None:
        """通过Buff计算当前异常的最大持续时间"""
        if self.duration_buff_list is None:
            self.max_duration = self.basic_max_duration
            # print(f'属性类型为{self.element_type}的异常不存在影响持续时间的Buff，所以直接使用基础值{self.basic_max_duration}')
            return
        max_duration_delta_fix = 0
        max_duration_delta_pct = 0
        for _buff_index in self.duration_buff_list:
            enemy_buff_list = dynamic_buff_list.get("enemy")
            for buffs in enemy_buff_list:
                if _buff_index == buffs.ft.index and buffs.dy.active:
                    for keys in self.duration_buff_key_list:
                        if keys in buffs.effect_dct.keys():
                            if "百分比" in keys:
                                max_duration_delta_pct += (
                                    buffs.dy.count * buffs.effect_dct.get(keys)
                                )
                            else:
                                max_duration_delta_fix += (
                                    buffs.dy.count * buffs.effect_dct.get(keys)
                                )

        self.max_duration = max(
            self.basic_max_duration * (1 + max_duration_delta_pct)
            + max_duration_delta_fix,
            0,
        )
        # print(f'属性类型为{self.element_type}的异常激活了，本次激活的最大时长为{self.max_duration}')

    @staticmethod
    def create_new_from_existing(existing_instance):
        """
        通过复制已有实例的状态来创建新实例
        """
        new_instance = AnomalyBar.__new__(AnomalyBar)  # 不调用构造函数
        new_instance.__dict__ = existing_instance.__dict__.copy()  # 复制原实例的属性
        return new_instance

    def __deepcopy__(self, memo):
        """AnomalyBar的deepcopy方法，需要绕开Buff"""
        import copy
        cls = self.__class__
        new_anomaly_bar = cls.__new__(cls)
        memo[id(self)] = new_anomaly_bar
        # 安全复制属性
        for key, value in self.__dict__.items():
            if key == 'sim_instance':
                # 直接复制 Simulator 引用（避免深拷贝 Buff）
                setattr(new_anomaly_bar, key, value)
            elif key == 'activated_by' and hasattr(value, 'skill'):
                # 复制 SkillNode 但不深拷贝其内部技能对象
                new_skill_node = copy.copy(value)
                setattr(new_anomaly_bar, key, new_skill_node)
            elif key == 'current_ndarray' and value is not None:
                # 使用 numpy 的安全复制方法
                setattr(new_anomaly_bar, key, value.copy())
            elif key == 'current_anomaly' and value is not None:
                # 安全复制 np.float64
                setattr(new_anomaly_bar, key, copy.copy(value))
            elif key == 'UUID':
                # 生成新的 UUID
                setattr(new_anomaly_bar, key, uuid.uuid4())
            else:
                try:
                    # 尝试标准深拷贝
                    setattr(new_anomaly_bar, key, copy.deepcopy(value, memo))
                except TypeError:
                    # 无法深拷贝时回退到浅拷贝
                    setattr(new_anomaly_bar, key, value)

        return new_anomaly_bar

    def anomaly_settled(self):
        """结算快照！"""
        total_array = np.zeros((1, 1), dtype=np.float64)
        effective_buildup = 0
        while self.ndarray_box:
            _tuples = self.ndarray_box.pop()
            _element_type = _tuples[0]
            _array = _tuples[2].reshape(1, -1)
            _build_up = _tuples[1]
            if total_array.shape[1] != _array.shape[1]:
                if total_array.shape[1] < _array.shape[1]:
                    new_shape = (1, _array.shape[1])
                    extended_ndarray = np.zeros(new_shape, dtype=np.float64)
                    # 将已有的数据复制到新的 ndarray 中
                    extended_ndarray[:, : total_array.shape[1]] = (
                        total_array
                    )
                    total_array = extended_ndarray
                else:
                    raise ValueError(
                        f"传入的快照数组列数为{_array.shape[1]}，小于快照缓存的列数！"
                    )
            total_array += _array * _build_up
            effective_buildup += _build_up
        self.current_effective_anomaly = effective_buildup
        self.current_ndarray = total_array / self.current_effective_anomaly

