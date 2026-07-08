from __future__ import annotations

from typing import TYPE_CHECKING, Final, Literal

if TYPE_CHECKING:
    from ...Character.Alice import Alice
    from ...Character.character import Character
    from ...Character.Seed import Seed
    from ...Character.Yixuan import Yixuan
    from ...data_struct.ActionStack import ActionStack
    from ...Enemy import Enemy
    from ...Preload.PreloadDataClass import PreloadData
    from ..buff_class import Buff


BuffRecordFieldCategory = Literal[
    "stable_identity",
    "run_scoped_read_snapshot",
    "mutable_local_state",
    "retained_old_template_link",
]

BUFF_RECORD_FIELD_CLASSIFICATION: Final[dict[str, BuffRecordFieldCategory]] = {
    "char": "run_scoped_read_snapshot",
    "sub_exist_buff_dict": "retained_old_template_link",
    "dynamic_buff_list": "run_scoped_read_snapshot",
    "enemy": "run_scoped_read_snapshot",
    "equipper": "stable_identity",
    "action_stack": "run_scoped_read_snapshot",
    "preload_data": "run_scoped_read_snapshot",
    "char_obj_list": "run_scoped_read_snapshot",
    "na_skill_level": "stable_identity",
    "trans_ratio": "mutable_local_state",
    "cd": "mutable_local_state",
    "last_active_tick": "mutable_local_state",
    "buff_index": "stable_identity",
    "trigger_buff_0": "retained_old_template_link",
    "additional_damage_skill_tag": "stable_identity",
    "trigger_skill_tag": "stable_identity",
}


class BuffRecordBaseClass:
    def __init__(self):
        self.char: "Character | None | Alice | Yixuan | Seed" = None
        self.sub_exist_buff_dict: dict[str, "Buff"] | None = None
        self.dynamic_buff_list: dict[str, list] | None = None
        self.enemy: "Enemy | None" = None
        self.equipper: "str | None" = None
        self.action_stack: "ActionStack | None" = None
        self.preload_data: "PreloadData | None" = None
        self.char_obj_list: "list[Character] | None" = None
        self.na_skill_level: "int | None" = None
        self.trans_ratio: float = 0
        self.cd: int = 60  # 内置CD：1秒一次
        self.last_active_tick: int = 0  # 上次触发的时间点
        self.buff_index: str | None = None
        self.trigger_buff_0: "Buff | None" = None
        self.additional_damage_skill_tag: str | None = None
        self.trigger_skill_tag: str | None = None

    def check_cd(self, tick_now: int):
        """检查内置CD是否就绪"""
        if self.cd == 0:
            return True
        if tick_now - self.last_active_tick < self.cd:
            return False
        else:
            return True
