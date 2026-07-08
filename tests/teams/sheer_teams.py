# -*- coding: utf-8 -*-
"""贯穿队伍配置"""

from zsim.models.session.session_run import CharConfig, CommonCfg, EnemyConfig

from .team_configs import TeamConfigBase, TeamRegistry


class SheerTeamYixuanAstraTriggerConfig(TeamConfigBase):
    """仪玄-耀嘉音-扳机试点队配置"""

    def __init__(self):
        super().__init__(
            team_name="仪玄-耀嘉音-扳机试点队",
            description="仪玄-耀嘉音-扳机贯穿路线试点队伍",
        )

    def create_config(self) -> CommonCfg:
        """创建仪玄-耀嘉音-扳机试点队配置"""
        return CommonCfg(
            session_id="test-team-pilot-yixuan-astra-trigger",
            char_config=[
                CharConfig(
                    name="仪玄",
                    weapon="青溟笼舍",
                    weapon_level=5,
                    cinema=6,
                    scATK_percent=47,
                    scCRIT=30,
                    scCRIT_DMG=50,
                    equip_style="4+2",
                    equip_set4="云岿如我",
                    equip_set2_a="啄木鸟电音",
                ),
                CharConfig(
                    name="耀嘉音",
                    weapon="飞鸟星梦",
                    weapon_level=1,
                    cinema=6,
                    scATK_percent=47,
                    scCRIT=30,
                    scCRIT_DMG=50,
                    equip_style="4+2",
                    equip_set4="静听嘉音",
                    equip_set2_a="摇摆爵士",
                ),
                CharConfig(
                    name="扳机",
                    weapon="索魂影眸",
                    weapon_level=5,
                    cinema=1,
                    scATK_percent=47,
                    scCRIT=30,
                    scCRIT_DMG=50,
                    equip_style="4+2",
                    equip_set4="如影相随",
                    equip_set2_a="折枝剑歌",
                ),
            ],
            enemy_config=EnemyConfig(index_id=11412, adjustment_id=22412, difficulty=8.74),
            apl_path="./zsim/data/APLData/仪玄-耀嘉音-扳机.toml",
        )

    def get_expected_characters(self) -> list:
        """获取预期的角色列表"""
        return ["仪玄", "耀嘉音", "扳机"]


class SheerTeamConfigs:
    """贯穿队伍配置集合"""

    @staticmethod
    def register_all():
        """注册所有贯穿队伍配置"""
        TeamRegistry.register(SheerTeamYixuanAstraTriggerConfig())

    @staticmethod
    def get_yixuan_team() -> SheerTeamYixuanAstraTriggerConfig:
        """获取仪玄-耀嘉音-扳机试点队配置"""
        return SheerTeamYixuanAstraTriggerConfig()

    @staticmethod
    def get_all_configs() -> list:
        """获取所有贯穿队伍配置"""
        return [SheerTeamConfigs.get_yixuan_team()]


SheerTeamConfigs.register_all()
