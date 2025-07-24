from typing import TYPE_CHECKING

import numpy as np

from zsim.define import ElementType
from zsim.sim_progress.anomaly_bar import AnomalyBar
from zsim.sim_progress.anomaly_bar.CopyAnomalyForOutput import (
    DirgeOfDestinyAnomaly as Abloom,
    Disorder,
    PolarityDisorder,
)
from zsim.sim_progress.Character.character import Character
from zsim.sim_progress.Character.Yanagi import Yanagi
from zsim.sim_progress.Enemy import Enemy
from zsim.sim_progress.Report import report_to_log

from .Calculator import Calculator as Cal
from .Calculator import MultiplierData as MulData

if TYPE_CHECKING:
    from zsim.simulator.simulator_class import Simulator


class CalAnomaly:
    def __init__(
        self,
        anomaly_obj: AnomalyBar,
        enemy_obj: Enemy,
        dynamic_buff: dict,
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
        self.anomaly_obj = anomaly_obj
        self.dynamic_buff = dynamic_buff
        snapshot: tuple[ElementType, np.ndarray] = (
            self.anomaly_obj.element_type,
            self.anomaly_obj.current_ndarray,
        )
        self.element_type: ElementType = snapshot[0]
        # self.dmg_sp 以 array 形式储存，顺序为：基础伤害区、增伤区、异常精通区、等级、异常增伤区、异常暴击区、穿透率、穿透值、抗性穿透、冲击力、失衡值增幅
        self.dmg_sp: np.ndarray = snapshot[1]
        if anomaly_obj.activated_by is None:
            print(f"【CalAnomaly Warnning】:检测到异常实例(属性类型：{anomaly_obj.element_type}）的激活源为空，改异常实例将无法享受Buff加成。")
        else:
            char_obj = anomaly_obj.activated_by.skill.char_obj
        # 根据动态buff读取怪物面板

        self.data: MulData = MulData(
            enemy_obj=self.enemy_obj,
            dynamic_buff=self.dynamic_buff,
            judge_node=anomaly_obj,
            character_obj=char_obj
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
            stun_mul
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
            addon_pen_ratio = (
                float(self.dmg_sp[0, 6]) + self.data.dynamic.strike_ignore_defense
            )
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
        # self.dmg_sp 以 array 形式储存，顺序为：基础伤害区、增伤区、异常精通区、等级、异常增伤区、异常暴击区、穿透率、穿透值、抗性穿透、冲击力、失衡值增幅
        base_dmg = self.dmg_sp[0, 0]
        dmg_bonus = self.dmg_sp[0, 1]
        am_mul = self.dmg_sp[0, 2]
        anomaly_bonus = self.dmg_sp[0, 4]
        active_crit = active_crit
        # 将所有乘数放入一个数组
        results = np.array(
            [
                base_dmg,
                dmg_bonus,
                am_mul,
                k_level,
                anomaly_bonus,
                active_crit,
                def_mul,
                res_mul,
                vulnerability_mul,
                imp_mul,
                stun_mul,
                stun_vulnerability,
                special_mul,
            ],
            dtype=np.float64,
        )
        return results

    def cal_anomaly_dmg(self) -> np.float64:
        """计算异常伤害期望"""

        return np.float64(np.prod(self.final_multipliers)/(self.dmg_sp[0,9] * self.dmg_sp[0,10]))


class CalDisorder(CalAnomaly):
    def __init__(
        self,
        disorder_obj: Disorder,
        enemy_obj: Enemy,
        dynamic_buff: dict,
        sim_instance: "Simulator",
    ):
        """
        异常伤害快照以 array 形式储存，顺序为：
        [基础伤害区、增伤区、异常精通区、等级、异常增伤区、异常暴击区、穿透率、穿透值、抗性穿透]
        """
        super().__init__(
            disorder_obj, enemy_obj, dynamic_buff, sim_instance=sim_instance
        )
        self.final_multipliers[0] = self.cal_disorder_base_dmg(
            np.float64(self.final_multipliers[0])
        )
        self.final_multipliers[4] = self.cal_disorder_extra_mul()

    def cal_disorder_base_dmg(self, base_mul: np.float64) -> np.float64:
        """
        计算紊乱的基础伤害

        紊乱基础伤害 = (各属性异常剩余倍率 + 各属性紊乱基础倍率) * (1 + 紊乱基础倍率增幅)
        """
        t_s = np.float64(self.anomaly_obj.remaining_tick() / 60)
        disorder_base_dmg: np.float64
        # 计算紊乱基础伤害
        match self.element_type:
            case 0:  # 强击紊乱
                disorder_base_dmg = (base_mul / 7.13) * (np.floor(t_s) * 0.075 + 4.5)
            case 1:  # 灼烧紊乱
                disorder_base_dmg = (base_mul / 0.5) * (np.floor(t_s / 0.5) * 0.5 + 4.5)
            case 2:  # 霜寒紊乱
                disorder_base_dmg = (base_mul / 5) * (np.floor(t_s) * 0.075 + 4.5)
            case 3:  # 感电紊乱
                disorder_base_dmg = (base_mul / 1.25) * (np.floor(t_s) * 1.25 + 4.5)
            case 4:  # 侵蚀紊乱
                disorder_base_dmg = (base_mul / 0.625) * (
                    np.floor(t_s / 0.5) * 0.625 + 4.5
                )
            case 5:  # 烈霜紊乱
                disorder_base_dmg = (base_mul / 5) * (np.floor(t_s) * 0.75 + 6)
            case 6:  # 玄墨侵蚀紊乱
                disorder_base_dmg = (base_mul / 0.625) * (
                    np.floor(t_s / 0.5) * 0.625 + 4.5
                )
            case _:
                assert False, f"Invalid Element Type {self.element_type}"
        # 计算紊乱基础倍率增幅
        disorder_basic_mul_map = self.data.dynamic.disorder_basic_mul_map
        disorder_base_dmg *= 1 + (
            disorder_basic_mul_map[self.element_type] + disorder_basic_mul_map["all"]
        )
        # print(f"111111，计算紊乱！{disorder_basic_mul_map}")
        return np.float64(disorder_base_dmg)

    def cal_disorder_extra_mul(self) -> np.float64:
        """计算紊乱的异常额外增伤区

        异常额外增伤区 = 1 + 对应属性异常额外增伤
        """
        map = self.data.dynamic.ano_extra_bonus
        return 1 + map[-1]

    def cal_disorder_stun(self) -> np.float64:
        imp = self.final_multipliers[9]
        stun_ratio = 2
        stun_res = Cal.StunMul.cal_stun_res(self.data, self.element_type)
        stun_bonus = self.final_multipliers[10]
        stun_received = Cal.StunMul.cal_stun_received(self.data)
        k_level_for_stun = 1 + self.v_char_level * 0.0075
        return np.float64(
            np.prod([imp, stun_ratio, stun_res, stun_bonus, stun_received, k_level_for_stun])
        )


class CalPolarityDisorder(CalDisorder):
    def __init__(
        self,
        disorder_obj: PolarityDisorder,
        enemy_obj: Enemy,
        dynamic_buff: dict,
        sim_instance: "Simulator",
    ):
        super().__init__(
            disorder_obj, enemy_obj, dynamic_buff, sim_instance=sim_instance
        )
        yanagi_obj = self.__find_yanagi()
        yanagi_mul = MulData(
            enemy_obj=enemy_obj, dynamic_buff=dynamic_buff, character_obj=yanagi_obj
        )
        ap = Cal.AnomalyMul.cal_ap(yanagi_mul)
        self.final_multipliers[0] = (
            self.final_multipliers[0] * disorder_obj.polarity_disorder_ratio
        ) + (ap * disorder_obj.additional_dmg_ap_ratio)

    def __find_yanagi(self) -> Yanagi | None:
        yanagi_obj: Yanagi | None = self.sim_instance.char_data.char_obj_dict.get(
            "柳", None
        )
        if yanagi_obj is None:
            assert False, "没柳你哪来的极性紊乱"
        return yanagi_obj


class CalAbloom(CalAnomaly):
    def __init__(
        self,
        abloom_obj: Abloom,
        enemy_obj: Enemy,
        dynamic_buff: dict,
        sim_instance: "Simulator",
    ):
        super().__init__(abloom_obj, enemy_obj, dynamic_buff, sim_instance=sim_instance)
        self.final_multipliers[0] *= abloom_obj.anomaly_dmg_ratio
