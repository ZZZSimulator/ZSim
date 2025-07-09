from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from zsim.define import (
    BUFF_LOADING_CONDITION_TRANSLATION_DICT,
    EXIST_FILE_PATH,
    JUDGE_FILE_PATH,
)
from zsim.sim_progress.Character.skill_class import Skill

from .buff_class import Buff

if TYPE_CHECKING:
    from zsim.sim_progress.Load import LoadingMission
    from zsim.simulator.simulator_class import Simulator

EXIST_FILE = pd.read_csv(EXIST_FILE_PATH, index_col="BuffName")
JUDGE_FILE = pd.read_csv(JUDGE_FILE_PATH, index_col="BuffName")
JUDGE_FILE = JUDGE_FILE.replace({np.nan: None})
EXIST_FILE = EXIST_FILE.replace({np.nan: None})


class BuffInitCache:
    def __init__(self):
        self.cache = {}

    def get(self, key):
        return self.cache.get(key)

    def add(self, key, value):
        self.cache[key] = value
        max_cache = 128
        while len(self.cache) > max_cache:
            self.cache.popitem()

    def __getitem__(self, key):
        return self.cache[key]


class BuffJudgeCache(BuffInitCache):
    def __init__(self):
        super().__init__()


def process_buff(
    buff_0,
    sub_exist_buff_dict,
    mission,
    time_now,
    selected_characters,
    LOADING_BUFF_DICT,
    exist_buff_dict: dict,
    sim_instance: "Simulator",
):
    """
    该函数是公用的buff逻辑处理函数，主要是通过BuffJudge来判断Buff是否应该触发。
    注意，此处的buff_0是operator的buff_0，哪怕buff是要加给别的角色，这里也是operator的buff_0
    """
    all_match, judge_condition_dict, active_condition_dict = BuffInitialize(
        buff_0.ft.index, sub_exist_buff_dict
    )
    all_match = BuffJudge(buff_0, judge_condition_dict, mission)
    if not all_match:
        return
    # if not buff_0.ft.is_debuff:
    """
    在20241114的更新中，我删除了debuff分支。因为buff的add_buff_to被拓展成了4字段，所以就没有必要判断是否是debuff了
    如果一个buff是debuff，那么它的add_buff_to字段的最后一位肯定是1，比如0001，
    这样，它就一定会在buff_go_to函数中导致'enemy'字段进入selected_characters列表，这样一来，enemy会被当成正常角色来执行正常的buff添加和update。
    """
    for char in selected_characters:
        # if buff_0.ft.simple_judge_logic:
        if buff_0.ft.simple_effect_logic:
            for sub_mission_start_tick, sub_mission in mission.mission_dict.items():
                if time_now - 1 < sub_mission_start_tick <= time_now:
                    """
                    筛选出正在发生的子任务，如果子任务正在发生就直接执行update，把子任务的str传进buff.update()函数
                    并且触发对应的分支（start、hit、end），完成符合buff属性的时间、层数更新。
                    """
                    buff_new = Buff(
                        active_condition_dict,
                        judge_condition_dict,
                        sim_instance=sim_instance,
                    )
                    buff_new.update(
                        char,
                        time_now,
                        mission.mission_node.skill.ticks,
                        sub_exist_buff_dict,
                        sub_mission,
                    )
                    buff_new.ft.operator = buff_0.ft.operator
                    buff_new.ft.passively_updating = buff_0.ft.passively_updating
                    buff_new.ft.beneficiary = buff_0.ft.beneficiary
                    if buff_new.dy.is_changed:
                        LOADING_BUFF_DICT[char].append(buff_new)
                        """
                        这里要注意：process_buff函数中传入的buff_0，只会来自于角色，
                        所以，如果有上个Enemy的debuff，那么角色自身作为触发源头，正常更新以外，
                        需要向Enemy的buff_0同步广播。否则，record就无法记录enemy身上Buff的正常层数。
                        """
                        if char == "enemy":
                            enemy_buff_0 = exist_buff_dict["enemy"][buff_0.ft.index]
                            buff_new.update_to_buff_0(enemy_buff_0)
        else:
            """
            这个分支主要是为了处理复杂的effect类的buff的
            此类buff的更新往往不依赖start、hit、end三大子标签进行，
            所以单独进行处理
            """
            buff_new = Buff(
                active_condition_dict, judge_condition_dict, sim_instance=sim_instance
            )
            buff_new.logic.xeffect()
            if buff_new.dy.is_changed:
                buff_new.ft.operator = buff_0.ft.operator
                buff_new.ft.passively_updating = buff_0.ft.passively_updating
                buff_new.ft.beneficiary = buff_0.ft.beneficiary
                LOADING_BUFF_DICT[char].append(buff_new)
                if char == "enemy":
                    enemy_buff_0 = exist_buff_dict["enemy"][buff_0.ft.index]
                    buff_new.update_to_buff_0(enemy_buff_0)


def BuffLoadLoop(
    time_now: int,
    load_mission_dict: dict,
    existbuff_dict: dict,
    character_name_box: list,
    LOADING_BUFF_DICT: dict,
    all_name_order_box: dict,
    sim_instance: "Simulator",
):
    """
    这是buff修改三部曲的第二步,也是最核心的一个步骤，
    该函数会向外抛出LOADING_BUFF_DICT——本tick触发了多少BUFF/DEBUFF，并且移交给BuffAdd函数，执行buff的添加。
    本函数的核心调用函数是ProcessBuff函数。
    """
    # 初始化LOADING_BUFF_DICT
    from zsim.sim_progress.Load import LoadingMission

    all_name_box = character_name_box + ["enemy"]
    for character in all_name_box:
        LOADING_BUFF_DICT[character] = []
    # 遍历load_mission_dict中的任务
    for mission in load_mission_dict.values():
        if not isinstance(mission, LoadingMission):
            raise TypeError(f"当前{mission}不是LoadingMission类！")
        actor_name = mission.mission_character
        if actor_name not in existbuff_dict:
            raise ValueError("当前角色的Buff源并未创建！")
        # 提取当前角色的 Buff 列表
        # sub_exist_debuff_dict = existbuff_dict['enemy']

        for char_name in character_name_box:
            sub_exist_buff_dict = existbuff_dict[char_name]
            if char_name == actor_name:
                process_on_field_buff(
                    sub_exist_buff_dict,
                    mission,
                    time_now,
                    LOADING_BUFF_DICT,
                    all_name_order_box,
                    existbuff_dict,
                    sim_instance=sim_instance,
                )
            else:
                process_backend_buff(
                    sub_exist_buff_dict,
                    all_name_order_box,
                    mission,
                    time_now,
                    LOADING_BUFF_DICT,
                    existbuff_dict,
                    sim_instance=sim_instance,
                )
    return LOADING_BUFF_DICT


def process_on_field_buff(
    sub_exist_buff_dict: dict,
    mission: "LoadingMission",
    time_now: int,
    LOADING_BUFF_DICT: dict,
    all_name_order_box: dict,
    exist_buff_dict: dict,
    sim_instance: "Simulator",
):
    """
    处理前台Buff的逻辑模块
        注意，这部分的分支，指的是以当前的前台角色为第一视角来给自己或是其他人添加Buff。
        由于这个循环的前置参数——character_name是从mission里面拿来的，所以“前台角色”不可能是enemy
        这意味enemy的所有buff必须是别人添加给它的，目前enemy没有主动更新buff的逻辑。
    """
    for buff_key, buff_0 in sub_exist_buff_dict.items():
        if not isinstance(buff_0, Buff):
            raise TypeError(f"当前{buff_key}不是Buff类！")
        if buff_0.ft.schedule_judge:
            #   跳过schedule阶段处理的buff
            continue
        if buff_0.ft.passively_updating:
            # 目前正是前台角色触发前台buff，而passively_updating为True时，
            # 意味着“当前buff的触发我说了不算，别人说了算”，那么本函数自然无法处理，要直接跳过。
            continue

        # 提前计算添加Buff的角色列表
        main_char = buff_0.ft.operator
        all_name_box = all_name_order_box[main_char]
        selected_characters = buff_go_to(buff_0, all_name_box)
        process_buff(
            buff_0,
            sub_exist_buff_dict,
            mission,
            time_now,
            selected_characters,
            LOADING_BUFF_DICT,
            exist_buff_dict,
            sim_instance=sim_instance,
        )


def process_backend_buff(
    sub_exist_buff_dict: dict,
    all_name_order_box: dict,
    mission: "LoadingMission",
    time_now: int,
    LOADING_BUFF_DICT: dict,
    exist_buff_dict: dict,
    sim_instance: "Simulator",
):
    """
    处理后台Buff的逻辑，
    尽管当前的动作是别的角色（actor ≠ char_name），但是，两位后台角色身上，依旧存在着可能发生更新的Buff
    这些Buff都拥有backend_active标签。但并非所有拥有这一标签的buff都应该执行更新。
    比如，后台角色A会给所有人叠层，当前台动作满足该Buff的触发条件时，
    应只执行该buff所有者（operator）的buff更新，而不执行受益者（beneficiary）的更新，
    这样就可以避免buff的重复更新。

    以 静听佳音4件套 为例：套装佩戴者位于后台时，如果前台角色使用了快速支援，
    那么，在process_on_field_buff函数中，前台角色的嘉音层数不会被更新；
    而在此函数中，该buff属于耀佳音的那个buff_0会触发更新，从而实现全队层数+1
    """
    for other_buff_key, other_buff_0 in sub_exist_buff_dict.items():
        if not isinstance(other_buff_0, Buff):
            raise TypeError(f"当前{other_buff_key}不是Buff类！")
        if other_buff_0.ft.schedule_judge:
            continue
        if not other_buff_0.ft.backend_acitve:
            continue
        if other_buff_0.ft.passively_updating:
            continue
        main_char = other_buff_0.ft.operator
        name_order_box = all_name_order_box[main_char]
        selected_characters_back = buff_go_to(other_buff_0, name_order_box)
        process_buff(
            other_buff_0,
            sub_exist_buff_dict,
            mission,
            time_now,
            selected_characters_back,
            LOADING_BUFF_DICT,
            exist_buff_dict,
            sim_instance=sim_instance,
        )


def buff_go_to(buff_0, all_name_box):
    """
    运行函数前，总有：
    all_name_box  = character_name_box + ['enemy']
    该函数是用来处理buff该加给什么角色的
    比如这个buff的add_buff_to字段的内容是1100（加给自己和下一位），那么新的这个selected_characters就会输出[艾莲，莱卡恩]
    如果字段内容是1010（加给自己和上一位），那么新的selected_characters就会输出[艾莲，苍角]
    """
    adding_code = str(int(buff_0.ft.add_buff_to)).zfill(4)
    selected_characters = [
        all_name_box[i] for i in range(len(all_name_box)) if adding_code[i] == "1"
    ]
    return selected_characters


def BuffInitialize(
    buff_name: str, existbuff_dict: dict, *, cache=BuffInitCache()
) -> tuple[bool, dict, dict]:
    cache_key = (buff_name, tuple(existbuff_dict.items()))
    if cache_key in cache.cache:
        return cache.get(cache_key)
    # 对单个buff进行初始化，抛出一个触发状态参数，两个参数序列。
    all_match = False
    buff_now = existbuff_dict[buff_name]
    if not isinstance(buff_now, Buff):
        raise ValueError(f"当前正在检索的Buff：{buff_name}并不是Buff类！")
    if buff_name not in JUDGE_FILE.index:
        raise ValueError(f"Buff{buff_name}不在JUDGE_FILE中！")
    judge_condition_dict = dict(JUDGE_FILE.loc[buff_name])
    active_condition_dict = dict(EXIST_FILE.loc[buff_name])
    active_condition_dict["BuffName"] = buff_name
    # 根据buff名称，直接把判断信息从JUDGE_FILE中提出来并且转化成dict。

    results = (all_match, judge_condition_dict, active_condition_dict)
    cache.add(cache_key, results)
    return results


def BuffJudge(
    buff_now: Buff,
    judge_condition_dict: dict,
    mission: "LoadingMission",
    *,
    cache=BuffJudgeCache(),
) -> bool:
    """
    如果judge_condition_dict的全部内容是None，同时buff还是简单判断逻辑
    说明是环境或是战斗系统自带的debuff，则直接返回False，跳过判断。
    """
    # 以下为缓存逻辑
    simple_logic: bool = buff_now.ft.simple_judge_logic
    all_simple = [
        buff_now.ft.simple_judge_logic,
        buff_now.ft.simple_start_logic,
        buff_now.ft.simple_hit_logic,
        buff_now.ft.simple_end_logic,
        buff_now.ft.simple_effect_logic,
        buff_now.ft.simple_exit_logic,
    ]
    if all(all_simple):
        cache_key = hash(
            (id(buff_now), tuple(judge_condition_dict.items()), id(mission))
        )
        if cache_key in cache.cache:
            return cache[cache_key]
    result: bool

    def save_cache_and_return(result: bool, *, cache=cache):
        """由于本函数有多个return中断，所以写了个这玩意，把直接return换成return这个函数就行"""
        if all(all_simple):
            cache.add(cache_key, result)
        return result

    # ——————缓存逻辑结束————————

    if buff_now.ft.alltime:
        result = True
        return save_cache_and_return(result)
    if (
        not any(
            value if value is None else True for value in judge_condition_dict.values()
        )
        and buff_now.ft.simple_judge_logic
    ):
        # EXPLAIN：全部数据都是None并且是简单判断逻辑
        #   这通常意味着Buff的判断不在Load阶段，而是通过某种方式在其他阶段暴力添加。
        #   但是部分alltime的buff也会进入这一分支，所以需要在判断alltime之后再进行全空判断。
        result = False
        return save_cache_and_return(result)
    """
    正常buff的判断逻辑
    """
    skill_now = mission.mission_node.skill
    if not isinstance(skill_now, Skill.InitSkill):
        raise TypeError(f"{skill_now}并非Skill类！")
    if simple_logic:
        all_match = simple_string_judge(judge_condition_dict, skill_now)
    else:
        # print(buff_now.ft.index)
        all_match = buff_now.logic.xjudge(
            loading_mission=mission, skill_node=mission.mission_node
        )
    result = all_match
    return save_cache_and_return(result)


def simple_string_judge(judge_condition_dict: dict, skill_now) -> bool:
    all_match = True
    """
        先假定all_match是True，一会儿循环过程中一旦有不符合的项，就改成False。
        只有全部通过才能继续维持All_match的值。
        """
    for condition, judge_condition in BUFF_LOADING_CONDITION_TRANSLATION_DICT.items():
        """
        由于SkillNode中的属性名和judge_condition_dict中的键值名不同，
        所以需要BUFF_LOADING_CONDITION_TRANSLATION_DICT进行翻译。
        """
        csv_judge_condition = judge_condition_dict[condition]

        if csv_judge_condition is not None:
            """
            如果键值下面是None则直接跳过。
            """
            final_condition = process_string(csv_judge_condition)
            if getattr(skill_now, judge_condition) not in final_condition:
                all_match = False
    return all_match


def process_string(source: str) -> list[int | float | str]:
    """
    在2024.11.13的更新中，从csv中读取的数据从单个数值变成了字符串，但是数据类型有点复杂。
    如果单元格内没有分隔符，那么就会被转化为单元素列表，且会自动转换其中的数字为python数字，
    如果有分隔符，则会根据分隔符打散成列表，并且将其中的数字转化成python数字。
    由于getattr方法获得的技能属性的数值永远是单个的，所以用 技能属性 in list 的判定逻辑，
    这样就可以实现“或”逻辑。
    """
    if isinstance(source, str):
        if "|" in source:
            split_list = source.split("|")
            return [eval(item) if item.isdigit() else item for item in split_list]
        else:
            return [eval(source) if source.isdigit() else source]
    else:
        return [source]


def process_buff_for_test(buff_0, sub_exist_buff_dict, mission):
    """
    本函数截取了process_buff函数的头部，专为Pytest服务，正常程序请勿调用！
    """
    all_match, judge_condition_dict, active_condition_dict = BuffInitialize(
        buff_0.ft.index, sub_exist_buff_dict
    )
    all_match = BuffJudge(buff_0, judge_condition_dict, mission)
    return all_match
