from typing import TYPE_CHECKING

from zsim.define import ENABLE_WATCHDOG, WATCHDOG_LEVEL
from zsim.sim_progress.Report import report_to_log

if TYPE_CHECKING:
    from zsim.sim_progress.Character.skill_class import Skill
    from zsim.sim_progress.Preload.SkillsQueue import SkillNode

if ENABLE_WATCHDOG:
    report_to_log("[INFO] Watchdog is enabled.", level=4)


def watch_reverse_order(
    current_node: "SkillNode | Skill.InitSkill",
    last_node: "SkillNode | Skill.InitSkill | None",
) -> bool | None:
    """
    监控技能队列中的技能加载顺序，如果发现逆序加载则发出警告。

    该函数检查当前节点和上一个节点的技能标签，判断是否存在逆序加载的情况。
    逆序加载指的是技能队列中本应先加载的技能后于其他技能加载，这可能是数据顺序错误或技能依赖关系处理不当导致的。

    参数:
    current_node: 当前正在检查的技能节点，可以是SkillsQueue.SkillNode或Skill_Class.Skill.InitSkill类型。
    last_node: 上一个已加载的技能节点，作为参考与当前节点比较。

    返回值:
    无。如果检测到逆序加载，会打印警告信息。
    """
    if not ENABLE_WATCHDOG:
        return None
    if WATCHDOG_LEVEL <= 0:
        return None
    if last_node is None:
        return None
    if not (isinstance(current_node, SkillNode) or isinstance(current_node, Skill.InitSkill)):
        return None
    if not (isinstance(last_node, SkillNode) or isinstance(last_node, Skill.InitSkill)):
        return None
    current_tag = current_node.skill_tag
    last_tag = last_node.skill_tag
    if current_tag[:-1] == last_tag[:-1]:
        if current_tag[-1] < last_tag[-1]:
            feedback = (
                f"[WARNING] Watchdog detected a reverse order preload event:"
                f"Is {current_tag} really behind of {last_tag}?"
            )
            print(feedback)
            report_to_log(feedback, level=0)
        return False
    return True


class WatchDog:
    def __init__(self, **kwargs):
        try:
            watch_reverse_order(**kwargs)
        except AttributeError:
            pass
