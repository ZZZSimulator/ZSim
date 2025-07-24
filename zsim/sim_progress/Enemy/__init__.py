from typing import TYPE_CHECKING, Literal

import numpy as np
import pandas as pd

from zsim.define import ENEMY_ADJUSTMENT_PATH, ENEMY_DATA_PATH
from zsim.sim_progress.anomaly_bar import (
    AuricInkAnomaly,
    ElectricAnomaly,
    EtherAnomaly,
    FireAnomaly,
    FrostAnomaly,
    IceAnomaly,
    PhysicalAnomaly,
)
from zsim.sim_progress.anomaly_bar.AnomalyBarClass import AnomalyBar
from zsim.sim_progress.data_struct import SingleHit
from zsim.sim_progress.Report import report_to_log
from zsim.models.event_enums import SpecialStateUpdateSignal as SSUS

from .EnemyAttack import EnemyAttackMethod
from .EnemyUniqueMechanic import unique_mechanic_factory
from .QTEManager import QTEManager
from zsim.sim_progress.data_struct.enemy_special_state_manager import SpecialStateManager

if TYPE_CHECKING:
    from zsim.simulator.simulator_class import Simulator


class EnemySettings:
    def __init__(self):
        self.enemy_info_overwrite = False  # 是否强制覆盖怪物数据
        self.forced_no_stun = False
        self.forced_no_anomaly = False
        self.forced_stun_DMG_take_ratio: float = 1.5
        self.forced_anomaly: int = 0


class Enemy:
    def __init__(
        self,
        *,
        name: str | None = None,
        index_id: int | None = None,
        sub_ID: int | None = None,
        adjustment_id: int | None = None,
        difficulty: float = 1,
        sim_instance: "Simulator" = None,
    ):
        """
        根据数据库信息创建怪物属性对象。

        三选一参数:（你不填也行，默认创建尼尼微作为木桩怪，因为她全部0抗性）
        - enemy_name (str): 敌人的中文名称
        - enemy_index_ID (int): 敌人的索引ID
        - enemy_sub_ID (int): 敌人的子ID，格式为9000+索引ID

        !!!注意!!!因为可能存在重名敌人的问题，使用中文名称查找怪物时，只会查找ID最靠前的那一个

        更新参数接口：
            hit_received(single_hit)
            update_stun(float)
        获取临时参数接口：
            get_hp_percentage()
            get_stun_percentage()
        """
        # 读取敌人数据文件，初始化敌人信息
        self.sim_instance = sim_instance
        self.__last_stun_increase_tick: int | None = None
        _raw_enemy_dataframe = pd.read_csv(ENEMY_DATA_PATH)
        _raw_enemy_adjustment_dataframe = pd.read_csv(ENEMY_ADJUSTMENT_PATH)
        # !!!注意!!!因为可能存在重名敌人的问题，使用中文名称查找怪物时，只会返回ID更靠前的
        enemy_info = self.__lookup_enemy(_raw_enemy_dataframe, name, index_id, sub_ID)
        self.name, self.index_ID, self.sub_ID, self.data_dict = enemy_info
        self.adjustment_id = adjustment_id
        # 获取调整倍率
        self.enemy_adjust: dict[
            Literal["生命值", "攻击力", "失衡值上限", "防御力", "异常积蓄值上限"], float
        ] = self.__lookup_enemy_adjustment(_raw_enemy_adjustment_dataframe, adjustment_id)
        # 难度
        self.difficulty: float = difficulty
        # 初始化动态属性
        self.dynamic = self.EnemyDynamic()
        # 初始化敌人基础属性
        self.base_max_HP: float = float(self.data_dict["70级最大生命值"])
        self.max_HP: float = (
            float(self.data_dict["70级最大生命值"])
            * (1 + self.enemy_adjust["生命值"])
            * difficulty
        )
        self.max_ATK: float = float(self.data_dict["70级最大攻击力"]) * (
            1 + self.enemy_adjust["攻击力"]
        )
        self.max_stun: float = float(self.data_dict["70级最大失衡值上限"]) * (
            1 + self.enemy_adjust["失衡值上限"]
        )
        self.max_DEF: float = float(self.data_dict["60级及以上防御力"]) * (
            1 + self.enemy_adjust["防御力"]
        )
        self.CRIT_damage: float = float(self.data_dict["暴击伤害"])
        self.able_to_be_stunned: bool = bool(self.data_dict["能否失衡"])
        self.able_to_get_anomaly: bool = bool(self.data_dict["能否异常"])
        self.stun_recovery_rate: float = float(self.data_dict["失衡恢复速度"]) / 60
        self.stun_recovery_time: float = 0.0
        self.qte_manager: QTEManager | None = None
        self.stun_DMG_take_ratio: float = float(self.data_dict["失衡易伤值"])
        self.QTE_triggerable_times: int = int(self.data_dict["可连携次数"])
        # 初始化敌人异常状态抗性
        max_element_anomaly, self.max_anomaly_PHY = self.__init_enemy_anomaly(
            self.able_to_get_anomaly,
            self.QTE_triggerable_times,
            self.enemy_adjust["异常积蓄值上限"],
        )

        self.max_anomaly_ICE = self.max_anomaly_FIRE = self.max_anomaly_ETHER = (
            self.max_anomaly_ELECTRIC
        ) = self.max_anomaly_FIREICE = self.max_anomaly_AURICINK = max_element_anomaly

        # 初始化敌人其他防御属性
        self.interruption_resistance_level: int = int(self.data_dict["抗打断等级"])
        self.freeze_resistance: float = float(self.data_dict["冻结抵抗"])
        # 伤害抗性
        self.ICE_damage_resistance: float = float(self.data_dict["冰伤害抗性"])
        self.FIRE_damage_resistance: float = float(self.data_dict["火伤害抗性"])
        self.ELECTRIC_damage_resistance: float = float(self.data_dict["电伤害抗性"])
        self.ETHER_damage_resistance: float = float(self.data_dict["以太伤害抗性"])
        self.PHY_damage_resistance: float = float(self.data_dict["物理伤害抗性"])
        # 异常抗性
        self.ICE_anomaly_resistance: float = float(self.data_dict["冰异常抗性"])
        self.FIRE_anomaly_resistance: float = float(self.data_dict["火异常抗性"])
        self.ELECTRIC_anomaly_resistance: float = float(self.data_dict["电异常抗性"])
        self.ETHER_anomaly_resistance: float = float(self.data_dict["以太异常抗性"])
        self.PHY_anomaly_resistance: float = float(self.data_dict["物理异常抗性"])
        # 失衡抗性
        self.ICE_stun_resistance: float = float(self.data_dict["冰失衡抗性"])
        self.FIRE_stun_resistance: float = float(self.data_dict["火失衡抗性"])
        self.ELECTRIC_stun_resistance: float = float(self.data_dict["电失衡抗性"])
        self.ETHER_stun_resistance: float = float(self.data_dict["以太失衡抗性"])
        self.PHY_stun_resistance: float = float(self.data_dict["物理失衡抗性"])
        # 各抗性对应字典
        self.damage_resistance_dict: dict[int, float] = {
            0: self.PHY_damage_resistance,
            1: self.FIRE_damage_resistance,
            2: self.ICE_damage_resistance,
            3: self.ELECTRIC_damage_resistance,
            4: self.ETHER_damage_resistance,
            5: self.ICE_damage_resistance,
            6: self.ETHER_damage_resistance,
        }
        self.anomaly_resistance_dict: dict[int, float] = {
            0: self.PHY_anomaly_resistance,
            1: self.FIRE_anomaly_resistance,
            2: self.ICE_anomaly_resistance,
            3: self.ELECTRIC_anomaly_resistance,
            4: self.ETHER_anomaly_resistance,
            5: self.ICE_anomaly_resistance,
            6: self.ETHER_anomaly_resistance,
        }
        self.stun_resistance_dict: dict[int, float] = {
            0: self.PHY_stun_resistance,
            1: self.FIRE_stun_resistance,
            2: self.ICE_stun_resistance,
            3: self.ELECTRIC_stun_resistance,
            4: self.ETHER_stun_resistance,
            5: self.ICE_stun_resistance,
            6: self.ETHER_stun_resistance,
        }

        # 初始化敌人设置
        self.settings = EnemySettings()
        self.__apply_settings(self.settings)

        # 下面的两个dict本来写在外面的，但是别的程序也要用这两个dict，所以索性写进来了。我是天才。
        self.trans_element_number_to_str = {
            0: "PHY",
            1: "FIRE",
            2: "ICE",
            3: "ELECTRIC",
            4: "ETHER",
            5: "FIREICE",
            6: "AURICINK",
        }
        self.trans_anomaly_effect_to_str = {
            0: "assault",
            1: "burn",
            2: "frostbite",
            3: "shock",
            4: "corruption",
            5: "frost_frostbite",
            6: "auricink_corruption",
        }

        # enemy实例化的时候，6种异常积蓄条也随着一起实例化
        self.frost_anomaly_bar = FrostAnomaly(sim_instance=self.sim_instance)
        self.ice_anomaly_bar = IceAnomaly(sim_instance=self.sim_instance)
        self.fire_anomaly_bar = FireAnomaly(sim_instance=self.sim_instance)
        self.physical_anomaly_bar = PhysicalAnomaly(sim_instance=self.sim_instance)
        self.ether_anomaly_bar = EtherAnomaly(sim_instance=self.sim_instance)
        self.electric_anomaly_bar = ElectricAnomaly(sim_instance=self.sim_instance)
        self.auricink_anomaly_bar = AuricInkAnomaly(sim_instance=self.sim_instance)
        """
        由于在AnomalyBar的init中有一个update_anomaly函数，
        该函数可以根据传入new_snap_shot: tuple 的第0位的属性标号，
        找到对应的anomaly_bar的实例，并且执行它的update_snap_shot 函数。
        以更新对应的积蓄快照。
        本来，这个dict应该建立在update_anomaly函数中，但是考虑到该函数会反复调用，频繁地创建这个dict会导致性能的浪费。
        所以将其挪到Enemy的init中，这样，这个dict只在Enemy实例化时被创建一次，
        然后update_anomaly函数将通过enemy.anomaly_bars_dict来调出对应的anomaly_bars实例。
        """
        self.anomaly_bars_dict: dict[int, AnomalyBar] = {
            0: self.physical_anomaly_bar,
            1: self.fire_anomaly_bar,
            2: self.ice_anomaly_bar,
            3: self.electric_anomaly_bar,
            4: self.ether_anomaly_bar,
            5: self.frost_anomaly_bar,
            6: self.auricink_anomaly_bar,
        }
        # 在初始化阶段更新属性异常条最大值。
        for element_type in self.anomaly_bars_dict:
            anomaly_bar = self.anomaly_bars_dict[element_type]
            max_value = getattr(
                self, f"max_anomaly_{self.trans_element_number_to_str[element_type]}"
            )
            anomaly_bar.max_anomaly = max_value

        if self.data_dict["进攻策略"] is None or self.data_dict["进攻策略"] is np.nan:
            attack_method_code = 0
        else:
            attack_method_code = int(self.data_dict["进攻策略"])
        self.attack_method = EnemyAttackMethod(
            ID=attack_method_code, enemy_instance=self
        )
        self.restore_stun()

        self.unique_machanic_manager = unique_mechanic_factory(self)  # 特殊机制管理器
        self.special_state_manager = SpecialStateManager(enemy_instance=self)

        report_to_log(
            f"[ENEMY]: 怪物对象 {self.name} 已创建，怪物ID {self.index_ID}", level=4
        )

    def __restore_stun_recovery_time(self):
        self.stun_recovery_time = float(self.data_dict["失衡恢复时间"]) * 60

    def restore_stun(self):
        """还原 Enemy 本身的失衡恢复时间，与QTE计数"""
        self.dynamic.stun = False
        self.dynamic.stun_bar = 0
        self.dynamic.stun_tick = 0
        self.dynamic.stun_tick_feed_back_from_QTE = 0
        self.__restore_stun_recovery_time()
        if self.qte_manager is None:
            self.qte_manager = QTEManager(self)
        self.qte_manager.qte_data.restore()

    def increase_stun_recovery_time(self, increase_tick: int):
        """更新失衡延长的时间，负责接收 Calculator 的 buff"""
        if self.__last_stun_increase_tick is None:
            self.__last_stun_increase_tick = increase_tick
            self.stun_recovery_time += increase_tick
        else:
            if increase_tick >= self.__last_stun_increase_tick:
                self.__last_stun_increase_tick = increase_tick
                self.__restore_stun_recovery_time()
                self.stun_recovery_time += increase_tick

    def get_active_anomaly_bar(self) -> type(AnomalyBar):
        """用于外部获取当前正在激活的属性异常条对象"""
        output_list = []
        for element_type, anomaly_bar in self.anomaly_bars_dict.items():
            if anomaly_bar.active:
                output_list.append(self.dynamic.active_anomaly_bar_dict[element_type])
        if len(output_list) == 0 or len(output_list) > 1:
            raise ValueError(
                f"状态错误！找到了{len(output_list)}种正在激活的属性异常条！"
            )
        return output_list[0]

    @staticmethod
    def __lookup_enemy(
        enemy_df: pd.DataFrame,
        enemy_name: str | None = None,
        enemy_index_ID: int | None = None,
        enemy_sub_ID: int | None = None,
    ) -> tuple[str, int, int, dict]:
        """
        根据敌人名称或ID查找敌人信息，并返回敌人名称、IndexID和SubID。

        若输入多个参数，此函数会检测这些参数是否一一对应
        !!!注意!!!因为可能存在重名敌人的问题，使用中文名称查找怪物时，只会返回ID更靠前的
        因此，在已经输入了ID的情况下，函数不会优先根据中文名查找

        参数:
        - enemy_df: pd.DataFrame, 敌人数据 DataFrame，包含敌人信息。
        - enemy_name: str, 可选，敌人名称。
        - enemy_index_ID: int, 可选，敌人IndexID。
        - enemy_sub_ID: int, 可选，敌人SubID。

        返回：
        - 有传入参数时，返回对应怪物的数据
        - 无传入参数时，返回尼尼微的数据
        """
        # fmt: off
        try:
            if enemy_index_ID is not None:
                row = enemy_df[enemy_df["IndexID"] == enemy_index_ID].to_dict("records")
            elif enemy_sub_ID is not None:
                row = enemy_df[enemy_df["SubID"] == enemy_sub_ID].to_dict("records")
            elif enemy_name is not None:
                row = enemy_df[enemy_df["CN_enemy_ID"] == enemy_name].to_dict("records")
            else:
                row = enemy_df[enemy_df["IndexID"] == 11531].to_dict("records")  # 默认打尼尼微（因为全部0抗）
            if not row:
                raise ValueError(f"找不到对应的敌人，请检查输入参数：name={enemy_name}, index_id={enemy_index_ID}, sub_id={enemy_sub_ID}")
        except IndexError:
            raise ValueError("找不到对应的敌人")
        # fmt: on

        row_0: dict = row[0]
        name: str = row_0["CN_enemy_ID"]
        index_ID: int = int(row_0["IndexID"])
        sub_ID: int = int(row_0["SubID"])

        # 检查输入的变量与查到的变量是否一致
        if enemy_name is not None:
            if name != enemy_name:
                raise ValueError("传入的name与ID不匹配")
        if enemy_index_ID is not None:
            if index_ID != enemy_index_ID:
                raise ValueError("传入的name与ID不匹配")
        if enemy_sub_ID is not None:
            if sub_ID != enemy_sub_ID:
                raise ValueError("传入的name与ID不匹配")

        return name, index_ID, sub_ID, row_0

    @staticmethod
    def __lookup_enemy_adjustment(
        adjust_df: pd.DataFrame, adjust_ID: int
    ) -> dict[
        Literal["生命值", "攻击力", "失衡值上限", "防御力", "异常积蓄值上限"], float
    ]:
        """根据调整ID查找敌人调整数据，并返回调整数据字典。"""
        try:
            row = adjust_df[adjust_df["ID"] == adjust_ID].to_dict("records")
        except IndexError:
            raise ValueError(f"找不到属性调整ID：{adjust_ID}")
        row_0: dict[
            Literal["生命值", "攻击力", "失衡值上限", "防御力", "异常积蓄值上限"], float
        ] = dict(row[0])
        return row_0

    @staticmethod
    def __init_enemy_anomaly(
        able_to_get_anomaly: bool, QTE_triggerable_times: int, adjust: float
    ) -> tuple[int | float, int | float]:
        """
        根据敌人的异常能力和QTE触发次数(怪物等阶)初始化敌人的异常值。

        参数:
        able_to_get_anomaly (bool): 敌人是否能获得异常值。
        QTE_triggerable_times (int): QTE可触发的次数。

        返回:
        tuple: 包含两个值，分别为基础异常值和物理异常值。
        """
        if able_to_get_anomaly:
            # 定义基础异常值
            base_anomaly = 150 * (1 + adjust)
            # 定义物理异常值的乘数
            physical_anomaly_mul = 1.2
            # 计算物理异常值
            base_anomaly_physical = base_anomaly * physical_anomaly_mul
            # 根据QTE触发次数返回相应的异常值
            if QTE_triggerable_times == 1:
                return base_anomaly * 4, base_anomaly_physical * 4
            elif QTE_triggerable_times == 2:
                return base_anomaly * 15, base_anomaly_physical * 15
            elif QTE_triggerable_times == 3:
                return base_anomaly * 20, base_anomaly_physical * 20
            else:
                # 如果QTE触发次数不符合已定义的条件，返回默认异常值
                return 3000, 3600  # 默认异常值
        else:
            return 0, 0

    def __apply_settings(self, settings: EnemySettings):
        if settings.enemy_info_overwrite:
            if settings.forced_no_stun:
                self.able_to_be_stunned = False
            if settings.forced_no_anomaly:
                self.able_to_get_anomaly = False
            self.stun_DMG_take_ratio = settings.forced_stun_DMG_take_ratio
        else:
            pass

    @staticmethod
    def __qte_tag_filter(self, tag: str) -> list[str]:
        """判断输入的标签是否为QTE，并作为列表返回"""
        result = []
        if "QTE" in tag:
            result.append(tag)
        return result

    def update_anomaly(self, element: str | int = "ALL", *, times: int = 1) -> None:
        """更新怪物异常值，触发一次异常后调用。"""

        # 参数类型检查
        if not isinstance(element, (str, int)):
            raise TypeError(
                f"element参数类型错误，必须是整数或字符串，实际类型为{type(element)}"
            )
        if not isinstance(times, int):
            raise TypeError(f"times参数必须是整数，实际类型为{type(times)}")
        if times <= 0:
            raise ValueError(f"times参数必须大于0，实际值为{times}")

        # 属性类型映射表
        element_mapping: dict[str, tuple] = {
            "PHY": ("物理", 0),
            "FIRE": ("火", 1),
            "ICE": ("冰", 2),
            "ELECTRIC": ("电", 3),
            "ETHER": ("以太", 4),
            "FROST": ("烈霜", "FIREICE", 5),
            "AURICINK": ("玄墨", 6),
            "ALL": ("全部", "所有"),
        }
        # 检查并标准化元素
        if isinstance(element, str):
            element = element.upper()
            for key, values in element_mapping.items():
                if element in (key, *values):
                    element = key
                    break
            else:
                raise ValueError(f"输入了不支持的元素种类：{element}")
        elif isinstance(element, int):
            for key, values in element_mapping.items():
                if element in values:
                    element = key
                    break
            else:
                raise ValueError(f"输入了不支持的元素种类：{element}")
        else:
            raise ValueError(f"无法识别的元素种类：{element}")

        # 更新比例
        update_ratio = 1.02  # 每次异常增加 2% 对应属性异常值

        # 确保 times 在合理范围内
        if times > 1e6:  # 防止极端值导致性能问题
            raise ValueError(f"times参数过大，可能导致性能问题，实际值为{times}")

        # 计算最终更新比例
        multiplier = update_ratio**times

        # 批量更新异常值
        if element == "ALL":
            self.max_anomaly_ICE *= multiplier
            self.max_anomaly_FIRE *= multiplier
            self.max_anomaly_ETHER *= multiplier
            self.max_anomaly_ELECTRIC *= multiplier
            self.max_anomaly_PHY *= multiplier
            self.max_anomaly_FIREICE *= multiplier
            self.max_anomaly_AURICINK *= multiplier
        else:
            # 单个元素更新
            if element == "ICE":
                self.max_anomaly_ICE *= multiplier
            elif element == "FIRE":
                self.max_anomaly_FIRE *= multiplier
            elif element == "ETHER":
                self.max_anomaly_ETHER *= multiplier
            elif element == "ELECTRIC":
                self.max_anomaly_ELECTRIC *= multiplier
            elif element == "PHY":
                self.max_anomaly_PHY *= multiplier
            elif element == "FROST":
                self.max_anomaly_FIREICE *= multiplier
            elif element == "AURICINK":
                self.max_anomaly_AURICINK *= multiplier

    def update_stun(self, stun: np.float64) -> None:
        self.dynamic.stun_bar += stun

    def hit_received(self, single_hit: SingleHit, tick: int) -> None:
        """实现怪物的QTE次数计算、扣血计算等受击时的对象结算，与伤害计算器对接"""
        # 更新失衡，为减少函数调用
        self.dynamic.stun_bar += single_hit.stun
        self.stun_judge(tick, single_hit=single_hit)
        # 怪物的扣血逻辑。
        self.__HP_update(single_hit.dmg_expect)
        # 更新异常值
        self.__anomaly_prod(single_hit.snapshot, single_hit=single_hit)

        if self.unique_machanic_manager is not None:
            self.unique_machanic_manager.update_myself(single_hit, tick)

        # 更新连携管理器
        self.qte_manager.receive_hit(single_hit)
        self.sim_instance.preload.preload_data.atk_manager.receive_single_hit(
            single_hit=single_hit, tick=tick
        )
        # 在接收hit的时，向所有特殊状态进行广播，执行更新自检！
        self.special_state_manager.broadcast_and_update(signal=SSUS.RECEIVE_HIT, single_hit=single_hit)

    # 遥远的需求：
    #  TODO：实时DPS的计算，以及预估战斗结束时间，用于进一步优化APL。（例：若目标预计死亡时间<5秒，则不补buff）

    def get_total_hp_percentage(self) -> float:
        """获取当前生命值百分比的方法（总量百分比）"""
        return 1 - self.dynamic.lost_hp / self.max_HP

    def get_current_hp_percentage(self) -> float:
        """获取当前生命值百分比的方法（小血条百分比）"""
        return 1 - self.dynamic.lost_hp % self.base_max_HP / self.base_max_HP

    def get_stun_percentage(self) -> float:
        """获取当前失衡值百分比的方法"""
        return self.dynamic.stun_bar / self.max_stun

    def get_stun_rest_tick(self) -> float:
        """获取当前剩余失衡时间的方法"""
        #  TODO：未完全实现！连携技返还失衡时间部分尚未完成。
        if not self.dynamic.stun:
            return 0
        return (
            self.stun_recovery_time
            - self.dynamic.stun_tick
            + self.dynamic.stun_tick_feed_back_from_QTE
        )

    def stun_judge(self, _tick: int, **kwargs) -> bool:
        """判断敌人是否处于 失衡 状态，并更新 失衡 状态"""

        single_hit = kwargs.get("single_hit", None)
        if not self.able_to_be_stunned:
            self.dynamic.stun_update_tick = _tick
            return False

        if self.dynamic.stun:
            # 如果已经是失衡状态，则判断是否恢复
            if (
                self.stun_recovery_time + self.dynamic.stun_tick_feed_back_from_QTE
                <= self.dynamic.stun_tick
            ):
                self.dynamic.stun_update_tick = _tick
                self.restore_stun()
            else:
                if _tick - self.dynamic.stun_update_tick > 1:
                    raise ValueError(
                        "状态更新间隔大于1！存在多个tick都未更新stun的情况！"
                    )
                self.dynamic.stun_bar = 0  # 避免 log 差错
                self.dynamic.stun_update_tick = _tick

                # 若怪物当前处于冻结状态，则不增加stun_tick
                if not self.dynamic.frozen:
                    self.dynamic.stun_tick += 1
                # else:
                #     print("检测到怪物当前处于冻结状态，所以不会增加stun_tick！！")
        elif self.dynamic.stun_bar >= self.max_stun:
            # 若是检测到失衡状态的上升沿，则应该开启彩色失衡状态。
            self.qte_manager.qte_data.reset()
            print("怪物陷入失衡了！")
            self.dynamic.stun = True
            self.dynamic.stun_bar = 0  # 避免 log 差错
            self.dynamic.stun_update_tick = _tick
            if single_hit:
                self.sim_instance.decibel_manager.update(
                    single_hit=single_hit, key="stun"
                )
                self.sim_instance.listener_manager.broadcast_event(
                    single_hit, stun_event=1
                )
            if self.sim_instance.preload.preload_data.atk_manager.attacking:
                self.sim_instance.preload.preload_data.atk_manager.interrupted(
                    tick=_tick, reason="被打进失衡"
                )

        return self.dynamic.stun

    def __HP_update(self, dmg_expect: np.float64) -> None:
        """用于更新敌人已损生命值"""
        self.dynamic.lost_hp += dmg_expect
        if (minus := self.max_HP - self.dynamic.lost_hp) <= 0:
            self.dynamic.lost_hp = -1 * minus
            report_to_log(f"怪物{self.name}死亡！")

    def __anomaly_prod(self, snapshot: tuple[int, np.float64, np.ndarray], single_hit: SingleHit) -> None:
        """用于更新异常条的角色面板快照"""
        if snapshot[1] >= 1e-6:  # 确保非零异常值才更新
            element_type_code = snapshot[0]
            updated_bar = self.anomaly_bars_dict[element_type_code]
            updated_bar.update_snap_shot(snapshot, single_hit=single_hit)

    def reset_myself(self):
        self.dynamic.reset_myself()
        self.reset_anomaly_bars()
        self.qte_manager.reset_myself()
        self.attack_method.reset_myself()
        if self.unique_machanic_manager is not None:
            self.unique_machanic_manager.reset_myself()

    def reset_anomaly_bars(self):
        """重置异常条！"""
        max_element_anomaly, self.max_anomaly_PHY = self.__init_enemy_anomaly(
            self.able_to_get_anomaly,
            self.QTE_triggerable_times,
            self.enemy_adjust["异常积蓄值上限"],
        )
        self.max_anomaly_ICE = self.max_anomaly_FIRE = self.max_anomaly_ETHER = (
            self.max_anomaly_ELECTRIC
        ) = self.max_anomaly_FIREICE = max_element_anomaly
        for element_type, anomaly_bar in self.anomaly_bars_dict.items():
            anomaly_bar.reset_myself()
            max_value = getattr(
                self, f"max_anomaly_{self.trans_element_number_to_str[element_type]}"
            )
            anomaly_bar.max_anomaly = max_value

    def find_dot(self, dot_tag: str) -> object | None:
        """通过dot名，查找enemy身上是否存在此dot"""
        for dots in self.dynamic.dynamic_dot_list:
            if dots.ft.index == dot_tag and dots.dy.active:
                return dots
            else:
                continue
        else:
            return None

    class EnemyDynamic:
        def __init__(self):
            self.stun = False  # 失衡状态
            self.stun_update_tick = 0  # 上次更新失衡状态的时间
            self.frozen = False  # 冻结状态
            self.frostbite = False  # 霜寒状态
            self.frost_frostbite = False  # 烈霜霜寒状态
            self.assault = False  # 畏缩状态
            self.shock = False  # 感电状态
            self.burn = False  # 灼烧状态
            self.corruption = False  # 侵蚀状态
            self.auricink_corruption = False  # 玄墨侵蚀状态

            self.dynamic_debuff_list = []  # 用来装debuff的list
            self.dynamic_dot_list = []  # 用来装dot的list
            self.active_anomaly_bar_dict = {
                number: AnomalyBar for number in range(6)
            }  # 用来装激活属性异常的字典。

            self.stun_bar = 0  # 累计失衡条
            self.lost_hp = 0  # 已损生命值
            self.stun_tick = 0  # 失衡已进行时间
            self.stun_tick_feed_back_from_QTE = 0  # 从QTE中返还的失衡时间

            self.frozen_tick = 0
            self.frostbite_tick = 0
            self.assault_tick = 0
            self.shock_tick = 0
            self.burn_tick = 0
            self.corruption_tick = 0

        def __str__(self):
            return f"失衡: {self.stun}, 失衡条: {self.stun_bar:.2f}, 冻结: {self.frozen}, 霜寒: {self.frostbite}, 畏缩: {self.assault}, 感电: {self.shock}, 灼烧: {self.burn}, 侵蚀：{self.corruption}, 烈霜霜寒：{self.frost_frostbite}"

        def get_status(self) -> dict:
            return {
                "失衡状态": self.stun,
                "失衡条": self.stun_bar,
                "已损生命值": self.lost_hp,
                "冻结": self.frozen,
                "霜寒": self.frostbite,
                "畏缩": self.assault,
                "感电": self.shock,
                "灼烧": self.burn,
                "侵蚀": self.corruption,
                "烈霜霜寒": self.frost_frostbite,
                "玄墨侵蚀": self.auricink_corruption,
            }

        def reset_myself(self):
            self.stun = False
            self.stun_update_tick = 0
            self.frozen = False
            self.frostbite = False
            self.frost_frostbite = False
            self.assault = False
            self.shock = False
            self.burn = False
            self.corruption = False
            self.dynamic_debuff_list = []
            self.dynamic_dot_list = []
            self.active_anomaly_bar_dict = {number: None for number in range(6)}
            self.stun_bar = 0
            self.lost_hp = 0
            self.stun_tick = 0
            self.frozen_tick = 0
            self.frostbite_tick = 0
            self.assault_tick = 0
            self.shock_tick = 0
            self.burn_tick = 0
            self.corruption_tick = 0
            self.stun_tick_feed_back_from_QTE = 0

        def is_under_anomaly(self) -> bool:
            """若敌人正处于任意一种异常状态下，都会返回True"""
            return any(
                [
                    self.frostbite,
                    self.frost_frostbite,
                    self.assault,
                    self.burn,
                    self.corruption,
                    self.shock,
                ]
            )

        def get_active_anomaly(self) -> list[type(AnomalyBar) | None]:
            if self.is_under_anomaly():
                return [
                    _anomaly_bar
                    for _anomaly_bar in self.active_anomaly_bar_dict.values()
                    if _anomaly_bar is not None and _anomaly_bar.active
                ]
            else:
                return []

    def __str__(self):
        return f"{self.name}: {self.dynamic.__str__()}"

    def __deepcopy__(self, memo):
        return self


if __name__ == "__main__":
    test = Enemy(index_id=11432, sub_ID=900011432)
    print(test.ice_anomaly_bar.max_anomaly)
