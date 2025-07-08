from .Buff0Manager import Buff0Manager  # noqa: F401
from .buff_class import Buff, spawn_buff_from_index  # noqa: F401
from .BuffAdd import buff_add  # noqa: F401
from .BuffLoad import BuffInitialize, BuffLoadLoop  # noqa: F401
from .JudgeTools import *  # noqa: F403
from .ScheduleBuffSettle import ScheduleBuffSettle  # noqa: F401


# TODO:
#  buff.ft.label = {"only_CoAttack": 1, "only_技能skill_tag": 1}
#   skill.label = {"CoAttack": 1, "accept_buff_Buff名字": 1}
#   按照如上格式，进行Buff的数据库拓展，并且写好构造函数的对应接口。
