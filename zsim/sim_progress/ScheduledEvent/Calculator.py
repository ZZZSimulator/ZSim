import json
from functools import lru_cache
from typing import Any

import numpy as np

from zsim.define import INVALID_ELEMENT_ERROR, ElementType
from zsim.sim_progress.Character import Character
from zsim.sim_progress.data_struct import cal_buff_total_bonus
from zsim.sim_progress.Enemy import Enemy
from zsim.sim_progress.Preload import SkillNode
from zsim.sim_progress.Report import report_to_log
from zsim .sim_progress.anomaly_bar.AnomalyBarClass import AnomalyBar


with open(
    file="./zsim/sim_progress/ScheduledEvent/buff_effect_trans.json",
    mode="r",
    encoding="utf-8-sig",
) as f:
    buff_effect_trans: dict = json.load(f)


class MultiplierData:
    mul_data_cache: dict[tuple, "MultiplierData"] = {}
    max_size = 128

    def __new__(
        cls,
        enemy_obj: Enemy,
        dynamic_buff: dict,
        character_obj: Character | None = None,
        judge_node: SkillNode | None = None,
    ):
        hashable_dynamic_buff = tuple(
            (key, tuple(value)) for key, value in dynamic_buff.items()
        )
        enemy_hashable = (
            tuple(enemy_obj.dynamic.dynamic_debuff_list),
            tuple(enemy_obj.dynamic.dynamic_dot_list),
        )
        cache_key = tuple(
            (enemy_hashable, hashable_dynamic_buff, id(character_obj), id(judge_node))
        )
        if cache_key in cls.mul_data_cache:
            return cls.mul_data_cache[cache_key]
        else:
            instance = super().__new__(cls)
            if len(cls.mul_data_cache) >= cls.max_size:
                cls.mul_data_cache.popitem()
            cls.mul_data_cache[cache_key] = instance
            return instance

    def __init__(
        self,
        enemy_obj: Enemy,
        dynamic_buff: dict | None = None,
        character_obj: Character | None = None,
        judge_node: SkillNode | AnomalyBar | None = None,
    ):
        if dynamic_buff is None:
            dynamic_buff = {}
        if not hasattr(self, "char_name"):
            self.judge_node: SkillNode | AnomalyBar | None = judge_node
            self.enemy_instance = enemy_obj
            if character_obj is None:
                self.char_name = None
                self.char_level = None
                self.cid = None
                self.char_instance = None
            else:
                self.char_name = character_obj.NAME
                self.char_level = character_obj.level
                self.cid = character_obj.CID
                self.char_instance = character_obj

            # 获取角色局外面板数据
            static_statement: Character.Statement | None = getattr(
                character_obj, "statement", None
            )
            self.static = self.StaticStatement(
                static_statement
            )  # 按理来说静态面板在角色都没有的情况下根本没必要生成，但是屎山就是这样搭建的，尊重
            # 获取敌人数据
            self.enemy_obj = enemy_obj
            # 获取buff动态加成
            dynamic_statement: dict = self.get_buff_bonus(dynamic_buff, self.judge_node)

            self.dynamic = self.DynamicStatement(dynamic_statement)

    def get_buff_bonus(self, dynamic_buff: dict, node: SkillNode | AnomalyBar | None) -> dict:
        if self.char_name is None:
            char_buff: list = []
        else:
            try:
                char_buff = dynamic_buff[self.char_name]
            except KeyError:
                char_buff = []
                report_to_log(
                    f"[WARNING] 动态Buff列表内没有角色 {self.char_name}", level=4
                )
        try:
            enemy_buff: list = self.enemy_obj.dynamic.dynamic_debuff_list
        except AttributeError:
            report_to_log("[WARNING] self.enemy_obj 中找不到动态buff列表", level=4)
            try:
                enemy_buff = dynamic_buff["enemy"]
            except KeyError:
                report_to_log(
                    "[WARNING] dynamic_buff 中依然找不到动态buff列表", level=4
                )
                enemy_buff = []
        enabled_buff: tuple = tuple(char_buff + enemy_buff)
        dynamic_statement: dict = cal_buff_total_bonus(enabled_buff, node, sim_instance=self.enemy_obj.sim_instance, char_name=self.char_name)
        return dynamic_statement

    class StaticStatement:
        _instance_cache: dict[tuple | None, Any] = {}
        _max_cache_size = 128

        def __new__(cls, static_statement: Character.Statement | None):
            if static_statement is None:
                cache_key = None
            else:
                cache_key = tuple(sorted(static_statement.statement.items()))
            if cache_key in cls._instance_cache:
                return cls._instance_cache[cache_key]
            else:
                instance = super().__new__(cls)
                if len(cls._instance_cache) >= cls._max_cache_size:
                    cls._instance_cache.popitem()
                cls._instance_cache[cache_key] = instance
                return instance

        def __init__(self, static_statement: Character.Statement | None):
            """将角色面板抄下来！！！！！如果没有角色传入，那就生成屎！！！"""
            self.atk: float = 0.0
            self.hp: float = 0.0
            self.defense: float = 0.0
            self.imp: float = 0.0
            self.ap: float = 0.0
            self.am: float = 0.0
            self.crit_rate: float = 0.0
            self.crit_damage: float = 0.0
            self.sp_regen: float = 0.0
            self.sp_get_ratio: float = 0.0
            self.sp_limit: float = 0.0
            self.pen_ratio: float = 0.0
            self.pen_numeric: float = 0.0
            self.phy_dmg_bonus: float = 0.0
            self.ice_dmg_bonus: float = 0.0
            self.fire_dmg_bonus: float = 0.0
            self.ether_dmg_bonus: float = 0.0
            self.electric_dmg_bonus: float = 0.0

            attribute_map = {
                "atk": "ATK",
                "hp": "HP",
                "defense": "DEF",
                "imp": "IMP",
                "ap": "AP",
                "am": "AM",
                "crit_rate": "CRIT_rate",
                "crit_damage": "CRIT_damage",
                "sp_regen": "sp_regen",
                "sp_get_ratio": "sp_get_ratio",
                "sp_limit": "sp_limit",
                "pen_ratio": "PEN_ratio",
                "pen_numeric": "PEN_numeric",
                "phy_dmg_bonus": "PHY_DMG_bonus",
                "ice_dmg_bonus": "ICE_DMG_bonus",
                "fire_dmg_bonus": "FIRE_DMG_bonus",
                "ether_dmg_bonus": "ETHER_DMG_bonus",
                "electric_dmg_bonus": "ELECTRIC_DMG_bonus",
            }
            if static_statement is None:
                pass
            else:
                for attr, static_attr in attribute_map.items():
                    setattr(self, attr, getattr(static_statement, static_attr, 0.0))

    class DynamicStatement:
        def __init__(self, dynamic_statement):
            """
            buff动态加成的初始化蟑螂桶，这一百多行不是屎山，是为了IDE能认识这些傻逼玩意
            """
            self.buff_name: float = 0.0
            self.hp: float = 0.0
            self.atk: float = 0.0
            self.defense: float = 0.0
            self.imp: float = 0.0
            self.crit_rate: float = 0.0
            self.crit_dmg: float = 0.0
            self.anomaly_proficiency: float = 0.0
            self.anomaly_mastery: float = 0.0
            self.pen_ratio: float = 0.0
            self.pen_numeric: float = 0.0
            self.sp_regen: float = 0.0
            self.sp_get_ratio: float = 0.0
            self.sp_limit: float = 0.0
            self.phy_dmg_bonus: float = 0.0
            self.fire_dmg_bonus: float = 0.0
            self.ice_dmg_bonus: float = 0.0
            self.electric_dmg_bonus: float = 0.0
            self.ether_dmg_bonus: float = 0.0
            self.field_hp_percentage: float = 0.0
            self.field_atk_percentage: float = 0.0
            self.field_def_percentage: float = 0.0
            self.field_imp_percentage: float = 0.0
            self.field_crit_rate: float = 0.0
            self.field_crit_dmg: float = 0.0
            self.field_anomaly_proficiency: float = 0.0
            self.field_anomaly_mastery: float = 0.0
            self.field_pen_ratio: float = 0.0
            self.field_pen_numeric: float = 0.0
            self.field_sp_regen: float = 0.0
            self.field_sp_get_ratio: float = 0.0
            self.field_sp_limit: float = 0.0
            self.extra_damage_ratio: float = 0.0  # 基础伤害倍率

            self.phy_crit_dmg_bonus: float = 0.0
            self.fire_crit_dmg_bonus: float = 0.0
            self.ice_crit_dmg_bonus: float = 0.0
            self.electric_crit_dmg_bonus: float = 0.0
            self.ether_crit_dmg_bonus: float = 0.0

            self.phy_crit_rate_bonus: float = 0.0
            self.fire_crit_rate_bonus: float = 0.0
            self.ice_crit_rate_bonus: float = 0.0
            self.electric_crit_rate_bonus: float = 0.0
            self.ether_crit_rate_bonus: float = 0.0

            self.attack_type_dmg_bonus: float = 0.0
            self.normal_attack_dmg_bonus: float = 0.0
            self.special_skill_dmg_bonus: float = 0.0
            self.ex_special_skill_dmg_bonus: float = 0.0
            self.dash_attack_dmg_bonus: float = 0.0
            self.counter_attack_dmg_bonus: float = 0.0
            self.qte_dmg_bonus: float = 0.0
            self.ultimate_dmg_bonus: float = 0.0
            self.quick_aid_dmg_bonus: float = 0.0
            self.defensive_aid_dmg_bonus: float = 0.0
            self.assault_aid_dmg_bonus: float = 0.0
            self.anomaly_dmg_bonus: float = 0.0
            self.all_dmg_bonus: float = 0.0

            self.percentage_def_reduction: float = 0.0
            self.def_reduction: float = 0.0

            self.all_dmg_res_decrease: float = 0.0
            self.physical_dmg_res_decrease: float = 0.0
            self.fire_dmg_res_decrease: float = 0.0
            self.ice_dmg_res_decrease: float = 0.0
            self.electric_dmg_res_decrease: float = 0.0
            self.ether_dmg_res_decrease: float = 0.0

            self.all_res_pen_increase: float = 0.0
            self.physical_res_pen_increase: float = 0.0
            self.fire_res_pen_increase: float = 0.0
            self.ice_res_pen_increase: float = 0.0
            self.electric_res_pen_increase: float = 0.0
            self.ether_res_pen_increase: float = 0.0

            self.all_anomaly_res_decrease: float = 0.0
            self.physical_anomaly_res_decrease: float = 0.0
            self.fire_anomaly_res_decrease: float = 0.0
            self.ice_anomaly_res_decrease: float = 0.0
            self.electric_anomaly_res_decrease: float = 0.0
            self.ether_anomaly_res_decrease: float = 0.0

            self.received_crit_dmg_bonus: float = 0.0
            self.crit_rate_received_increase: float = 0.0

            self.physical_vulnerability: float = 0.0
            self.fire_vulnerability: float = 0.0
            self.ice_vulnerability: float = 0.0
            self.electric_vulnerability: float = 0.0
            self.ether_vulnerability: float = 0.0
            self.anomaly_vulnerability: float = 0.0
            self.all_vulnerability: float = 0.0

            self.stun_res: float = 0.0
            self.stun_bonus: float = 0.0
            self.received_stun_increase: float = 0.0
            self.stun_vulnerability_increase: float = 0.0
            self.stun_vulnerability_increase_all_time: float = 0.0

            self.normal_attack_stun_bonus: float = 0.0
            self.special_skill_stun_bonus: float = 0.0
            self.ex_special_skill_stun_bonus: float = 0.0
            self.dash_attack_stun_bonus: float = 0.0
            self.counter_attack_stun_bonus: float = 0.0
            self.qte_stun_bonus: float = 0.0
            self.ultimate_stun_bonus: float = 0.0
            self.quick_aid_stun_bonus: float = 0.0
            self.defensive_aid_stun_bonus: float = 0.0
            self.assault_aid_stun_bonus: float = 0.0

            self.physical_anomaly_buildup_bonus: float = 0.0
            self.fire_anomaly_buildup_bonus: float = 0.0
            self.ice_anomaly_buildup_bonus: float = 0.0
            self.electric_anomaly_buildup_bonus: float = 0.0
            self.ether_anomaly_buildup_bonus: float = 0.0
            self.frost_anomaly_buildup_bonus: float = 0.0
            self.all_anomaly_buildup_bonus: float = 0.0

            self.normal_attack_anomaly_buildup_bonus: float = 0.0
            self.special_skill_anomaly_buildup_bonus: float = 0.0
            self.ex_special_skill_anomaly_buildup_bonus: float = 0.0
            self.dash_attack_anomaly_buildup_bonus: float = 0.0
            self.counter_attack_anomaly_buildup_bonus: float = 0.0
            self.qte_anomaly_buildup_bonus: float = 0.0
            self.ultimate_anomaly_buildup_bonus: float = 0.0
            self.quick_aid_anomaly_buildup_bonus: float = 0.0
            self.defensive_aid_anomaly_buildup_bonus: float = 0.0
            self.assault_aid_anomaly_buildup_bonus: float = 0.0

            self.assault_dmg_mul: float = 0.0
            self.burn_dmg_mul: float = 0.0
            self.freeze_dmg_mul: float = 0.0
            self.shock_dmg_mul: float = 0.0
            self.chaos_dmg_mul: float = 0.0
            self.disorder_dmg_mul: float = 0.0
            self.all_anomaly_dmg_mul: float = 0.0

            self.ano_extra_bonus: dict[ElementType | str, float] = {
                0: self.assault_dmg_mul,
                1: self.burn_dmg_mul,
                2: self.freeze_dmg_mul,
                3: self.shock_dmg_mul,
                4: self.chaos_dmg_mul,
                5: self.freeze_dmg_mul,
                -1: self.disorder_dmg_mul,
                "all": self.all_anomaly_dmg_mul,
            }

            self.special_multiplier_zone: float = 0.0

            self.stun_tick_increase: int = 0

            self.base_dmg_increase: float = 0.0
            self.base_dmg_increase_percentage: float = 0.0

            self.aftershock_attack_dmg_bonus: float = 0.0
            self.aftershock_attack_crit_dmg_bonus: float = 0.0
            self.aftershock_attack_stun_bonus: float = 0.0

            self.assault_time_increase: float = 0.0
            self.assault_time_increase_percentage: float = 0.0
            self.burn_time_increase: float = 0.0
            self.burn_time_increase_percentage: float = 0.0
            self.shock_time_increase: float = 0.0
            self.shock_time_increase_percentage: float = 0.0
            self.corruption_time_increase: float = 0.0
            self.corruption_time_increase_percentage: float = 0.0
            self.frostbite_time_increase: float = 0.0
            self.frostbite_time_increase_percentage: float = 0.0
            self.frost_frostbite_time_increase: float = 0.0
            self.frost_frostbite_time_increase_percentage: float = 0.0
            self.all_anomaly_time_increase: float = 0.0
            self.all_anomaly_time_increase_percentage: float = 0.0

            self.anomaly_time_increase: dict[ElementType | str, float] = {
                0: self.assault_time_increase,
                1: self.burn_time_increase,
                2: self.shock_time_increase,
                3: self.frostbite_time_increase,
                4: self.corruption_time_increase,
                5: self.frost_frostbite_time_increase,
                "all": self.all_anomaly_time_increase,
            }

            self.anomaly_time_increase_percentage: dict[ElementType | str, float] = {
                0: self.assault_time_increase_percentage,
                1: self.burn_time_increase_percentage,
                2: self.shock_time_increase_percentage,
                3: self.frostbite_time_increase_percentage,
                4: self.corruption_time_increase_percentage,
                5: self.frost_frostbite_time_increase_percentage,
                "all": self.all_anomaly_time_increase_percentage,
            }

            self.strike_crit_rate_increase: float = 0.0
            self.strike_crit_dmg_increase: float = 0.0
            self.strike_ignore_defense: float = 0.0

            # 异常其他属性
            self.strike_crit_rate_increase: float = 0.0
            self.strike_crit_dmg_increase: float = 0.0
            self.strike_ignore_defense: float = 0.0

            self.all_disorder_basic_mul: float = 0.0
            self.strike_disorder_basic_mul: float = 0.0
            self.burn_disorder_basic_mul: float = 0.0
            self.frostbite_disorder_basic_mul: float = 0.0
            self.shock_disorder_basic_mul: float = 0.0
            self.chaos_disorder_basic_mul: float = 0.0

            self.disorder_basic_mul_map: dict[ElementType | str, float] = {
                0: self.strike_disorder_basic_mul,
                1: self.burn_disorder_basic_mul,
                2: self.frostbite_disorder_basic_mul,
                3: self.shock_disorder_basic_mul,
                4: self.chaos_disorder_basic_mul,
                5: self.frostbite_disorder_basic_mul,
                6: self.chaos_disorder_basic_mul,
                "all": self.all_disorder_basic_mul,
            }
            self.sheer_atk: float = 0.0  # 固定贯穿力增幅
            self.field_sheer_atk_percentage: float = 0.0  # 局内百分比贯穿力增幅
            self.sheer_dmg_bonus: float = 0.0  # 贯穿伤害增加

            self.__read_dynamic_statement(dynamic_statement)

        def __read_dynamic_statement(self, dynamic_statement: dict) -> None:
            """使用翻译json初始化动态面板"""
            # 打开buff_effect_trans.json

            # 确保所有的属性都有默认值
            # for value in buff_effect_trans.values():
            #     if not hasattr(self, value):
            #         setattr(self, value, 0.0)
            # 遍历dynamic_statement，根据json翻译，设置对应的属性值
            for key, value in dynamic_statement.items():
                if key in buff_effect_trans:
                    attr_name = buff_effect_trans[key]
                    setattr(self, attr_name, getattr(self, attr_name) + value)
                else:
                    raise KeyError(f"Invalid buff multiplier key: {key}")


class Calculator:
    def __init__(
        self,
        skill_node: SkillNode,
        character_obj: Character,
        enemy_obj: Enemy,
        dynamic_buff: dict | None = None,
    ):
        """
        Calculator 是 Schedule 阶段获得 SkillNode 后的计算处理逻辑

        当计划事件读取到 SkillNode 时，Calculator 会根据目前的角色的面板、enemy 对象、角色的动态buff，
        计算出角色的直伤、异常、失衡的各乘区，并根据需求计算出输出、异常值、异常快照、失衡值
        """
        if dynamic_buff is None:
            dynamic_buff = {}

        if not isinstance(skill_node, SkillNode):
            raise ValueError("错误的参数类型，应该为SkillNode")
        if not isinstance(character_obj, Character):
            raise ValueError("错误的参数类型，应该为Character")
        if not isinstance(enemy_obj, Enemy):
            raise ValueError("错误的参数类型，应该为Enemy")
        if not isinstance(dynamic_buff, dict):
            raise ValueError("错误的参数类型，应该为dict")

        # 创建MultiplierData对象，用于计算各种战斗中的乘区数据
        data = MultiplierData(enemy_obj, dynamic_buff, character_obj, skill_node)

        # 初始化角色名称和角色ID

        self.char_name: str | None = data.char_name
        self.cid: int | None = data.cid
        self.skill_node = skill_node
        self.element_type = data.judge_node.element_type
        self.skill_tag = data.judge_node.skill_tag

        # 初始化各种乘区
        self.regular_multipliers = self.RegularMul(data)
        self.anomaly_multipliers = self.AnomalyMul(data)
        self.stun_multipliers = self.StunMul(data)

        # 处理失衡时间增加
        self.update_stun_tick(enemy_obj, data)

    class RegularMul:
        """
        负责计算与储存与常规直伤有关的属性

        常规直伤 = 基础伤害区 * 增伤区 * 暴击区 * 防御区 * 抗性区 * 减易伤区 * 失衡易伤区 * 特殊乘区
        """

        def __init__(self, data: MultiplierData):
            self.base_dmg = self.cal_base_dmg(data)
            self.dmg_bonus = self.cal_dmg_bonus(data)
            self.crit_rate = self.cal_crit_rate(data)
            self.crit_dmg = self.cal_crit_dmg(data)
            self.crit_expect = self.cal_crit_expect(data)
            self.defense_mul = self.cal_defense_mul(data)
            self.res_mul = self.cal_res_mul(data)
            self.dmg_vulnerability = self.cal_dmg_vulnerability(data)
            self.stun_vulnerability = self.cal_stun_vulnerability(data)
            self.special_multiplier_zone = self.cal_special_mul(data)
            self.sheer_dmg_bonus = self.cal_sheer_dmg_bonus(data)
            # 常规伤害
            self.regular_dmg_multipliers = {
                "基础伤害区": self.base_dmg,
                "增伤区": self.dmg_bonus,
                "暴击率": self.crit_rate,
                "暴击伤害": self.crit_dmg,
                "暴击期望": self.crit_expect,
                "防御区": self.defense_mul,
                "抗性区": self.res_mul,
                "减易伤区": self.dmg_vulnerability,
                "失衡易伤区": self.stun_vulnerability,
                "特殊倍率区": self.special_multiplier_zone,
                "贯穿伤害区": self.sheer_dmg_bonus,
            }

        def get_array_expect(self) -> np.ndarray:
            array_expect: np.ndarray = np.array(
                [
                    self.base_dmg,
                    self.dmg_bonus,
                    self.crit_expect,
                    self.defense_mul,
                    self.res_mul,
                    self.dmg_vulnerability,
                    self.stun_vulnerability,
                    self.special_multiplier_zone,
                    self.sheer_dmg_bonus,
                ],
                dtype=np.float64,
            )
            return array_expect

        def get_array_crit(self) -> np.ndarray:
            when_crit_mul = 1 + self.crit_dmg
            array_crit: np.ndarray = np.array(
                [
                    self.base_dmg,
                    self.dmg_bonus,
                    when_crit_mul,
                    self.defense_mul,
                    self.res_mul,
                    self.dmg_vulnerability,
                    self.stun_vulnerability,
                    self.special_multiplier_zone,
                    self.sheer_dmg_bonus,
                ],
                dtype=np.float64,
            )
            return array_crit

        def get_array_not_crit(self) -> np.ndarray:
            array_no_crit: np.ndarray = np.array(
                [
                    self.base_dmg,
                    self.dmg_bonus,
                    1,
                    self.defense_mul,
                    self.res_mul,
                    self.dmg_vulnerability,
                    self.stun_vulnerability,
                    self.special_multiplier_zone,
                    self.sheer_dmg_bonus,
                ],
                dtype=np.float64,
            )
            return array_no_crit

        def cal_base_dmg(self, data: MultiplierData) -> float:
            """
            基础伤害区 = 伤害倍率 * 对应属性

            如非特殊注明，代理人技能的伤害倍率都是基于自身攻击力的，在代理人的技能页面可以轻易查阅技能的伤害倍率，
            玩家也可以在战斗中于暂停菜单中看到技能的伤害倍率。
            而代理人的攻击力也可以在代理人页面或战斗中的暂停菜单中查阅，当然考虑到战斗中可能存在的各种Buff，
            实时的伤害计算请关注战斗中实际的攻击力数值。
            """
            assert data.judge_node is not None, "非法的调用，没有获取到skill node"
            # 伤害倍率 = 技能伤害倍率 / 攻击次数
            dmg_ratio = data.judge_node.skill.damage_ratio / data.judge_node.hit_times
            # 获取伤害对应属性
            base_attr = data.judge_node.skill.diff_multiplier
            # 属性为攻击力
            attr = self.cal_base_attr(base_attr, data)
            base_dmg = ((dmg_ratio + data.dynamic.extra_damage_ratio) * attr) * (
                1 + data.dynamic.base_dmg_increase_percentage
            ) + data.dynamic.base_dmg_increase
            return base_dmg

        def cal_base_attr(self, base_attr: int, data: MultiplierData):
            """根据base_attr来计算对应属性的值"""
            if base_attr == 0:
                # 攻击力 = 局外攻击力 * 局内百分比攻击力 + 局内固定攻击力
                attr = (
                    data.static.atk * (1 + data.dynamic.field_atk_percentage)
                    + data.dynamic.atk
                )
            # 属性为生命值
            elif base_attr == 1:
                attr = (
                    data.static.hp * (1 + data.dynamic.field_hp_percentage)
                    + data.dynamic.hp
                )
            # 属性为防御力
            elif base_attr == 2:
                attr = (
                    data.static.defense * (1 + data.dynamic.field_def_percentage)
                    + data.dynamic.defense
                )
            # 属性为精通
            elif base_attr == 3:
                attr = (
                    data.static.am * (1 + data.dynamic.anomaly_mastery)
                    + data.dynamic.field_anomaly_mastery
                )
            elif base_attr == 4:
                #  贯穿力属性的实时计算
                if not hasattr(data.char_instance, "sheer_attack_conversion_rate"):
                    raise AttributeError(
                        f"{data.char_instance.NAME}作为命破属性代理人，必须拥有贯穿力转化字典！"
                    )
                base_sheer_atk = 0
                for (
                    key,
                    value,
                ) in data.char_instance.sheer_attack_conversion_rate.items():
                    if key not in [0, 1, 2, 3]:
                        raise ValueError(f"无法解析的贯穿力转化率key：{key}")
                    if value <= 0:
                        continue
                    base_sheer_atk += (
                        self.cal_base_attr(base_attr=key, data=data) * value
                    )
                else:
                    if data.dynamic.field_sheer_atk_percentage != 0:
                        raise ValueError(
                            "警告！检测到非0的“局内贯穿力%Buff”，该效果目前还无法处理，请注意检查buff_effect"
                        )
                    current_sheer_atk = base_sheer_atk + data.dynamic.sheer_atk
                    attr = current_sheer_atk
                    # if data.dynamic.sheer_atk != 0:
                    #     print(f"检测到 {data.char_instance.NAME} 的局内固定贯穿力Buff：{data.dynamic.sheer_atk}, 基础贯穿力：{base_sheer_atk}")
            else:
                assert False, INVALID_ELEMENT_ERROR
            return attr

        @staticmethod
        def cal_dmg_bonus(data: MultiplierData) -> float:
            """
            增伤区 = 100% + 属性增伤 + 伤害类型增伤 + 进攻类型增伤 + 全类型增伤

            增伤区包含游戏中各种百分比形式的伤害提升/加成，造成伤害降低同样作用于该乘区，理解为负的增伤即可。
            属性增伤即针对游戏中5种伤害属性(火(Fire)、电(Electric)、冰(Ice)、物理(Physical)和以太(Ether))的伤害加成。属性增伤常见于驱动盘位的主属性和音擎效果。
            伤害类型增伤包括针对于各类技能(如普通攻击，强化特殊技，终结技等)的增伤。常见于音擎效果和鸣徽效果中。
            进攻类型增伤即针对于角色进攻类型(斩击(Slash)、打击(Strike)和穿透(Pierce))的增伤。全类型增伤就是未作类型限定的增伤。
            """
            element_type = data.judge_node.element_type
            # 获取属性伤害加成，初始化为1.0
            if element_type == 0:
                element_dmg_bonus = (
                    data.static.phy_dmg_bonus + data.dynamic.phy_dmg_bonus
                )
            elif element_type == 1:
                element_dmg_bonus = (
                    data.static.fire_dmg_bonus + data.dynamic.fire_dmg_bonus
                )
            elif element_type == 3:
                element_dmg_bonus = (
                    data.static.electric_dmg_bonus + data.dynamic.electric_dmg_bonus
                )
            elif element_type == 2 or element_type == 5:
                element_dmg_bonus = (
                    data.static.ice_dmg_bonus + data.dynamic.ice_dmg_bonus
                )
            elif element_type in [4, 6]:
                element_dmg_bonus = (
                    data.static.ether_dmg_bonus + data.dynamic.ether_dmg_bonus
                )
            else:
                raise ValueError(
                    f"Invalid element type: {element_type}, must be a integer in 0~6"
                )
            # 获取指定Tag增伤
            trigger_buff_level = data.judge_node.skill.trigger_buff_level
            if trigger_buff_level == 0:
                trigger_dmg_bonus = data.dynamic.normal_attack_dmg_bonus
            elif trigger_buff_level == 1:
                trigger_dmg_bonus = data.dynamic.special_skill_dmg_bonus
            elif trigger_buff_level == 2:
                trigger_dmg_bonus = data.dynamic.ex_special_skill_dmg_bonus
            elif trigger_buff_level == 3:
                trigger_dmg_bonus = data.dynamic.dash_attack_dmg_bonus
            elif trigger_buff_level == 4:
                trigger_dmg_bonus = data.dynamic.counter_attack_dmg_bonus
            elif trigger_buff_level == 5:
                trigger_dmg_bonus = data.dynamic.qte_dmg_bonus
            elif trigger_buff_level == 6:
                trigger_dmg_bonus = data.dynamic.ultimate_dmg_bonus
            elif trigger_buff_level == 7:
                trigger_dmg_bonus = data.dynamic.quick_aid_dmg_bonus
            elif trigger_buff_level == 8:
                trigger_dmg_bonus = data.dynamic.defensive_aid_dmg_bonus
            elif trigger_buff_level == 9:
                trigger_dmg_bonus = data.dynamic.assault_aid_dmg_bonus
            elif trigger_buff_level == 10:
                trigger_dmg_bonus = 0
            else:
                assert False, "Invalid trigger_level"
            # 获取指定label增伤
            if (
                data.judge_node.skill.labels is not None
                and data.judge_node.skill.labels.get("aftershock_attack") == 1
            ):
                label_dmg_bonus = data.dynamic.aftershock_attack_dmg_bonus
            else:
                label_dmg_bonus = 0
            dmg_bonus = (
                1
                + element_dmg_bonus
                + trigger_dmg_bonus
                + label_dmg_bonus
                + data.dynamic.all_dmg_bonus
            )
            # if "Cinema_1" in data.judge_node.skill_tag:
            #     print(element_dmg_bonus, trigger_dmg_bonus, label_dmg_bonus, data.dynamic.all_dmg_bonus)
            # if "1291_CorePassive" in data.judge_node.skill_tag:
            #     print(
            #         f"元素类增伤：{element_dmg_bonus}, 技能类型增伤：{trigger_dmg_bonus}, 标签增伤：{label_dmg_bonus}, 全类型增伤：{data.dynamic.all_dmg_bonus}",
            #     )
            return dmg_bonus

        @staticmethod
        def cal_crit_rate(data: MultiplierData) -> float:
            """暴击率 = 面板暴击率 + buff暴击率 + 受暴击概率增加"""
            crit_rate = (
                data.static.crit_rate
                + data.dynamic.crit_rate
                + data.dynamic.field_crit_rate
                + data.dynamic.crit_rate_received_increase
            )
            return crit_rate

        @staticmethod
        def cal_personal_crit_rate(data: MultiplierData) -> float:
            """个人实时暴击率 = 面板暴击率 + buff暴击率"""
            crit_rate = (
                data.static.crit_rate
                + data.dynamic.crit_rate
                + data.dynamic.field_crit_rate
            )
            return crit_rate

        @staticmethod
        def cal_crit_dmg(data: MultiplierData) -> float:
            """暴击伤害 = 静态面板暴击伤害 + buff暴击伤害 + 受暴击伤害增加"""
            # 获取指定label暴伤
            if (
                data.judge_node.skill.labels is not None
                and data.judge_node.skill.labels.get("aftershock_attack") == 1
            ):
                label_crit_dmg_bonus = data.dynamic.aftershock_attack_crit_dmg_bonus
            else:
                label_crit_dmg_bonus = 0

            buff_crit_dmg_bonus = (
                data.dynamic.crit_dmg
                + data.dynamic.field_crit_dmg
                + label_crit_dmg_bonus
            )

            crit_dmg = (
                data.static.crit_damage
                + buff_crit_dmg_bonus
                + data.dynamic.received_crit_dmg_bonus
            )
            return min(5, crit_dmg)

        def cal_crit_expect(self, data: MultiplierData) -> float:
            """暴击期望 = 1 + 暴击率 * 暴击伤害"""
            if (
                data.char_instance is not None
                and data.char_instance.crit_balancing
                and self.crit_rate > 1
            ):
                # 目前不使用溢出补偿
                return 1 + min(1, self.crit_rate) * self.crit_dmg
                # 配平算法下的暴击溢出补偿，为了解决配平仅能适配静态面板的问题
                # return 1 + ((self.crit_rate - 1) * 2 + self.crit_dmg)
            else:
                return 1 + min(1, self.crit_rate) * self.crit_dmg

        @staticmethod
        def cal_personal_crit_dmg(data: MultiplierData) -> float:
            """面板暴击伤害 = 静态面板暴击伤害 + buff暴击伤害"""
            personal_crit_dmg = (
                data.static.crit_damage
                + data.dynamic.crit_dmg
                + data.dynamic.field_crit_dmg
            )
            return personal_crit_dmg

        def cal_defense_mul(self, data: MultiplierData) -> float:
            """
            防御区 = 攻击方等级基数 / (受击方有效防御 + 攻击方等级基数)
            当检测到攻击属性为4时，说明是贯穿伤害，无视防御区，所以直接返回1

            受击方有效防御 = 受击方防御 * (1 - 攻击方穿透率%) - 攻击方穿透值 ≥ 0
            受击方防御 = (基础防御 * (1 + 战斗外防御%) + 战斗外固定防御) * (1 + 防御加成% - 防御降低%) + 固定防御
            """
            base_attr = data.judge_node.skill.diff_multiplier
            if base_attr != 4:
                attacker_level: int = (
                    data.char_level if data.char_level is not None else 1
                )
                # 攻击方等级系数
                k_attacker = self.cal_k_attacker(attacker_level)
                # 穿透率
                pen_ratio = self.cal_pen_ratio(data)
                # 受击方有效防御
                effective_def = self.cal_recipient_def(data, pen_ratio)
                # 防御区
                defense_mul = k_attacker / (effective_def + k_attacker)
            else:
                defense_mul = 1
            return defense_mul

        @staticmethod
        def cal_recipient_def(
            data: MultiplierData,
            pen_ratio: float,
            *,
            addon_pen_ratio: float = 0.0,
            addon_pen_numeric: float = 0.0,
        ) -> float:
            # 受击方防御
            recipient_def = (
                data.enemy_obj.max_DEF * (1 - data.dynamic.percentage_def_reduction)
                - data.dynamic.def_reduction
            )
            # 穿透值
            pen_numeric: float = (
                data.static.pen_numeric + data.dynamic.pen_numeric + addon_pen_numeric
            )
            # 受击方有效防御
            effective_def: float = max(
                0.0, recipient_def * (1 - pen_ratio - addon_pen_ratio) - pen_numeric
            )
            return effective_def

        @staticmethod
        def cal_pen_ratio(data: MultiplierData, *, addon_pen_ratio=0.0):
            return data.static.pen_ratio + data.dynamic.pen_ratio + addon_pen_ratio

        @staticmethod
        def cal_k_attacker(attacker_level: int) -> int:
            # 定义域检查
            if attacker_level < 0:
                report_to_log(f"角色等级{attacker_level}过低，将被设置为0")
                attacker_level = 0
            elif attacker_level > 60:
                report_to_log(f"角色等级{attacker_level}过高，将被设置为60")
                attacker_level = 60
            # 攻击方等级系数
            # fmt: off
            values: list[int] = [
                0, 50, 54, 58, 62, 66, 71, 76, 82, 88, 94,
                100, 107, 114, 121, 129, 137, 145, 153, 162,
                172, 181, 191, 201, 211, 222, 233, 245, 258,
                268, 281, 293, 306, 319, 333, 347, 362, 377,
                393, 409, 421, 436, 452, 469, 485, 502, 519,
                537, 556, 573, 592, 612, 629, 649, 669, 689,
                709, 730, 751, 772, 794,
            ]
            # fmt: on
            k_attacker = values[attacker_level]
            return k_attacker

        @staticmethod
        def cal_res_mul(
            data: MultiplierData,
            *,
            element_type: ElementType | None = None,
            snapshot_res_pen=0,
        ) -> float:
            """抗性区 = 1 - 受击方抗性 + 受击方抗性降低 + 攻击方抗性穿透"""
            if element_type is None:
                element_type = data.judge_node.element_type
            # 获取抗性区，初始化为0
            if element_type == 0:
                element_res = (
                    data.enemy_obj.PHY_damage_resistance
                    - data.dynamic.physical_dmg_res_decrease
                    - data.dynamic.physical_res_pen_increase
                )
            elif element_type == 1:
                element_res = (
                    data.enemy_obj.FIRE_damage_resistance
                    - data.dynamic.fire_dmg_res_decrease
                    - data.dynamic.fire_res_pen_increase
                )
            elif element_type == 2 or element_type == 5:
                element_res = (
                    data.enemy_obj.ICE_damage_resistance
                    - data.dynamic.ice_dmg_res_decrease
                    - data.dynamic.ice_res_pen_increase
                )
            elif element_type == 3:
                element_res = (
                    data.enemy_obj.ELECTRIC_damage_resistance
                    - data.dynamic.electric_dmg_res_decrease
                    - data.dynamic.electric_res_pen_increase
                )
            elif element_type in [4, 6]:
                element_res = (
                    data.enemy_obj.ETHER_damage_resistance
                    - data.dynamic.ether_dmg_res_decrease
                    - data.dynamic.ether_res_pen_increase
                )
            else:
                assert False, INVALID_ELEMENT_ERROR
            res_mul = (
                1
                - element_res
                + data.dynamic.all_dmg_res_decrease
                + data.dynamic.all_res_pen_increase
                + snapshot_res_pen
            )
            # if snapshot_res_pen == 0:
            #     if isinstance(data.judge_node, SkillNode) and data.judge_node.char_name == "仪玄" and data.judge_node.skill.trigger_buff_level in [2, 6]:
            #         print(element_res, data.dynamic.all_dmg_res_decrease, data.dynamic.all_res_pen_increase)
            return res_mul

        @staticmethod
        def cal_dmg_vulnerability(
            data: MultiplierData, *, element_type: ElementType | None = None
        ) -> float:
            """
            减易伤区 = 1 + 减易伤
            """
            if element_type is None:
                element_type = data.judge_node.element_type
            # 获取抗性区，初始化为0
            if element_type == 0:
                element_vulnerability = data.dynamic.physical_vulnerability
            elif element_type == 1:
                element_vulnerability = data.dynamic.fire_vulnerability
            elif element_type == 2 or element_type == 5:
                element_vulnerability = data.dynamic.ice_vulnerability
            elif element_type == 3:
                element_vulnerability = data.dynamic.electric_vulnerability
            elif element_type in [4, 6]:
                element_vulnerability = data.dynamic.ether_vulnerability
            else:
                assert False, INVALID_ELEMENT_ERROR
            dmg_vulnerability = (
                1 + element_vulnerability + data.dynamic.all_vulnerability
            )
            return dmg_vulnerability

        @staticmethod
        def cal_stun_vulnerability(data: MultiplierData) -> float:
            """
            失衡时：失衡易伤区 = 1 + 怪物失衡易伤 + 失衡易伤增幅 + 全时段失衡易伤（扳机核心被动那种）
            非失衡时：失衡易伤区 = 1 + 全时段失衡易伤（扳机核心被动那种）
            """
            stun_status: bool = data.enemy_obj.dynamic.stun
            if stun_status:
                stun_vulnerability = (
                    1
                    + data.enemy_obj.stun_DMG_take_ratio
                    + data.dynamic.stun_vulnerability_increase
                    + data.dynamic.stun_vulnerability_increase_all_time
                )
            else:
                stun_vulnerability = (
                    1 + data.dynamic.stun_vulnerability_increase_all_time
                )
            return stun_vulnerability

        @staticmethod
        def cal_special_mul(data: MultiplierData) -> float:
            return 1 + data.dynamic.special_multiplier_zone

        @staticmethod
        def cal_sheer_dmg_bonus(data: MultiplierData) -> float:
            """计算贯穿伤害增幅区——贯穿伤害增加是一个独立乘区！"""
            if data.judge_node.skill.diff_multiplier != 4:
                return 1.0
            else:
                return 1 + data.dynamic.sheer_dmg_bonus

    class AnomalyMul:
        """
        负责计算与储存与异常伤害有关的属性

        异常伤害快照以 array 形式储存，顺序为：
        [基础伤害区、增伤区、异常精通区、等级、异常增伤区、异常暴击区、穿透率、穿透值、抗性穿透]

        异常积蓄值 = 基础积蓄值 * 异常掌控/100 * (1 + 属性异常积蓄效率提升) * (1 - 属性异常积蓄抗性)
        基础伤害区 = 攻击力 * 对应属性的异常伤害倍率
        增伤区 = 1 + 属性增伤 + 全增伤
        异常精通区 = 异常精通 / 100
        等级 = 角色等级
        异常增伤区 = 单独异常增伤
        异常暴击区 单独考虑简一个角色
        """

        def __init__(self, data: MultiplierData):
            self.element_type: ElementType = data.judge_node.element_type
            self.anomaly_buildup: np.float64 = self.cal_anomaly_buildup(data)

            self.base_damage: float = self.cal_base_damage(data)
            self.dmg_bonus: float = self.cal_dmg_bonus(data)
            self.ap_mul: float = self.cal_ap_mul(data)
            self.level: int = data.char_level if data.char_level is not None else 0
            self.anomaly_bonus: float = self.cal_ano_extra_mul(data)
            self.anomaly_crit: float = self.cal_anomaly_crit(data)
            self.pen_ratio: float = data.static.pen_ratio + data.dynamic.pen_ratio
            self.pen_numeric: float = data.static.pen_numeric + data.dynamic.pen_numeric
            self.res_pen: float = self.cal_res_pen(data)

            self.anomaly_snapshot = np.array(
                [
                    self.base_damage,
                    self.dmg_bonus,
                    self.ap_mul,
                    self.level,
                    self.anomaly_bonus,
                    self.anomaly_crit,
                    self.pen_ratio,
                    self.pen_numeric,
                    self.res_pen,
                ],
                dtype=np.float64,
            )

        @staticmethod
        def cal_am(data: MultiplierData) -> np.float64:
            am = np.float64(
                data.static.am * (1 + data.dynamic.field_anomaly_mastery)
                + data.dynamic.anomaly_mastery
            )
            return am

        @staticmethod
        def cal_anomaly_buildup(data: MultiplierData) -> np.float64:
            """异常积蓄值 = 基础积蓄值 * 异常掌控/100 * (1 + 属性异常积蓄效率提升) * (1 - 属性异常积蓄抗性)"""
            # 基础蓄积值
            accumulation = data.judge_node.skill.anomaly_accumulation
            # 异常掌控
            am = Calculator.AnomalyMul.cal_am(data)
            # 属性异常积蓄效率提升、属性异常积蓄抗性
            element_type = data.judge_node.element_type

            enemy_buildup_res = data.enemy_obj.anomaly_resistance_dict.get(
                element_type, 0
            )

            if element_type == 0:
                element_buildup_bonus = (
                    data.dynamic.physical_anomaly_buildup_bonus
                    + data.dynamic.all_anomaly_buildup_bonus
                )
                buildup_res = (
                    1 - data.dynamic.physical_anomaly_res_decrease - enemy_buildup_res
                )
            elif element_type == 1:
                element_buildup_bonus = (
                    data.dynamic.fire_anomaly_buildup_bonus
                    + data.dynamic.all_anomaly_buildup_bonus
                )
                buildup_res = (
                    1 - data.dynamic.fire_anomaly_res_decrease - enemy_buildup_res
                )
            elif element_type == 2:
                element_buildup_bonus = (
                    data.dynamic.ice_anomaly_buildup_bonus
                    + data.dynamic.all_anomaly_buildup_bonus
                )
                buildup_res = (
                    1 - data.dynamic.ice_anomaly_res_decrease - enemy_buildup_res
                )
            elif element_type == 3:
                element_buildup_bonus = (
                    data.dynamic.electric_anomaly_buildup_bonus
                    + data.dynamic.all_anomaly_buildup_bonus
                )
                buildup_res = (
                    1 - data.dynamic.electric_anomaly_res_decrease - enemy_buildup_res
                )
            elif element_type in [4, 6]:
                element_buildup_bonus = (
                    data.dynamic.ether_anomaly_buildup_bonus
                    + data.dynamic.all_anomaly_buildup_bonus
                )
                buildup_res = (
                    1 - data.dynamic.ether_anomaly_res_decrease - enemy_buildup_res
                )
            elif element_type == 5:
                element_buildup_bonus = (
                    data.dynamic.frost_anomaly_buildup_bonus
                    + data.dynamic.all_anomaly_buildup_bonus
                )
                buildup_res = (
                    1 - data.dynamic.ice_anomaly_res_decrease - enemy_buildup_res
                )
            else:
                assert False, INVALID_ELEMENT_ERROR

            trigger_buff_level = data.judge_node.skill.trigger_buff_level
            if trigger_buff_level == 0:
                trigger_buildup_bonus = data.dynamic.normal_attack_anomaly_buildup_bonus
            elif trigger_buff_level == 1:
                trigger_buildup_bonus = data.dynamic.special_skill_anomaly_buildup_bonus
            elif trigger_buff_level == 2:
                trigger_buildup_bonus = (
                    data.dynamic.ex_special_skill_anomaly_buildup_bonus
                )
            elif trigger_buff_level == 3:
                trigger_buildup_bonus = data.dynamic.dash_attack_anomaly_buildup_bonus
            elif trigger_buff_level == 4:
                trigger_buildup_bonus = (
                    data.dynamic.counter_attack_anomaly_buildup_bonus
                )
            elif trigger_buff_level == 5:
                trigger_buildup_bonus = data.dynamic.qte_anomaly_buildup_bonus
            elif trigger_buff_level == 6:
                trigger_buildup_bonus = data.dynamic.ultimate_anomaly_buildup_bonus
            elif trigger_buff_level == 7:
                trigger_buildup_bonus = data.dynamic.quick_aid_anomaly_buildup_bonus
            elif trigger_buff_level == 8:
                trigger_buildup_bonus = data.dynamic.defensive_aid_anomaly_buildup_bonus
            elif trigger_buff_level == 9:
                trigger_buildup_bonus = data.dynamic.assault_aid_anomaly_buildup_bonus
            elif trigger_buff_level == 10:
                trigger_buildup_bonus = 0
            else:
                assert False, INVALID_ELEMENT_ERROR

            element_dmg_percentage = data.judge_node.skill.element_damage_percent

            hit_times = data.judge_node.hit_times

            anomaly_buildup = (
                accumulation
                * (am / 100)
                * (1 + element_buildup_bonus + trigger_buildup_bonus)
                * buildup_res
                * element_dmg_percentage
                / hit_times
            )

            return np.float64(anomaly_buildup)

        @staticmethod
        def cal_base_damage(data: MultiplierData) -> float:
            """基础伤害区 = 攻击力 * 对应属性的异常伤害倍率"""
            atk = (
                data.static.atk * (1 + data.dynamic.field_atk_percentage)
                + data.dynamic.atk
            )
            element_type = data.judge_node.element_type
            if element_type == 0:
                base_damage = 7.13 * atk
            elif element_type == 1:
                base_damage = 0.5 * atk
            elif element_type == 2 or element_type == 5:
                base_damage = 5 * atk
            elif element_type == 3:
                base_damage = 1.25 * atk
            elif element_type in [4, 6]:
                base_damage = 0.625 * atk
            else:
                assert False, INVALID_ELEMENT_ERROR
            return base_damage

        @staticmethod
        def cal_dmg_bonus(data: MultiplierData) -> float:
            """增伤区 = 1 + 属性增伤 + 全增伤"""
            element_type = data.judge_node.element_type
            if element_type == 0:
                element_dmg_bonus = (
                    data.static.phy_dmg_bonus + data.dynamic.phy_dmg_bonus
                )
            elif element_type == 1:
                element_dmg_bonus = (
                    data.static.fire_dmg_bonus + data.dynamic.fire_dmg_bonus
                )
            elif element_type == 2 or element_type == 5:
                element_dmg_bonus = (
                    data.static.ice_dmg_bonus + data.dynamic.ice_dmg_bonus
                )
            elif element_type == 3:
                element_dmg_bonus = (
                    data.static.electric_dmg_bonus + data.dynamic.electric_dmg_bonus
                )
            elif element_type in [4, 6]:
                element_dmg_bonus = (
                    data.static.ether_dmg_bonus + data.dynamic.ether_dmg_bonus
                )
            else:
                assert False, INVALID_ELEMENT_ERROR

            dmg_bonus = (
                1
                + element_dmg_bonus
                + data.dynamic.all_dmg_bonus
                + data.dynamic.anomaly_dmg_bonus
            )
            return dmg_bonus

        def cal_ap_mul(self, data: MultiplierData) -> float:
            """异常精通区 = 异常精通 / 100"""
            ap = self.cal_ap(data)
            ap_mul = ap / 100
            return ap_mul

        @staticmethod
        @lru_cache(maxsize=16)
        def cal_ap(data: MultiplierData):
            ap = (
                data.static.ap * (1 + data.dynamic.field_anomaly_proficiency)
                + data.dynamic.anomaly_proficiency
            )
            return ap

        @staticmethod
        def cal_ano_extra_mul(data: MultiplierData) -> float:
            """异常额外增伤区 = 1 + 对应属性异常额外增伤"""
            element_type = data.judge_node.element_type
            map = data.dynamic.ano_extra_bonus
            ano_dmg_mul = 1 + map.get(element_type, 0) + map["all"]
            return ano_dmg_mul

        def cal_anomaly_crit(self, data: MultiplierData) -> float:
            """已弃用，避免大范围重构数据类型，保留一个1"""
            return 1

        def cal_res_pen(self, data: MultiplierData) -> float:
            if self.element_type == 0:
                element_res_pen = data.dynamic.physical_res_pen_increase
            elif self.element_type == 1:
                element_res_pen = data.dynamic.fire_res_pen_increase
            elif self.element_type == 2 or self.element_type == 5:
                element_res_pen = data.dynamic.ice_res_pen_increase
            elif self.element_type == 3:
                element_res_pen = data.dynamic.electric_res_pen_increase
            elif self.element_type in [4, 6]:
                element_res_pen = data.dynamic.ether_res_pen_increase
            else:
                assert False, INVALID_ELEMENT_ERROR
            return element_res_pen

    class StunMul:
        """
        负责计算与储存与失衡值有关的属性，并负责与enemy互相

        失衡值累积 = 冲击力 * 失衡倍率 * (1 - 失衡抗性) * (1 + 失衡值提升 - 失衡值降低) * (1+ 受到失衡值提升 - 受到失衡值降低)
        """

        def __init__(self, data: MultiplierData):
            self.element_type: ElementType = data.judge_node.element_type
            self.imp = self.cal_imp(data)
            self.stun_ratio = self.cal_stun_ratio(data)
            self.stun_res = self.cal_stun_res(data, self.element_type)
            self.stun_bonus = self.cal_stun_bonus(data)
            self.stun_received = self.cal_stun_received(data)

        def get_stun_array(self) -> np.ndarray:
            stun_array = np.array(
                [
                    self.imp,
                    self.stun_ratio,
                    self.stun_res,
                    self.stun_bonus,
                    self.stun_received,
                ],
                dtype=np.float64,
            )
            return stun_array

        @staticmethod
        def cal_imp(data: MultiplierData) -> float:
            imp = (
                data.static.imp * (1 + data.dynamic.field_imp_percentage)
                + data.dynamic.imp
            )
            return imp

        @staticmethod
        def cal_stun_ratio(data: MultiplierData) -> float:
            stun_ratio = data.judge_node.skill.stun_ratio / data.judge_node.hit_times
            return stun_ratio

        @staticmethod
        def cal_stun_res(
            data: MultiplierData, element_type: ElementType, *, over_stun_res: float = 0
        ) -> float:
            enemy_stun_res = data.enemy_obj.stun_resistance_dict.get(element_type)
            stun_res = 1 - data.dynamic.stun_res - over_stun_res - enemy_stun_res
            return stun_res

        @staticmethod
        def cal_stun_bonus(data: MultiplierData) -> float:
            # 获取指定label失衡值增加
            if (
                data.judge_node.skill.labels is not None
                and data.judge_node.skill.labels.get("aftershock_attack") == 1
            ):
                label_stun_bonus = data.dynamic.aftershock_attack_stun_bonus
            else:
                label_stun_bonus = 0
            # 接下来计算标签类失衡值
            tbl = data.judge_node.skill.trigger_buff_level
            if tbl == 0:
                stun_bonus_tbl = data.dynamic.normal_attack_stun_bonus
            elif tbl == 1:
                stun_bonus_tbl = data.dynamic.special_skill_stun_bonus
            elif tbl == 2:
                stun_bonus_tbl = data.dynamic.ex_special_skill_stun_bonus
            elif tbl == 3:
                stun_bonus_tbl = data.dynamic.dash_attack_stun_bonus
            elif tbl == 4:
                stun_bonus_tbl = data.dynamic.counter_attack_stun_bonus
            elif tbl == 5:
                stun_bonus_tbl = data.dynamic.qte_stun_bonus
            elif tbl == 6:
                stun_bonus_tbl = data.dynamic.ultimate_stun_bonus
            elif tbl == 7:
                stun_bonus_tbl = data.dynamic.quick_aid_stun_bonus
            elif tbl == 8:
                stun_bonus_tbl = data.dynamic.defensive_aid_stun_bonus
            elif tbl == 9:
                stun_bonus_tbl = data.dynamic.assault_aid_stun_bonus
            elif tbl == 10:
                stun_bonus_tbl = 0
            else:
                raise ValueError(
                    f"{data.judge_node.skill_tag}的trigger_buff_level为{tbl}，无法解析！"
                )
            all_stun_bonus = data.dynamic.stun_bonus  # 全品类失衡增幅
            stun_bonus = 1 + stun_bonus_tbl + all_stun_bonus + label_stun_bonus
            return stun_bonus

        @staticmethod
        def cal_stun_received(
            data: MultiplierData, over_stun_received: float = 0
        ) -> float:
            stun_received = 1 + data.dynamic.received_stun_increase + over_stun_received
            return stun_received

    def cal_dmg_expect(self) -> np.float64:
        """计算伤害期望"""
        multipliers: np.ndarray = self.regular_multipliers.get_array_expect()
        dmg_expect = np.prod(multipliers)
        # if any([__tag in self.skill_tag for __tag in
        #         ["1371"]]):
        #     tag_list = [
        #         "基础乘区",
        #         "增伤区",
        #         "双暴区",
        #         "防御区",
        #         "抗性区",
        #         "易伤区",
        #         "失衡易伤区",
        #         "特殊乘区",
        #         "贯穿伤害区"
        #     ]
        #     print(self.skill_node.skill.skill_text, f"第{self.skill_node.loading_mission.hitted_count if self.skill_node.loading_mission else 1}次命中", "：",
        #           [f"{__tag} : {__value:.2f}" for __tag, __value in zip(tag_list, multipliers)])
        return dmg_expect

    def cal_dmg_crit(self) -> np.float64:
        """计算暴击伤害"""
        multipliers: np.ndarray = self.regular_multipliers.get_array_crit()
        dmg_crit = np.prod(multipliers)
        return dmg_crit

    def cal_dmg_not_crit(self) -> np.float64:
        """计算非暴击伤害"""
        multipliers: np.ndarray = self.regular_multipliers.get_array_not_crit()
        dmg_not_crit = np.prod(multipliers)
        return dmg_not_crit

    def cal_snapshot(self) -> tuple[int, np.float64, np.ndarray]:
        """计算异常值与失衡值快照，返回一个一维数组，用于计算异常伤害的虚拟角色，鬼知道为什么那么麻烦"""
        element_type: int = self.element_type
        build_up: np.float64 = self.anomaly_multipliers.anomaly_buildup
        anomaly_snapshot: np.ndarray = self.anomaly_multipliers.anomaly_snapshot
        stun_snapshot: np.ndarray = np.array(
            [self.stun_multipliers.imp, self.stun_multipliers.stun_bonus]
        )
        snapshot = np.concatenate((anomaly_snapshot, stun_snapshot))
        return element_type, build_up, snapshot

    def cal_stun(self) -> np.float64:
        """计算失衡值"""
        multipliers: np.ndarray = self.stun_multipliers.get_stun_array()
        stun = np.prod(multipliers)
        return stun

    @staticmethod
    def update_stun_tick(enemy_obj: Enemy, data: MultiplierData):
        """专门更新延长失衡时间的 buff"""
        if data.dynamic.stun_tick_increase >= 1:
            enemy_obj.increase_stun_recovery_time(data.dynamic.stun_tick_increase)

    # TODO：当前动作是否能够被打断的计算。
    #  技能自身有抗打断系数，但是考虑到凯撒之类的抗打断Buff的存在，所以需要在Schedule阶段进行一个全局的计算，
    #  在检测到Preload阶段抛出的“怪物进攻”信息后（当前Preload还没有这个功能，应该在这里留好接口），Schedule调取当前动作对应的基础抗打断值，
    #  并且从buff系统中读取抗打断加成，最后返回bool值，表示当前动作是否能够被打断。

    # TODO：Preload与Schedule阶段在打断功能上的交互与后续设计：
    #  ①将打断模块放在Schedule的原因：
    #       在同一个tick中，理论上说，打断事件在Preload阶段处理或是Schedule阶段处理是一样的，
    #       在Schedule阶段处理的好处更多，因为当前tick触发的buff也会被纳入考量。
    #       这样可以避免诸多类似于“某添加抗打断buff、但自身不抗打断的技能，在start标签附近被打断”的特殊情况发生
    #  ②后续设计：
    #       Schedule阶段在完成判定后，应该第一时间更新一个全局的、或是Preload内部能够读取到的一个指定数据结构
    #    （该数据结构粗看下来，布尔值应该就能满足要求，但是后续如果还有精确到tick的要求，那可能会变成字典。）
    #      而在下一个Tick，Preload会根据这个数据结构中的内容来判断“刚刚那个tick的动作是否被打断了”，
    #      这将影响到Preload抛出的是正常主动动作，还是“被打断”的空动作。


if __name__ == "__main__":
    pass
