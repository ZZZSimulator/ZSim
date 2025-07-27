import threading
import uuid
from typing import TYPE_CHECKING, Iterable

import pandas as pd

from zsim.define import APL_MODE, ElementType
from zsim.define import ELEMENT_TYPE_MAPPING as ETM
from zsim.sim_progress.Character.skill_class import Skill
from zsim.sim_progress.data_struct.LinkedList import LinkedList
from zsim.sim_progress.Report import report_to_log

if TYPE_CHECKING:
    from zsim.sim_progress.Load import LoadingMission


class SkillNode:
    _instance_counter = 0
    _counter_lock = threading.Lock()

    def __init__(
        self,
        skill: Skill.InitSkill,
        preload_tick: int,
        active_generation: bool = False,
        apl_unit=None,
        **kwargs,
    ):
        """
        预加载技能节点

        包含：
        1、部分需要立即调用的信息；
        2、整个 Skill.InitSkill 对象，包含了技能的全部信息，用于计算器调用
        """
        with SkillNode._counter_lock:
            self.apl_priority: int = kwargs.get("apl_priority", 0)
            self.apl_unit = apl_unit
            self.skill_tag: str = skill.skill_tag
            self.char_name: str = skill.char_name
            self.preload_tick: int = preload_tick
            self.hit_times: int = skill.hit_times
            self.labels: dict[str, list[str] | str | int | float] | None = skill.labels
            self.skill: Skill.InitSkill = skill
            self.end_tick: int = self.preload_tick + self.skill.ticks
            self.active_generation: bool = active_generation  # 构造函数的调用来源是否是主动动作
            # TODO：后续需用UUID替换skill_node实例ID
            self.instance_id = SkillNode._instance_counter
            SkillNode._instance_counter += 1
            # 生成 UUID
            self.UUID = uuid.uuid4()
            tick_list = []
            if self.skill.tick_list:
                for hit_tick in self.skill.tick_list:
                    tick_key = self.preload_tick + hit_tick
                    tick_list.append(tick_key)
            else:
                time_step = (self.skill.ticks - 1) / (self.hit_times + 1)
                for i in range(self.hit_times):
                    tick_key = self.preload_tick + time_step * (i + 1)
                    tick_list.append(tick_key)
            self.tick_list = tick_list

            self.loading_mission: "LoadingMission | None" = None
            self._effective_anomaly_buildup: bool = True
            self._element_type_change: ElementType | None = None
            self.force_qte_trigger: bool = False

    @property
    def element_type(self) -> ElementType:
        """返回当前的属性种类！（考虑染色）"""
        if self._element_type_change is None:
            return self.skill.element_type
        else:
            return self._element_type_change

    @property
    def element_type_change(self) -> ElementType | None:
        """技能的染色"""
        return self._element_type_change

    @element_type_change.setter
    def element_type_change(self, value: ElementType | None):
        if self._element_type_change is not None:
            raise ValueError(
                f"技能{self.skill_tag}已经被染色为【{ETM.get(self._element_type_change)}】属性！不能被重复染色！"
            )
        self._element_type_change = value

    @property
    def effective_anomaly_buildup(self) -> bool:
        """判断技能是否为异常技能"""
        return self._effective_anomaly_buildup

    @effective_anomaly_buildup.setter
    def effective_anomaly_buildup(self, value: bool):
        self._effective_anomaly_buildup = value

    def __str__(self) -> str:
        return f"SkillNode: {self.skill_tag}"

    @classmethod
    def get_total_instances(cls) -> int:
        """获取当前skill_node的唯一ID，该ID在skill_node被构造时就已经确定"""
        return cls._instance_counter

    def have_label(self, label_key: str):
        """判断当前skill_node是否拥有传入数值的skill_label"""
        if self.skill.labels is None:
            return False
        if self.labels is not None and label_key in self.labels.keys():
            return True
        else:
            return False

    def is_heavy_hit(self, tick: int) -> bool:
        """判断当前技能是否为重击"""
        if not self.skill.heavy_attack:
            return False
        last_hit = self.tick_list[-1]

        if tick - 1 < last_hit <= tick:
            return True
        else:
            return False

    def is_hit_now(self, tick: int) -> bool:
        """判断当前技能是否命中"""
        for tick_key in self.tick_list:
            if tick - 1 < tick_key <= tick:
                return True
            continue
        else:
            return False

    def is_last_hit(self, tick: int):
        """判断当前tick是否存在最后一击"""
        if not self.is_hit_now(tick):
            return False
        else:
            return tick - 1 < self.tick_list[-1] <= tick


def spawn_node(tag: str, preload_tick: int, skills: Iterable[Skill], **kwargs) -> SkillNode:
    """
    通过输入的tag和preload_tick，直接创建SkillNode。
    """
    active_generation = kwargs.get("active_generation", False)
    apl_priority = kwargs.get("apl_priority", 0)
    apl_unit = kwargs.get("apl_unit", None)
    for obj in skills:
        if tag in obj.skills_dict.keys():
            node = SkillNode(
                obj.skills_dict[tag],
                preload_tick,
                active_generation,
                apl_priority=apl_priority,
                apl_unit=apl_unit,
            )
            return node
    else:
        raise ValueError(
            f"预加载技能 {tag} 不存在于输入的 Skill 类中，请检查输入, "
            f"当前技能列表为：{[(skill.name, skill.skills_dict.keys()) for skill in skills]}"
        )


def get_skills_queue(
    preload_table: pd.DataFrame,
    *skills: Skill,
) -> tuple[int, LinkedList]:
    """
    提取dataframe中，‘skill_tag’列的信息
    并将其与输入的 Skill 类比对
    可输入任意数量的 Skill 类比对。

    示例：
    get_skills_queue(dataframe,
                     skills = Skill( name='艾莲'),
                     skills_2 = Skill(name = '苍角'),
                     skills_3 = Skill(name = '莱卡恩'))

    返回：一个链表，包含全部可被预加载的 SkillNode
    """
    # 输入类型检查
    if not isinstance(preload_table, pd.DataFrame):
        raise TypeError("预加载序列表必须是 pandas.DataFrame 类型")
    if not all(isinstance(x, Skill) for x in skills):
        raise TypeError("输入的技能必须是 Skill 类")

    skills_queue = LinkedList()  # 用于储存技能节点
    preload_skills: pd.Series = pd.Series()
    try:
        preload_skills: pd.Series = preload_table["skill_tag"]  # 传入的数据必须包含 skill_tag 列
    except KeyError:
        print("提供错误的预加载序列表，请检查输入")

    # 确保技能列表不为空
    if not preload_skills.empty:
        preload_skills_list: list[str] = preload_skills.tolist()
    else:
        raise ValueError("预加载序技能列表为空")

    preload_tick_stamps = {skill.CID: 0 for skill in skills}
    if not APL_MODE:
        for tag in preload_skills_list:
            cid = int(tag[:4])  # 提取tag的前四个字符作为key
            if cid not in preload_tick_stamps:
                raise ValueError(f"技能 {tag} 的CID不在输入的技能列表中，请检查输入")

            try:
                # 在__main__中寻找tick变量，并与preload_tick_stamp比较
                tick = globals().get("tick", 0)
                preload_tick_stamp = max(
                    preload_tick_stamps[cid], tick
                )  # 取最大值作为preload_tick_stamp
                node = spawn_node(tag, preload_tick_stamp, skills)
                skills_queue.add(node)
                preload_tick_stamps[cid] = (
                    preload_tick_stamp + node.skill.ticks
                )  # 更新preload_tick_stamp
                report_to_log(
                    f"[PRELOAD]:预加载节点 {tag} 已创建，将在 {preload_tick_stamps[cid]} 执行",
                    level=2,
                )
            except ValueError as e:
                raise ValueError(str(e))

    return max(preload_tick_stamps.values()), skills_queue


if __name__ == "__main__":
    pass
