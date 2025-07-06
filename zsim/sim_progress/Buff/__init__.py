from .Buff0Manager import Buff0Manager
from .buff_class import Buff, spawn_buff_from_index
from .BuffAdd import buff_add
from .BuffLoad import BuffInitialize, BuffLoadLoop
from .JudgeTools import *
from .ScheduleBuffSettle import ScheduleBuffSettle


# TODO:
#  buff.ft.label = {"only_CoAttack": 1, "only_技能skill_tag": 1}
#   skill.label = {"CoAttack": 1, "accept_buff_Buff名字": 1}
#   按照如上格式，进行Buff的数据库拓展，并且写好构造函数的对应接口。
