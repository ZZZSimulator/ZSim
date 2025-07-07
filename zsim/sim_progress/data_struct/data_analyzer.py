from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING, Any, Sequence

from zsim.define import BACK_ATTACK_RATE
from zsim.sim_progress.Report import report_to_log

if TYPE_CHECKING:
    from zsim.sim_progress.anomaly_bar import AnomalyBar
    from zsim.sim_progress.Buff import Buff
    from zsim.sim_progress.Preload.SkillsQueue import SkillNode


@lru_cache(maxsize=128)
def cal_buff_total_bonus(
    enabled_buff: Sequence["Buff"],
    judge_obj: "SkillNode" | "AnomalyBar" | None = None,
) -> dict[str, float]:
    """过滤并计算buff总加成。

    该方法首先读取buff效果的键值对，然后遍历提供列表的所有buff（一般为特定角色+怪物，具体参考调用方式）
    对于每个buff，检查其是否为Buff类型，然后根据buff的计数（count）来计算总加成。

    参数:
    - enabled_buff: 包含需要处理的buff的列表。
    - judge_obj: 可选的技能节点或异常状态，用于过滤buff。

    返回:
    - dict[str, float]: 包含所有buff总加成的键值对。
    """

    # 初始化动态语句字典，用于累加buff效果的值
    dynamic_statement: dict[str, float] = {}
    # effect_buff_list: list[str] = []
    # 遍历角色身上的所有buff
    from zsim.sim_progress.anomaly_bar import AnomalyBar
    from zsim.sim_progress.Buff import Buff
    from zsim.sim_progress.Preload.SkillsQueue import SkillNode

    buff_obj: Buff
    for buff_obj in enabled_buff:
        # 确保buff是Buff类的实例
        if not isinstance(buff_obj, Buff):
            raise TypeError(f"{buff_obj} 不是Buff类型，无法计算！")
        else:
            # 检查buff是否激活
            if not buff_obj.dy.active:
                report_to_log(
                    f"[Warning] 动态buff列表中混入了未激活buff: {str(buff_obj)}，已跳过"
                )
                continue
            # 检查buff的标签是否与技能节点匹配
            if judge_obj is not None:
                """
                下面两个continue作用：筛选掉无法对当前judge_obj生效的buff。
                一般来说，buff都是默认对所有的judge_obj产生效果的，但是有一类buff不是。
                这类的buff通常带有标签，比如only_skill或者only_anomaly，或者only_label，
                这些buff只有在特定条件被满足的情况下才会对当前技能生效——__check_skill_node() 和 __check_special_anomlay()方法就是用来检查这个的。
                所以，被continue跳过的Buff一定自带label或是其他的特殊判定条件，并且和当前的检查对象——judge_obj不相符，导致它对当前检测对象无法生效。
                """
                if isinstance(judge_obj, SkillNode) and not __check_skill_node(
                    buff_obj, judge_obj
                ):
                    continue
                if isinstance(judge_obj, AnomalyBar) and not __check_special_anomly(
                    buff_obj, judge_obj
                ):
                    continue
            # 获取buff的层数
            count = buff_obj.dy.count
            count = count if count > 0 else 0
            # 遍历buff的每个效果和对应的值，并将其累加
            # if buff_obj.ft.label and judge_obj is not None:
            #     if 'only_label' in buff_obj.ft.label.keys():
            #         print(f'{buff_obj.ft.index}通过了判定，享受该buff加成的对象为：{judge_obj}')

            for key, value in buff_obj.effect_dct.items():
                # 如果键值对在动态语句字典中，则累加值，否则初始化并赋值
                try:
                    dynamic_statement[key] = (
                        dynamic_statement.get(key, 0) + value * count
                    )
                except TypeError:
                    continue
        # effect_buff_list.append(buff_obj)
    # if judge_obj is not None and isinstance(judge_obj, SkillNode):
    #     if "1291_CorePassive" in judge_obj.skill_tag:
    #         print(f"检测到决算{judge_obj.skill_tag}, 其享受的buff列表为：")
    #         for _buff in effect_buff_list:
    #             print(f"{_buff.ft.index}: {_buff.effect_dct}")
    return dynamic_statement


def __check_skill_node(buff: "Buff", skill_node: "SkillNode") -> bool:
    """
    检查 buff 的标签是否与 skill node 匹配。

    该方法用于验证 buff 的标签限制条件是否满足技能节点的要求。检查标签类型：
    1. only_skill: buff仅对特定技能标签生效
    2. only_label: buff仅对带有特定标签的技能生效

    参数:
        buff (Buff): 需要检查的buff对象
        skill_node (SkillNode): 技能节点对象

    返回:
        bool: 如果buff标签与技能节点匹配则返回True，否则返回False
    """
    # 定义允许的标签类型
    ALLOWED_LABELS = [
        "only_skill",
        "only_label",
        "only_trigger_buff_level",
        "only_back_attack",
        "only_element",
        "only_skill_type",
    ]
    # 获取buff的标签列表
    buff_labels: dict[str, list[str] | str] = buff.ft.label
    # 如果buff没有标签限制，则直接返回True
    if not buff_labels:
        return True

    # 获取技能节点的标签信息
    skill_tag: str = skill_node.skill_tag
    skill_labels: dict[str, Any] = skill_node.labels

    # 遍历buff的所有标签进行检查
    for label_key, label_value in buff_labels.items():
        """注意，在Buff端，label总是以 {str, list[str]}的形式存在的，这里要针对这一特性进行处理。"""
        if not label_value:
            continue
        if not isinstance(label_value, list):
            raise TypeError(
                f"Buff {buff} 的标签 {label_key} 的值存在，对应Value为：{label_value} ，但不是列表类型，请检查初始化或者数据库。"
            )
        if any(
            [
                __check_label_key(label_key=label_key, target_label_key=_tlk)
                for _tlk in ALLOWED_LABELS
            ]
        ):
            # 检查是否为特定技能限制
            if __check_label_key(label_key=label_key, target_label_key="only_skill"):
                if skill_tag in label_value:
                    return True
            # 检查是否为特定标签限制
            elif __check_label_key(label_key=label_key, target_label_key="only_label"):
                """
                当被检查技能完全不存在label属性时，说明该技能是无标签的普通技能。
                而当前分支检查的是“技能是否具有Buff指定的标签”，所以这里无需继续遍历，直接continue。
                """
                if skill_labels is None:
                    continue
                if any(_sub_label in skill_labels.keys() for _sub_label in label_value):
                    # print(f'在技能 {skill_tag} 中，成功找到标签 {label_value}，')
                    return True
                # for _sub_label in label_value:
                #     if _sub_label in skill_labels.keys():
                #         print(f'在技能 {skill_tag} 中，成功找到标签 {label_value}，')
                #         return True
                #     else:
                #         print(skill_node.skill_tag, skill_labels, _sub_label, label_value)
            elif __check_label_key(
                label_key=label_key, target_label_key="only_trigger_buff_level"
            ):
                if skill_node.skill.trigger_buff_level in label_value:
                    # print(f"{buff.ft.index}对技能{skill_tag}成功生效！")
                    return True
            elif __check_label_key(
                label_key=label_key, target_label_key="only_back_attack"
            ):
                from zsim.sim_progress.RandomNumberGenerator import RNG

                rng: RNG = buff.sim_instance.rng_instance
                normalized_value = rng.random_float()
                if normalized_value <= BACK_ATTACK_RATE:
                    return True
            elif __check_label_key(
                label_key=label_key, target_label_key="only_element"
            ):
                from zsim.define import ELEMENT_EQUIVALENCE_MAP

                for _ele_type in label_value:
                    if (
                        skill_node.skill.element_type
                        in ELEMENT_EQUIVALENCE_MAP[_ele_type]
                    ):
                        # 只要找到一种符合要求的元素，就返回True
                        return True
            elif __check_label_key(
                label_key=label_key, target_label_key="only_skill_type"
            ):
                if skill_node.skill.skill_type in label_value:
                    return True
        else:
            raise ValueError(f"{buff.ft.index}的标签类型 {label_key} 未定义！")
    else:
        # if buff.ft.index == "Buff-角色-仪玄-2画-强化E与终结技无视以太抗" and any([__tags in skill_node.skill_tag for __tags in ["1371_E_EX", "1371_Q"]]):
        #     print(f"data_analyzer的报告：{buff.ft.index}与{skill_node.skill_tag}不匹配！")
        return False
    # FIXME: 该函数还是有些逻辑问题的，等带后续继续优化修改！


def __check_label_key(label_key: str, target_label_key: str):
    """用于筛选出对应的label"""
    pattern = r"_\d{1,2}$"  # 匹配结尾是_加1-2位数字
    import re

    if bool(re.search(pattern, label_key)):
        base_key = label_key.rsplit("_", 1)[0]
    else:
        base_key = label_key
    return base_key == target_label_key


def __check_special_anomly(buff: "Buff", anomly_node: "AnomalyBar") -> bool:
    """
    检查 buff 的标签是否与异常匹配。

    检查标签类型：
    1. only_anomly: buff仅对特定异常状态生效
        - Disorder: 紊乱
        - Abloom: 异放
        - PolarityDisorder: 极性紊乱

    参数:
        buff (Buff): 需要检查的buff对象
        anomly_node (AnomalyBar的各种子类): 异常状态对象

    返回:
        bool: 如果buff标签与异常状态节点匹配则返回True，否则返回False
    """
    # 导入异常状态相关的类
    from zsim.sim_progress.anomaly_bar.CopyAnomalyForOutput import (
        DirgeOfDestinyAnomaly as Abloom,
    )
    from zsim.sim_progress.anomaly_bar.CopyAnomalyForOutput import (
        Disorder,
        PolarityDisorder,
    )

    # 定义允许的标签类型
    ALLOW_LABELS = ["only_anomaly"]
    # 定义异常状态类型映射字典
    SELECT_ANOMALY_MAP = {
        "Disorder": Disorder,
        "Abloom": Abloom,
        "PolarityDisorder": PolarityDisorder,
    }

    # 获取buff的标签列表
    buff_labels: dict[str, list[str] | str] = buff.ft.label
    # 如果buff没有标签限制，则直接返回True
    if not buff_labels:
        return True

    # 遍历buff的所有标签进行检查
    for label_key, label_value in buff_labels.items():
        # 跳过空值标签
        if not label_value:
            continue
        # 检查是否为允许的标签类型
        if label_key in ALLOW_LABELS:
            # 输入为单个字符串
            if isinstance(label_value, str):
                if label_value in SELECT_ANOMALY_MAP.keys():
                    if isinstance(anomly_node, SELECT_ANOMALY_MAP[label_value]):
                        return True
            # 输入为列表
            if isinstance(label_value, list):
                if any(
                    isinstance(anomly_node, SELECT_ANOMALY_MAP[sig_value])
                    for sig_value in label_value
                    if sig_value in SELECT_ANOMALY_MAP.keys()
                ):
                    return True
    return False


if __name__ == "__main__":
    base_key = "only_skill"
    key_1 = "only_skill_1"
    key_2 = "only_skill_trigger_buff_level"
    key_3 = "only_skill_trigger_buff_level_1"
    list1 = [key_1, key_2, key_3]
    for _key in list1:
        print(__check_label_key(label_key=_key, target_label_key=base_key))
