from typing import TYPE_CHECKING, Literal, Mapping, Sequence

import numpy as np

from zsim.define import ELEMENT_TYPE_MAPPING as ETM
from zsim.define import ElementType
from zsim.sim_progress.anomaly_bar import AnomalyBar
from zsim.sim_progress.anomaly_bar.CopyAnomalyForOutput import DirgeOfDestinyAnomaly as Abloom
from zsim.sim_progress.anomaly_bar.CopyAnomalyForOutput import (
    Disorder,
    PolarityDisorder,
)
from zsim.sim_progress.calculation.calculator import Calculator as Cal
from zsim.sim_progress.calculation.calculator import MultiplierData as MulData
from zsim.sim_progress.calculation.formulas.anomaly import anomaly_damage as anomaly_damage_formulas
from zsim.sim_progress.calculation.formulas.anomaly import disorder as disorder_formulas
from zsim.sim_progress.calculation.formulas.anomaly import (
    polarity_disorder as polarity_disorder_formulas,
)
from zsim.sim_progress.calculation.inputs.anomaly import (
    AnomalyDamageMultipliers,
    AnomalyDamageSnapshot,
)
from zsim.sim_progress.calculation.results.common import MultiplierVector
from zsim.sim_progress.Character.character import Character
from zsim.sim_progress.Character.Yanagi import Yanagi
from zsim.sim_progress.Enemy import Enemy
from zsim.sim_progress.Report import report_to_log

if TYPE_CHECKING:
    from zsim.sim_progress.Buff import Buff
    from zsim.sim_progress.Character import Character
    from zsim.simulator.simulator_class import Simulator


def _assemble_final_multiplier_vector(
    dmg_sp: np.ndarray,
    *,
    k_level: float | np.float64,
    active_crit: float | np.float64,
    def_mul: float | np.float64,
    res_mul: float | np.float64,
    vulnerability_mul: float | np.float64,
    snapshot_impact: float | np.float64,
    snapshot_stun_bonus: float | np.float64,
    stun_vulnerability: float | np.float64,
    special_mul: float | np.float64,
) -> np.ndarray:
    """组装异常最终伤害乘区，顺序必须与旧公式保持一致。"""
    # self.dmg_sp 以 array 形式储存，顺序为：基础伤害区、增伤区、异常精通区、等级、异常增伤区、异常暴击区、穿透率、穿透值、抗性穿透、冲击力、失衡值增幅
    snapshot = AnomalyDamageSnapshot(
        base_damage=float(dmg_sp[0, 0]),
        damage_bonus=float(dmg_sp[0, 1]),
        anomaly_mastery_multiplier=float(dmg_sp[0, 2]),
        anomaly_damage_bonus=float(dmg_sp[0, 4]),
        snapshot_impact=float(snapshot_impact),
        snapshot_stun_bonus=float(snapshot_stun_bonus),
    )
    multipliers = AnomalyDamageMultipliers(
        level_multiplier=float(k_level),
        active_crit_multiplier=float(active_crit),
        defense_multiplier=float(def_mul),
        resistance_multiplier=float(res_mul),
        vulnerability_multiplier=float(vulnerability_mul),
        stun_vulnerability_multiplier=float(stun_vulnerability),
        special_multiplier=float(special_mul),
    )
    vector = anomaly_damage_formulas.assemble_anomaly_damage_multiplier_vector(
        snapshot,
        multipliers,
    )
    return np.array(
        vector.values,
        dtype=np.float64,
    )


def _calculate_anomaly_damage_expectation(
    final_multipliers: np.ndarray,
    *,
    snapshot_impact: float | np.float64,
    snapshot_stun_bonus: float | np.float64,
    scaling_factor: float | np.float64,
) -> np.float64:
    """计算异常伤害期望，保留旧公式中的冲击力与失衡值增幅抵消。"""
    return anomaly_damage_formulas.calculate_anomaly_damage_expectation(
        final_multipliers,
        snapshot_impact=float(snapshot_impact),
        snapshot_stun_bonus=float(snapshot_stun_bonus),
        scaling_factor=float(scaling_factor),
    )


def _calculate_disorder_base_damage(
    *,
    element_type: ElementType,
    base_mul: float | np.float64,
    remaining_tick: float | np.float64,
    disorder_basic_mul_map: Mapping[ElementType | Literal["all"], float],
) -> np.float64:
    """
    计算紊乱的基础伤害。

    紊乱基础伤害 = (各属性异常剩余倍率 + 各属性紊乱基础倍率) * (1 + 紊乱基础倍率增幅)
    """
    return disorder_formulas.calculate_disorder_base_damage(
        element_type=element_type,
        base_multiplier=float(base_mul),
        remaining_tick=float(remaining_tick),
        disorder_basic_multiplier_map=disorder_basic_mul_map,
    )


def _calculate_disorder_extra_multiplier(
    ano_extra_bonus: Mapping[ElementType | Literal["all", -1], float],
) -> np.float64:
    return disorder_formulas.calculate_disorder_extra_multiplier(ano_extra_bonus)


def _calculate_disorder_stun_multiplier(
    *,
    impact: float | np.float64,
    snapshot_stun_bonus: float | np.float64,
    stun_res: float | np.float64,
    received_stun_increase: float | np.float64,
    v_char_level: int,
) -> np.float64:
    return disorder_formulas.calculate_disorder_stun_multiplier(
        impact=float(impact),
        snapshot_stun_bonus=float(snapshot_stun_bonus),
        stun_resistance_multiplier=float(stun_res),
        received_stun_increase_multiplier=float(received_stun_increase),
        virtual_character_level=v_char_level,
    )


def _calculate_polarity_disorder_base_damage(
    *,
    base_disorder_damage: float | np.float64,
    yanagi_ap: float | np.float64,
    polarity_disorder_ratio: float | np.float64,
    additional_dmg_ap_ratio: float | np.float64,
) -> np.float64:
    """计算极性紊乱最终基础伤害，保留柳异常精通追加项。"""
    return polarity_disorder_formulas.calculate_polarity_disorder_base_damage(
        base_disorder_damage=float(base_disorder_damage),
        yanagi_ap=float(yanagi_ap),
        polarity_disorder_ratio=float(polarity_disorder_ratio),
        additional_dmg_ap_ratio=float(additional_dmg_ap_ratio),
    )


def _apply_abloom_anomaly_damage_ratio(
    final_multipliers: np.ndarray,
    *,
    anomaly_dmg_ratio: float | np.float64,
) -> np.ndarray:
    """应用紊乱绽放异常伤害倍率，并保留原乘区向量对象。"""
    adjusted_vector = anomaly_damage_formulas.apply_anomaly_damage_ratio(
        MultiplierVector(final_multipliers),
        anomaly_damage_ratio=float(anomaly_dmg_ratio),
    )
    final_multipliers[:] = np.array(adjusted_vector.values, dtype=np.float64)
    return final_multipliers


class CalAnomaly:
    def __init__(
        self,
        anomaly_obj: AnomalyBar,
        enemy_obj: Enemy,
        dynamic_buff: Mapping[str, Sequence["Buff"]],
        sim_instance: "Simulator",
    ):
        """
        Schedule 节点对于异常伤害的分支逻辑，用于计算异常伤害

        调用方法 cal_anomaly_dmg() 输出.伤害期望

        异常伤害快照以 array 形式储存，顺序为：
        [基础伤害区、增伤区、异常精通区、等级、异常增伤区、异常暴击区、穿透率、穿透值、抗性穿透]
        """
        self.sim_instance = sim_instance
        self.enemy_obj = enemy_obj
        self.anomaly_obj: AnomalyBar = anomaly_obj
        if not self.anomaly_obj.settled:
            raise ValueError(
                f"即将被计算的 {ETM[self.anomaly_obj.element_type]} 异常条对象尚未结算快照，请检查前置业务逻辑"
            )
        self.dynamic_buff = dynamic_buff
        snapshot: tuple[ElementType, np.ndarray] = (
            self.anomaly_obj.element_type,
            self.anomaly_obj.current_ndarray,
        )
        self.element_type: ElementType = snapshot[0]
        # self.dmg_sp 以 array 形式储存，顺序为：基础伤害区、增伤区、异常精通区、等级、异常增伤区、异常暴击区、穿透率、穿透值、抗性穿透、冲击力、失衡值增幅
        self.dmg_sp: np.ndarray = snapshot[1]
        assert self.dmg_sp.shape == (1, 11), (
            f"tick: {self.sim_instance.tick}  异常伤害快照形状错误，期望(1, 11)，实际{self.dmg_sp}\n"
            f"其他信息：名字：{type(self.anomaly_obj).__name__}\n"
            f"属性：{self.anomaly_obj.element_type}\n"
            f"是否是紊乱：{self.anomaly_obj.is_disorder}\n"
            f"是否已经被结算：{self.anomaly_obj.settled}"
        )
        if anomaly_obj.activated_by is None:
            print(
                f"【CalAnomaly 警告】:检测到异常实例(属性类型：{anomaly_obj.element_type}）的激活源为空，该异常实例将无法享受Buff加成。"
            )
            raise NotImplementedError
        else:
            char_obj: "Character | None" = anomaly_obj.activated_by.skill.char_obj
        # 根据动态buff读取怪物面板

        self.data: MulData = MulData(
            enemy_obj=self.enemy_obj,
            dynamic_buff=self.dynamic_buff,
            judge_node=anomaly_obj,
            character_obj=char_obj,
        )
        # 虚拟角色等级
        v_char_level: int = int(
            np.floor(self.dmg_sp[0, 3] + 0.0000001)
        )  # 加一个极小的数避免精度向下丢失导致的误差

        self.v_char_level = v_char_level
        # 等级系数
        k_level = self.cal_k_level(v_char_level)

        # 激活型暴击区（目前仅简的核心被动）
        active_crit: float = self.cal_active_crit(self.data)
        # 防御区
        def_mul: np.float64 = self.cal_def_mul(self.data, v_char_level)
        # 抗性区
        res_mul: float = Cal.RegularMul.cal_res_mul(
            self.data,
            element_type=self.element_type,
            snapshot_res_pen=self.dmg_sp[0, 8],
        )
        # 减易伤区
        vulnerability_mul: float = Cal.RegularMul.cal_dmg_vulnerability(
            self.data, element_type=self.element_type
        )
        # 失衡易伤区
        stun_vulnerability: float = Cal.RegularMul.cal_stun_vulnerability(self.data)
        # 特殊乘区
        special_mul: float = Cal.RegularMul.cal_special_mul(self.data)

        imp_mul = self.dmg_sp[0, 9]
        stun_mul = self.dmg_sp[0, 10]

        self.final_multipliers: np.ndarray = self.set_final_multipliers(
            k_level,
            active_crit,
            def_mul,
            res_mul,
            vulnerability_mul,
            stun_vulnerability,
            special_mul,
            imp_mul,
            stun_mul,
        )

    @staticmethod
    def cal_k_level(v_char_level: int) -> np.float64:
        """等级区 = trunc(1+ 1/59* (等级 - 1), 4)"""
        # 定义域检查
        if v_char_level < 0:
            report_to_log(f"角色等级{v_char_level}过低，将被设置为0")
            v_char_level = 0
        elif v_char_level > 60:
            report_to_log(f"角色等级{v_char_level}过高，将被设置为60")
            v_char_level = 60
        # 查表
        # fmt: off
        values: list[float] = [
            0, 1.0000, 1.0169, 1.0338, 1.0508, 1.0677, 1.0847, 1.1016, 1.1186, 1.1355, 1.1525,
            1.1694, 1.1864, 1.2033, 1.2203, 1.2372, 1.2542, 1.2711, 1.2881, 1.3050, 1.3220,
            1.3389, 1.3559, 1.3728, 1.3898, 1.4067, 1.4237, 1.4406, 1.4576, 1.4745, 1.4915,
            1.5084, 1.5254, 1.5423, 1.5593, 1.5762, 1.5932, 1.6101, 1.6271, 1.6440, 1.6610,
            1.6779, 1.6949, 1.7118, 1.7288, 1.7457, 1.7627, 1.7796, 1.7966, 1.8135, 1.8305,
            1.8474, 1.8644, 1.8813, 1.8983, 1.9152, 1.9322, 1.9491, 1.9661, 1.9830, 2.0000
        ]
        # fmt: on
        return np.float64(values[v_char_level])

    def cal_active_crit(self, data: MulData) -> float:
        """激活型异常暴击区

        目前仅简的核心被动
        """
        if self.element_type == 0:
            crit_rate = data.dynamic.strike_crit_rate_increase
            crit_dmg = data.dynamic.strike_crit_dmg_increase
            return 1 + crit_rate * crit_dmg
        else:
            return 1

    def cal_def_mul(self, data: MulData, v_char_level) -> np.float64:
        """防御区 = 攻击方等级基数 / (受击方有效防御 + 攻击方等级基数)"""
        # 攻击方等级系数
        k_attacker: int = Cal.RegularMul.cal_k_attacker(v_char_level)
        # 计算属性/类型的穿透
        if self.element_type == 0:
            # 穿透率
            addon_pen_ratio = float(self.dmg_sp[0, 6]) + self.data.dynamic.strike_ignore_defense
            # 受击方有效防御
        else:
            addon_pen_ratio = float(self.dmg_sp[0, 6])
        # 受击方有效防御
        recipient_def: float = Cal.RegularMul.cal_recipient_def(
            data,
            Cal.RegularMul.cal_pen_ratio(data),
            addon_pen_ratio=addon_pen_ratio,
            addon_pen_numeric=float(self.dmg_sp[0, 7]),
        )
        # 计算防御区
        defense_mul = k_attacker / (recipient_def + k_attacker)
        return np.float64(defense_mul)

    def set_final_multipliers(
        self,
        k_level,
        active_crit,
        def_mul,
        res_mul,
        vulnerability_mul,
        stun_vulnerability,
        special_mul,
        imp_mul,
        stun_mul,
    ) -> np.ndarray:
        """将计算结果写入 self.final_multipliers"""
        return _assemble_final_multiplier_vector(
            self.dmg_sp,
            k_level=k_level,
            active_crit=active_crit,
            def_mul=def_mul,
            res_mul=res_mul,
            vulnerability_mul=vulnerability_mul,
            snapshot_impact=imp_mul,
            snapshot_stun_bonus=stun_mul,
            stun_vulnerability=stun_vulnerability,
            special_mul=special_mul,
        )

    def cal_anomaly_dmg(self) -> np.float64:
        """计算异常伤害期望"""
        """
        在v0.3.5a1中，由于爱丽丝的核心被动Dot会以固定比例造成属性异常伤害，
        所以我们为属性异常伤害期望计算添加了缩放比例的乘算逻辑
        """
        return _calculate_anomaly_damage_expectation(
            self.final_multipliers,
            snapshot_impact=np.float64(self.dmg_sp[0, 9]),
            snapshot_stun_bonus=np.float64(self.dmg_sp[0, 10]),
            scaling_factor=self.anomaly_obj.scaling_factor,
        )


class CalDisorder(CalAnomaly):
    def __init__(
        self,
        disorder_obj: Disorder,
        enemy_obj: Enemy,
        dynamic_buff: Mapping[str, Sequence["Buff"]],
        sim_instance: "Simulator",
    ):
        """
        异常伤害快照以 array 形式储存，顺序为：
        [基础伤害区、增伤区、异常精通区、等级、异常增伤区、异常暴击区、穿透率、穿透值、抗性穿透]
        """
        super().__init__(disorder_obj, enemy_obj, dynamic_buff, sim_instance=sim_instance)
        self.final_multipliers[0] = self.cal_disorder_base_dmg(
            np.float64(self.final_multipliers[0])
        )
        self.final_multipliers[4] = self.cal_disorder_extra_mul()

    def cal_disorder_base_dmg(self, base_mul: np.float64) -> np.float64:
        return _calculate_disorder_base_damage(
            element_type=self.element_type,
            base_mul=base_mul,
            remaining_tick=np.float64(self.anomaly_obj.remaining_tick()),
            disorder_basic_mul_map=self.data.dynamic.disorder_basic_mul_map,
        )

    def cal_disorder_extra_mul(self) -> np.float64:
        """
        计算紊乱的异常额外增伤区，即紊乱的异常增伤区。
        异常额外增伤区 = 1 + 对应属性异常额外增伤
        紊乱的额外增伤本身只有一个词条：紊乱额外伤害增幅（disorder_dmg_mul），该词条本身是对所有紊乱通用的，
        所以若是要实现“X属性紊乱伤害增幅”，则必须通过buff label的"specified_disorder_element_type"加以限制。
        """
        return _calculate_disorder_extra_multiplier(self.data.dynamic.ano_extra_bonus)

    def cal_disorder_stun(self) -> np.float64:
        imp = np.float64(self.final_multipliers[9])
        stun_res = Cal.StunMul.cal_stun_res(self.data, self.element_type)
        stun_bonus = np.float64(self.final_multipliers[10])
        stun_received = Cal.StunMul.cal_stun_received(self.data)
        return _calculate_disorder_stun_multiplier(
            impact=imp,
            snapshot_stun_bonus=stun_bonus,
            stun_res=stun_res,
            received_stun_increase=stun_received,
            v_char_level=self.v_char_level,
        )


class CalPolarityDisorder(CalDisorder):
    def __init__(
        self,
        disorder_obj: PolarityDisorder,
        enemy_obj: Enemy,
        dynamic_buff: Mapping[str, Sequence["Buff"]],
        sim_instance: "Simulator",
    ):
        super().__init__(disorder_obj, enemy_obj, dynamic_buff, sim_instance=sim_instance)
        yanagi_obj = self.__find_yanagi()
        yanagi_mul = MulData(
            enemy_obj=enemy_obj, dynamic_buff=dynamic_buff, character_obj=yanagi_obj
        )
        ap = Cal.AnomalyMul.cal_ap(yanagi_mul)
        self.final_multipliers[0] = self.cal_polarity_disorder_base_dmg(
            np.float64(self.final_multipliers[0]),
            np.float64(ap),
            polarity_disorder_ratio=disorder_obj.polarity_disorder_ratio,
            additional_dmg_ap_ratio=disorder_obj.additional_dmg_ap_ratio,
        )

    def cal_polarity_disorder_base_dmg(
        self,
        base_disorder_damage: np.float64,
        yanagi_ap: np.float64,
        *,
        polarity_disorder_ratio: float | np.float64,
        additional_dmg_ap_ratio: float | np.float64,
    ) -> np.float64:
        return _calculate_polarity_disorder_base_damage(
            base_disorder_damage=base_disorder_damage,
            yanagi_ap=yanagi_ap,
            polarity_disorder_ratio=polarity_disorder_ratio,
            additional_dmg_ap_ratio=additional_dmg_ap_ratio,
        )

    def __find_yanagi(self) -> Yanagi | None:
        yanagi_obj: Character | None = self.sim_instance.char_data.char_obj_dict.get("柳", None)
        if yanagi_obj is None or not isinstance(yanagi_obj, Yanagi):
            raise AssertionError("没柳你哪来的极性紊乱")
        return yanagi_obj


class CalAbloom(CalAnomaly):
    def __init__(
        self,
        abloom_obj: Abloom,
        enemy_obj: Enemy,
        dynamic_buff: Mapping[str, Sequence["Buff"]],
        sim_instance: "Simulator",
    ):
        super().__init__(abloom_obj, enemy_obj, dynamic_buff, sim_instance=sim_instance)
        _apply_abloom_anomaly_damage_ratio(
            self.final_multipliers,
            anomaly_dmg_ratio=abloom_obj.anomaly_dmg_ratio,
        )
