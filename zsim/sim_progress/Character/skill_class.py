import ast
from functools import lru_cache

import polars as pl

from zsim.define import (
    CHARACTER_DATA_PATH,
    DEFAULT_SKILL_PATH,
    SKILL_DATA_PATH,
    ElementType,
)
from zsim.sim_progress import Report

try:
    # 读取角色数据
    char_lf = pl.scan_csv(CHARACTER_DATA_PATH)
except Exception as e:
    raise IOError(f"无法读取文件 {CHARACTER_DATA_PATH}: {e}")


@lru_cache(maxsize=64)
def lookup_name_or_cid(name: str = "", cid: int | str | None = None) -> tuple[str, int]:
    """
    初始化角色名称和CID（角色ID）。

    这个方法用于验证和确定角色的名称和CID。它可以根据提供的名称或CID来查找
    对应的角色信息，并确保提供的名称和CID匹配。如果只提供了名称或CID，它将
    尝试从 ./data/character.csv 中查找对应的CID或名称。

    参数:
    - name:str 角色的名称。
    - CID:int 角色的ID。

    示例：
    self.NAME, self.CID = lookup_name_or_cid(name, cid)

    返回:
    - 一个包含角色名称和CID的元组。

    异常:
    - ValueError: 提供的名称和CID不匹配，或者角色不存在。
    - IOError: 角色数据库常量 CHARACTER_DATA_PATH 有误
    - SystemError: 无法处理提供的参数。
    """
    global char_lf
    # 查找角色信息
    if name != "":
        result = char_lf.filter(pl.col("name") == name).collect().to_dicts()
    elif cid is not None:
        # 确保cid是整数
        cid_int = int(cid) if cid is not None else None
        result = char_lf.filter(pl.col("CID") == cid_int).collect().to_dicts()
    else:
        raise ValueError("角色名称与ID必须至少提供一个")

    if not result:
        raise ValueError("角色不存在")

    character_info = result[0]

    # 检查传入的name与CID是否匹配
    if name is not None and cid is not None:
        if int(character_info["CID"]) != int(cid):
            raise ValueError("传入的name与CID不匹配")

    return character_info["name"], int(character_info["CID"])


class Skill:
    def __init__(
        self,
        name: str = "",
        CID: int | str | None = None,
        normal_level=12,
        special_level=12,
        dodge_level=12,
        chain_level=12,
        assist_level=12,
        core_level=6,
        char_obj=None,
    ):
        """
        根据提供的角色、各技能等级，创建一个角色的技能对象。

        成功创建的对象会包含角色的名称、ID、核心技等级、包含全部技能的字典
        skills_dict：
            -keys: 该角色的全部技能标签（skill_tag）
            -values: 包含全部属性的 InitSkill 对象，可使用getattr()方法调用

        方法 __create_action_list():
            -检查 self.skill_dict 中是否包含闪避、正向切人、反向切人、被打断、发呆
                -有，则使用自身的技能
                -没有，则使用自带 module，初始化这些动作
            -返回仅包含动作名称的列表

        方法 get_skill_info()：
            -在仅输入技能标签（skill_tag）时，返回该技能的 InitSkill 对象
            -在同时输入技能标签（skill_tag）和所需属性时（attr_info)时，返回该技能对象的指定属性

        以下两个标识符必须提供至少一个：\n
        name:str 角色名称\n
        CID:int 角色的ID

        调用示例：
        test_object = Skill(name='艾莲')
        action_list = test_object.action_list  # 获取动作列表
        skills_dict = test_object.skills_dict  # 获取技能字典
        skill_0: Skill.InitSkill = test_object.skills_dict[action_list[0]]  # 获取第一个动作对应的技能对象
        skill_0.damage_ratio  # 获取第一个动作的伤害倍率—方式1
        test_object.get_skill_info(skill_tag=action_list[0], attr_info='damage_ratio')  # 获取第一个动作的伤害倍率-方式2
        """

        # 初始化时确保CID被转换为整数或None
        cid_int = int(CID) if CID is not None else None
        # 初始化角色名称和CID
        self.name, self.CID = lookup_name_or_cid(name, cid_int)
        # 核心技等级需要可读
        self.core_level = core_level
        self.skill_level_dict = {
            "normal": normal_level,
            "special": special_level,
            "dodge": dodge_level,
            "chain": chain_level,
            "assist": assist_level,
            "core": core_level
        }       # 技能等级字典
        # 最晚在这里创建DataFrame，优化不一点点，这玩意可大了
        schema_dict = {
            "CID": int,
            "name": str,
            "CN_TriggerLevel": str,
            "skill_tag": str,
            "CN_skill_tag": str,
            "skill_text": str,
            "INSTRUCTION": str,
            "damage_ratio": float,
            "damage_ratio_growth": float,
            "D_LEVEL12": float,
            "D_LEVEL14": float,
            "D_LEVEL16": float,
            "stun_ratio": float,
            "stun_ratio_growth": float,
            "S_LEVEL12": float,
            "S_LEVEL14": float,
            "S_LEVEL16": float,
            "sp_threshold": int,
            "sp_consume": int,
            "sp_recovery": float,
            "adrenaline_recovery": float,
            "adrenaline_threshold": float,
            "adrenaline_consume": float,
            "fever_recovery": float,
            "self_fever_re": float,
            "distance_attenuation": int,
            "initial_level": int,
            "anomaly_accumulation": float,
            "skill_type": int,
            "trigger_buff_level": int,
            "element_type": int,
            "element_damage_percent": float,
            "diff_multiplier": float,
            "ticks": int,
            "hit_times": int,
            "on_field": bool,
            "anomaly_attack": bool,
            "interruption_resistance": int,
            "swap_cancel_ticks": int,
            "labels": str,
            "follow_up": str,
            "follow_by": str,
            "aid_direction": int,
            "aid_lag_ticks": int,
            "tick_list": str,
            "force_add_condition_APL": str,
            "heavy_attack": bool,
            "max_repeat_times": int,
            "do_immediately": bool,
            "anomaly_update_list": str,
        }
        all_skills_lf = pl.scan_csv(SKILL_DATA_PATH, schema_overrides=schema_dict)

        # 根据CID提取角色的技能数据
        try:
            self.skill_df = all_skills_lf.filter(pl.col("CID") == self.CID).collect()
            # 如果没有找到对应CID，则报错
            if self.skill_df.is_empty():
                raise ValueError(f"找不到CID为 {self.CID} 的角色信息")
            # 提取dataframe中，每个索引为skill_tag的值，保存为keys
            else:
                __keys = self.skill_df["skill_tag"].unique()
        except KeyError:
            print(f"{SKILL_DATA_PATH} 中缺少 'skill_tag' 列")  # 虽然不可能
            return
        except ValueError as e:
            print(e)
            return

        # 创建技能字典与技能列表 self.skills_dict 与 self.action_list
        self.skills_dict = {}  # {技能名str:技能参数object:InitSkill}
        self.char_obj = char_obj
        for key in __keys:
            skill = self.InitSkill(
                skill_dataframe=self.skill_df,
                key=key,
                normal_level=normal_level,
                special_level=special_level,
                dodge_level=dodge_level,
                chain_level=chain_level,
                assist_level=assist_level,
                core_level=core_level,
                CID=self.CID,
                char_name=self.name,
                char_obj=self.char_obj,
            )
            self.skills_dict[key] = skill
        self.action_list = self.__create_action_list()

    def get_skill_info(self, skill_tag: str, attr_info: str | None = None):
        """
        -在仅输入技能标签（skill_tag）时，返回该技能的 InitSkill 对象\n
        -在同时输入技能标签（skill_tag）和所需属性时（attr_info)时，返回该技能对象的指定属性
        """
        skill_info: Skill.InitSkill = self.skills_dict[skill_tag]
        if attr_info is None:
            return skill_info
        else:
            value = getattr(skill_info, attr_info)
            if value:
                return value
            else:
                return None

    def __create_action_list(self):
        """
        创建动作列表并检查初始化状态

        此函数旨在为角色或实体创建一个动作列表，并检查这些动作是否已经初始化。
        它通过检查技能字典（skills_dict）中的键来确定哪些动作已经存在，如果不存在（即未初始化），
        则会创建这些动作的默认实例。
        """
        # 定义需要检查是否初始化的动作列表
        default_actions_dataframe = pl.read_csv(DEFAULT_SKILL_PATH)
        by_default_actions = default_actions_dataframe["skill_tag"].unique()

        # 初始化每个动作的状态为 True
        init_actions = {action: True for action in by_default_actions}

        # 遍历 skills_dict 的键
        for key in self.skills_dict.keys():
            # 检查键中是否包含某个动作
            for action in by_default_actions:
                if action in key:
                    # 如果包含，则将对应动作的状态设为 False
                    init_actions[action] = False

        # 遍历每个动作及其初始化状态
        for action, init in init_actions.items():
            # 如果某个动作未被初始化，则创建对应的 Skill 对象并添加到 skills_dict
            if init:
                self.skills_dict[f"{self.CID}_{action}"] = Skill.InitSkill(
                    default_actions_dataframe,
                    key=action,
                    char_name=self.name,
                    CID=self.CID,
                    char_obj=self.char_obj,
                )
        return list(self.skills_dict.keys())

    class InitSkill:
        def __init__(
            self,
            skill_dataframe: pl.DataFrame,
            key,
            char_name: str,
            normal_level=12,
            special_level=12,
            dodge_level=12,
            chain_level=12,
            assist_level=12,
            core_level=6,
            CID=0,
            char_obj=None,
        ):
            """
            初始化角色的单个技能。

            会在执行class Skill的时候自动调用，不用手动创建此类的对象
            继承自此类的对象会包含输入的技能（key）的全部属性
            """
            self.char_obj = char_obj

            # 提取数据库内，该技能的数据
            _raw_skill_data = skill_dataframe.filter(pl.col("skill_tag") == key).to_dicts()
            if not _raw_skill_data:
                raise ValueError("未找到技能")
            else:
                _raw_skill_data = _raw_skill_data[0]
            # 如果不是 攻击力/生命值/防御力/精通 倍率，报错，未来可接复杂逻辑
            self.diff_multiplier = int(_raw_skill_data["diff_multiplier"])
            if _raw_skill_data["diff_multiplier"] not in [0, 1, 2, 3, 4]:
                raise ValueError("目前只支持 攻击力/生命值/防御力/精通/贯穿力 倍率")
            self.char_name: str = char_name
            # 储存技能Tag
            self.cid = CID
            self.skill_tag = f"{CID}_{key}" if str(CID) not in key else key
            self.CN_skill_tag: str = _raw_skill_data["CN_skill_tag"]
            self.skill_text: str = _raw_skill_data["skill_text"]
            # 确定使用的技能等级
            self.skill_type: int = int(_raw_skill_data["skill_type"])
            self.skill_level: int = self.__init_skill_level(
                self.skill_type,
                normal_level,
                special_level,
                dodge_level,
                chain_level,
                assist_level,
                core_level,
            )
            # 确定伤害倍率
            damage_ratio = float(_raw_skill_data["damage_ratio"])
            damage_ratio_growth = float(_raw_skill_data["damage_ratio_growth"])
            self.damage_ratio: float = damage_ratio + damage_ratio_growth * (self.skill_level - 1)
            # 确定失衡倍率
            stun_ratio = float(_raw_skill_data["stun_ratio"])
            stun_ratio_growth = float(_raw_skill_data["stun_ratio_growth"])
            self.stun_ratio: float = stun_ratio + stun_ratio_growth * (self.skill_level - 1)
            # 能量相关属性
            self.sp_threshold: float = float(_raw_skill_data["sp_threshold"])
            self.sp_consume: float = float(_raw_skill_data["sp_consume"])
            self.sp_recovery: float = float(_raw_skill_data["sp_recovery"])
            # 闪能相关——仪玄专属
            self.adrenaline_threshold: float = float(_raw_skill_data["adrenaline_threshold"])
            self.adrenaline_consume: float = float(_raw_skill_data["adrenaline_consume"])
            self.adrenaline_recovery: float = float(_raw_skill_data["adrenaline_recovery"])
            # 喧响值
            self.self_fever_re: float = float(_raw_skill_data["self_fever_re"])
            # 距离衰减，不知道有啥用
            self.distance_attenuation: int = int(_raw_skill_data["distance_attenuation"])
            # 属性异常蓄积值，直接转化为浮点
            self.anomaly_accumulation: float = float(_raw_skill_data["anomaly_accumulation"]) / 100
            # TriggerBuffLevel
            self.trigger_buff_level: int = int(_raw_skill_data["trigger_buff_level"])
            # 元素相关
            self.element_type: ElementType = _raw_skill_data["element_type"]
            self.element_damage_percent: float = float(_raw_skill_data["element_damage_percent"])
            # 动画相关
            ticks_str = _raw_skill_data["ticks"]
            if ticks_str is None or ticks_str == "test":
                print(f"检测到技能 {self.skill_tag}的ticks参数不正确，已设置为默认值60")
                self.ticks = 60
            else:
                self.ticks: int = int(_raw_skill_data["ticks"])
            temp_hit_times = int(_raw_skill_data["hit_times"])
            self.hit_times: int = temp_hit_times if temp_hit_times > 0 else 1
            self.on_field: bool = bool(_raw_skill_data["on_field"])
            self.anomaly_attack: bool = bool(_raw_skill_data["anomaly_attack"])
            # 特殊标签
            labels_str = _raw_skill_data["labels"]
            if labels_str is None or not str(labels_str).strip():  # 判断空值或空字符串
                labels = None
            else:
                # 去除首尾空格后尝试解析字典
                labels = ast.literal_eval(str(labels_str).strip())

            self.labels: dict | None = labels  # 技能特殊标签
            # if self.labels:
            #     pass

            # TODO：抗打断标签；无敌标签

            # 技能链相关
            __swap_cancel_ticks_value = _raw_skill_data["swap_cancel_ticks"]
            if __swap_cancel_ticks_value is None:
                self.swap_cancel_ticks = 0
            else:
                self.swap_cancel_ticks: int = int(
                    _raw_skill_data["swap_cancel_ticks"]
                )  # 可执行合轴操作的最短时间

            follow_up = _raw_skill_data["follow_up"]
            if follow_up is None:
                self.follow_up: list = []
            else:
                self.follow_up: list = _raw_skill_data["follow_up"].split(
                    "|"
                )  # 技能发动后强制衔接的技能标签

            follow_by = _raw_skill_data["follow_by"]
            if follow_by is None:
                self.follow_by: list = []
            else:
                self.follow_by: list = _raw_skill_data["follow_by"].split(
                    "|"
                )  # 发动技能必须的前置技能标签
            self.aid_direction: int = _raw_skill_data["aid_direction"]  # 触发快速支援的方向
            aid_lag_ticks_value = _raw_skill_data["aid_lag_ticks"]
            if aid_lag_ticks_value == "inf":
                self.aid_lag_ticks = self.ticks - 1
            elif aid_lag_ticks_value is None:
                self.aid_lag_ticks = 0
            else:
                self.aid_lag_ticks: int = int(
                    _raw_skill_data["aid_lag_ticks"]
                )  # 技能激活快速支援的滞后时间
            tick_value = _raw_skill_data["tick_list"]
            if tick_value is None:
                self.tick_list = None
            elif isinstance(tick_value, str):
                # 处理空字符串或纯空格
                if not tick_value.strip():
                    self.tick_list = None
                else:
                    try:
                        # 转换并去除首尾空格
                        self.tick_list = ast.literal_eval(str(tick_value).strip())
                        # self.tick_list = [int(v.strip()) for v in split_values]
                    except ValueError as e:
                        raise ValueError(f"{self.skill_tag} 的 tick_list 包含无效整数: {e}")
            else:
                # 处理非字符串类型（如意外数值）
                self.tick_list = None
            if self.tick_list:
                if max(self.tick_list) >= self.ticks:
                    raise ValueError(
                        f"{self.skill_tag}的精确帧数分布的最大值超过技能总帧数！请检查数据正确性，{self.tick_list, self.ticks}"
                    )
                if len(self.tick_list) != self.hit_times:
                    raise ValueError(
                        f"{self.skill_tag}的精确帧数分布所包含的命中数与技能的命中总数不符！请检查数据正确性，{self.tick_list, self.hit_times}"
                    )

            self.ratio_distribution: list | None = None  # 技能的精确倍率分布
            #  _raw_skill_data['ratio_distribution'].split(':') if _raw_skill_data['ratio_distribution'] else None
            self.force_add_condition_APL = []
            condition_value = _raw_skill_data["force_add_condition_APL"]
            if condition_value is None:
                self.force_add_condition_APL = []
            else:
                from zsim.sim_progress.Preload.apl_unit.APLUnit import (
                    SimpleUnitForForceAdd,
                )

                condition_list = condition_value.strip().split(";")
                for _cond_str in condition_list:
                    _cond_list = _cond_str.strip().split("|")
                    simple_apl_unit_for_force_add = SimpleUnitForForceAdd(condition_list=_cond_list)
                    self.force_add_condition_APL.append(simple_apl_unit_for_force_add)
            if (
                len(self.follow_up) != len(self.force_add_condition_APL)
                and self.force_add_condition_APL
            ):
                raise ValueError(
                    f"ID为{self.skill_tag}的技能的follow_up与force_add_condition_APL长度不一致！请检查数据正确性"
                )
            self.skill_attr_dict = {
                attr: getattr(self, attr)
                for attr in dir(self)
                if not attr.startswith("__") and not callable(getattr(self, attr))
            }
            self.heavy_attack: bool = bool(_raw_skill_data["heavy_attack"])
            __max_repeat_times_value = _raw_skill_data["max_repeat_times"]
            if __max_repeat_times_value is None:
                self.max_repeat_times = 1
            else:
                self.max_repeat_times: int = int(
                    _raw_skill_data["max_repeat_times"]
                )  # 最大重复释放次数。
            """
            技能是否立刻执行，大部分技能都是False，目前只有QTE和大招具有这种属性。
            该属性会在APL部分的SwapCancelEngine中被用到，用于检测角色已有的动作是否会被新动作打断。
            """
            self.do_immediately: bool = bool(_raw_skill_data["do_immediately"])

            self.anomaly_update_rule: (
                list[int] | int | None
            ) = []  # 更新异常的模式，如果不填，那就是最后一跳，如果有填写，那就按照填写的跳数来更新。
            anomaly_update_list_str = _raw_skill_data["anomaly_update_list"]
            self._process_anomaly_update_rule(anomaly_update_list_str)

            Report.report_to_log(f"[Skill INFO]:{self.skill_tag}:{str(self.skill_attr_dict)}")

        def _process_anomaly_update_rule(self, anomaly_update_list_str):
            """
            初始化 异常更新规则 ：
                1、不填，则就返回[]，那就按照最后一跳处理；
                2、-1，则返回-1，那就按照每一跳处理；
                3、a&b&c&d， 则返回[a, b, c, d]，那就按照这些跳数处理
            """
            if anomaly_update_list_str is None:
                self.anomaly_update_rule = []  # None代表更新节点是最后一跳
            else:
                try:
                    anomaly_update_mode = int(anomaly_update_list_str)
                    if anomaly_update_mode == -1:
                        self.anomaly_update_rule = anomaly_update_mode
                    else:
                        if anomaly_update_mode > self.hit_times:
                            raise ValueError(
                                f"{self.skill_tag}的更新节点大于技能总帧数！请检查数据正确性"
                            )
                        self.anomaly_update_rule = [anomaly_update_mode]
                except ValueError:
                    self.anomaly_update_rule = anomaly_update_list_str.split("&")
            if (
                isinstance(self.anomaly_update_rule, list)
                and len(self.anomaly_update_rule) > self.hit_times
            ):
                raise ValueError(f"{self.skill_tag}的更新节点总数大于技能总帧数！请检查数据正确性")

        @staticmethod
        def __init_skill_level(
            skill_type: int,
            normal_level: int,
            special_level: int,
            dodge_level: int,
            chain_level: int,
            assist_level: int,
            core_level: int,
        ) -> int:
            """
            根据 skill_type 选择对应的技能等级

            参数:
            - skill_type (int): 技能类型标签
            - normal_level (int): 普攻等级
            - special_level (int): 特殊技等级
            - dodge_level (int): 闪避等级
            - chain_level (int): 连携技等级
            - assist_level (int): 支援技等级
            - core_level (int): 核心被动等级
            """
            skill_levels = {
                0: normal_level,
                1: special_level,
                2: dodge_level,
                3: chain_level,
                4: core_level,
                5: assist_level,
                6: assist_level,  # 暂时过度一下，防止报错
            }
            # FIXME：修复数据库中支援技skill_type的问题！

            if skill_type in skill_levels:
                return skill_levels[skill_type]
            else:
                raise ValueError(f"非法的技能种类（skill_type）：{skill_type}")

        def __str__(self) -> str:
            return self.skill_tag

    def __str__(self) -> str:
        return self.name + "Skills"


if __name__ == "__main__":
    test_object = Skill(name="艾莲")
    test_object2 = Skill(CID=1221)
    action_list = test_object.action_list  # 获取动作列表
    skills_dict = test_object.skills_dict  # 获取技能字典
    skill_0: Skill.InitSkill = test_object.skills_dict[
        action_list[0]
    ]  # 获取第一个动作对应的技能对象
    print(skill_0.damage_ratio)  # 获取第一个动作的伤害倍率
    print(
        test_object.get_skill_info(skill_tag=action_list[0], attr_info="damage_ratio")
    )  # 获取第一个动作的伤害倍率
