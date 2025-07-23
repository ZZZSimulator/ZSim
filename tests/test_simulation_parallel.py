import os
from pathlib import Path
import pytest
from pydantic import ValidationError

from zsim.api_src.services.sim_controller.sim_controller import SimController
from zsim.models.session.session_run import (
    CharConfig,
    CommonCfg,
    EnemyConfig,
    ExecAttrCurveCfg,
    ExecWeaponCfg,
    ParallelCfg,
    SessionRun,
)
from zsim.models.session.session_create import Session
from zsim.simulator.simulator_class import Simulator


class TestSimulationParallel:
    """并行模拟测试套件."""

    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """在每个测试前设置测试环境."""
        # 存储原始工作目录
        self.original_cwd = os.getcwd()

        # 切换到项目根目录
        os.chdir(Path(__file__).parent.parent)

        yield

        # 恢复原始工作目录
        os.chdir(self.original_cwd)

    def create_common_config(self) -> CommonCfg:
        """创建通用配置."""
        return CommonCfg(
            session_id="test-session-001",
            char_config=[
                CharConfig(
                    name="薇薇安",
                    weapon="青溟笼舍",
                    weapon_level=5,
                    cinema=6,
                    scATK_percent=47,
                    scCRIT=30,
                    scCRIT_DMG=50,
                    equip_style="4+2",
                    equip_set4="自由蓝调",
                    equip_set2_a="灵魂摇滚",
                ),
                CharConfig(
                    name="柳",
                    weapon="时流贤者",
                    weapon_level=5,
                    cinema=6,
                    scATK_percent=47,
                    scCRIT=30,
                    scCRIT_DMG=50,
                    equip_style="4+2",
                    equip_set4="自由蓝调",
                    equip_set2_a="灵魂摇滚",
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
                    equip_set4="自由蓝调",
                    equip_set2_a="灵魂摇滚",
                ),
            ],
            enemy_config=EnemyConfig(index_id=11412, adjustment_id=22412, difficulty=8.74),
            apl_path="./zsim/data/APLData/薇薇安-柳-耀嘉音.toml",
        )

    def create_session_run_config(self, mode: str = "normal") -> SessionRun:
        """创建会话运行配置."""
        if mode == "parallel":
            return SessionRun(
                stop_tick=1000,
                mode="parallel",
                common_config=self.create_common_config(),
                parallel_config=ParallelCfg(
                    enable=True,
                    adjust_char=2,
                    func="attr_curve",
                    func_config=ParallelCfg.AttrCurveConfig(
                        sc_range=(0, 5),
                        sc_list=["攻击力%", "暴击率"],
                        remove_equip_list=[],
                    ),
                ),
            )
        else:
            return SessionRun(
                stop_tick=1000,
                mode="normal",
                common_config=self.create_common_config(),
            )

    def test_sim_controller_singleton(self):
        """测试 SimController 是单例模式."""
        controller1 = SimController()
        controller2 = SimController()
        assert controller1 is controller2

    def test_session_run_config_validation(self):
        """测试会话运行配置验证."""
        # 测试正常模式
        config = self.create_session_run_config("normal")
        assert config.mode == "normal"
        assert config.stop_tick == 1000

        # 测试并行模式
        config = self.create_session_run_config("parallel")
        assert config.mode == "parallel"
        assert config.parallel_config is not None
        assert config.parallel_config.func == "attr_curve"

    def test_generate_parallel_args_attr_curve(self):
        """测试生成属性曲线并行参数."""
        controller = SimController()
        session = Session()
        session_run_config = self.create_session_run_config("parallel")

        # 生成并行参数
        args_iterator = controller.generate_parallel_args(session, session_run_config)
        args_list = list(args_iterator)

        # 验证生成的参数
        assert len(args_list) == 12
        for arg in args_list:
            assert isinstance(arg, ExecAttrCurveCfg)
            assert arg.stop_tick == 1000
            assert arg.mode == "parallel"
            assert arg.func == "attr_curve"

    def test_generate_parallel_args_weapon(self):
        """测试生成武器并行参数."""
        controller = SimController()
        session = Session()

        # 创建武器并行配置
        session_run_config = SessionRun(
            stop_tick=1000,
            mode="parallel",
            common_config=self.create_common_config(),
            parallel_config=ParallelCfg(
                enable=True,
                adjust_char=2,
                func="weapon",
                func_config=ParallelCfg.WeaponConfig(
                    weapon_list=[
                        ParallelCfg.WeaponConfig.SingleWeapon(name="青溟笼舍", level=5),
                        ParallelCfg.WeaponConfig.SingleWeapon(name="时流贤者", level=5),
                        ParallelCfg.WeaponConfig.SingleWeapon(name="飞鸟星梦", level=1),
                    ]
                ),
            ),
        )

        # 生成并行参数
        args_iterator = controller.generate_parallel_args(session, session_run_config)
        args_list = list(args_iterator)

        # 验证生成的参数
        assert len(args_list) == 3
        for arg in args_list:
            assert isinstance(arg, ExecWeaponCfg)
            assert arg.stop_tick == 1000
            assert arg.mode == "parallel"
            assert arg.func == "weapon"

    def test_api_run_simulator_normal_mode(self):
        """测试 API 运行模拟器（正常模式）."""
        # 创建配置
        common_cfg = self.create_common_config()
        session_run_config = self.create_session_run_config("normal")

        # 运行模拟器
        simulator = Simulator()
        result = simulator.api_run_simulator(common_cfg, None, session_run_config.stop_tick)

        # 验证结果
        assert result.run_turn_uuid == common_cfg.session_id
        assert result.status == "completed"
        assert result.sim_cfg is None

    def test_api_run_simulator_parallel_mode(self):
        """测试 API 运行模拟器（并行模式）."""
        # 创建配置
        common_cfg = self.create_common_config()
        session_run_config = self.create_session_run_config("parallel")

        # 获取第一个并行参数
        controller = SimController()
        session = Session()
        args_iterator = controller.generate_parallel_args(session, session_run_config)
        
        # 运行所有并行模拟
        results = []
        for sim_cfg in args_iterator:
            simulator = Simulator()
            result = simulator.api_run_simulator(common_cfg, sim_cfg, session_run_config.stop_tick)
            results.append(result)

        # 验证结果
        assert len(results) == 12
        for result in results:
            assert result.run_turn_uuid == common_cfg.session_id
            assert result.status == "completed"
            assert result.sim_cfg is not None
            assert isinstance(result.sim_cfg, ExecAttrCurveCfg)

    def test_parallel_args_generation_edge_cases(self):
        """测试并行参数生成的边界情况."""
        controller = SimController()
        session = Session()

        # 测试未知属性名称
        session_run_config = SessionRun(
            stop_tick=1000,
            mode="parallel",
            common_config=self.create_common_config(),
            parallel_config=ParallelCfg(
                enable=True,
                adjust_char=2,
                func="attr_curve",
                func_config=ParallelCfg.AttrCurveConfig(
                    sc_range=(0, 7),
                    sc_list=["unknown_stat"],  # 未知属性
                    remove_equip_list=[],
                ),
            ),
        )

        # 生成并行参数，应该跳过未知属性
        args_iterator = controller.generate_parallel_args(session, session_run_config)
        args_list = list(args_iterator)
        assert len(args_list) == 0  # 未知属性应该被跳过

    def test_parallel_args_generation_invalid_mode(self):
        """测试并行参数生成的无效模式."""
        controller = SimController()
        session = Session()
        session_run_config = self.create_session_run_config("normal")  # 正常模式

        # 生成并行参数，应该返回空
        args_iterator = controller.generate_parallel_args(session, session_run_config)
        args_list = list(args_iterator)
        assert len(args_list) == 0

    def test_parallel_args_generation_missing_config(self):
        """测试并行参数生成缺少配置的情况."""
        with pytest.raises(ValidationError) as excinfo:
            SessionRun(
                stop_tick=1000,
                mode="parallel",
                common_config=self.create_common_config(),
                # 缺少 parallel_config
            )
        assert "并行模式下，parallel_config 不能为空" in str(excinfo.value)
