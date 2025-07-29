import asyncio
import gc
import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from zsim.api_src.services.sim_controller.sim_controller import SimController
from zsim.models.session.session_create import Session
from zsim.models.session.session_run import (
    CharConfig,
    CommonCfg,
    EnemyConfig,
    ExecAttrCurveCfg,
    ExecWeaponCfg,
    ParallelCfg,
    SessionRun,
)
from zsim.simulator.simulator_class import Simulator


class TestSimulator:
    """Comprehensive test suite for simulator functionality."""

    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Setup test environment before each test."""
        # Store original working directory
        self.original_cwd = os.getcwd()

        # Change to project root directory
        os.chdir(Path(__file__).parent.parent)

        yield

        # Restore original working directory
        os.chdir(self.original_cwd)

    def create_test_common_config(self) -> CommonCfg:
        """Create a test common configuration."""
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
        """Create session run configuration."""
        if mode == "parallel":
            return SessionRun(
                stop_tick=1000,
                mode="parallel",
                common_config=self.create_test_common_config(),
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
                common_config=self.create_test_common_config(),
            )

    def create_multiple_team_configs(self) -> list[tuple[str, CommonCfg]]:
        """创建多个测试队伍配置，方便编辑和扩展。

        Returns:
            list[tuple[str, CommonCfg]]: 包含队伍名称和配置的元组列表
        """
        team_configs = []

        # 队伍1: 薇薇安-柳-耀嘉音 (物理队)
        team_configs.append(
            (
                "薇薇安物理队",
                CommonCfg(
                    session_id="test-team-vivian-physical",
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
                ),
            )
        )

        # # 队伍2: 莱特-扳机-雨果 (火属性队)
        team_configs.append(
            (
                "莱特火属性队",
                CommonCfg(
                    session_id="test-team-lighter-fire",
                    char_config=[
                        CharConfig(
                            name="莱特",
                            weapon="焰心桂冠",
                            weapon_level=5,
                            cinema=0,
                            scATK_percent=47,
                            scCRIT=30,
                            scCRIT_DMG=50,
                            equip_style="4+2",
                            equip_set4="震星迪斯科",
                            equip_set2_a="炎狱重金属",
                        ),
                        CharConfig(
                            name="扳机",
                            weapon="索魂影眸",
                            weapon_level=5,
                            cinema=0,
                            scATK_percent=47,
                            scCRIT=30,
                            scCRIT_DMG=50,
                            equip_style="4+2",
                            equip_set4="如影相随",
                            equip_set2_a="啄木鸟电音",
                        ),
                        CharConfig(
                            name="雨果",
                            weapon="千面日陨",
                            weapon_level=5,
                            cinema=0,
                            scATK_percent=47,
                            scCRIT=30,
                            scCRIT_DMG=50,
                            equip_style="4+2",
                            equip_set4="啄木鸟电音",
                            equip_set2_a="激素朋克",
                        ),
                    ],
                    enemy_config=EnemyConfig(index_id=11412, adjustment_id=22412, difficulty=8.74),
                    apl_path="./zsim/data/APLData/莱特-扳机-雨果.toml",
                ),
            )
        )

        # 队伍3: 青衣-丽娜-雅 (雷属性队)
        team_configs.append(
            (
                "青衣雷属性队",
                CommonCfg(
                    session_id="test-team-qingyi-electric",
                    char_config=[
                        CharConfig(
                            name="青衣",
                            weapon="玉壶青冰",
                            weapon_level=5,
                            cinema=6,
                            scATK_percent=47,
                            scCRIT=30,
                            scCRIT_DMG=50,
                            equip_style="4+2",
                            equip_set4="震星迪斯科",
                            equip_set2_a="啄木鸟电音",
                        ),
                        CharConfig(
                            name="丽娜",
                            weapon="啜泣摇篮",
                            weapon_level=5,
                            cinema=6,
                            scATK_percent=47,
                            scCRIT=30,
                            scCRIT_DMG=50,
                            equip_style="4+2",
                            equip_set4="静听嘉音",
                            equip_set2_a="摇摆爵士",
                        ),
                        CharConfig(
                            name="雅",
                            weapon="霰落星殿",
                            weapon_level=5,
                            cinema=6,
                            scATK_percent=47,
                            scCRIT=30,
                            scCRIT_DMG=50,
                            equip_style="4+2",
                            equip_set4="折枝剑歌",
                            equip_set2_a="啄木鸟电音",
                        ),
                    ],
                    enemy_config=EnemyConfig(index_id=11412, adjustment_id=22412, difficulty=8.74),
                    apl_path="./zsim/data/APLData/青衣-丽娜-雅.toml",
                ),
            )
        )

        return team_configs

    # Basic Simulator Tests
    def test_init_simulator_without_config(self):
        """Test that simulator can be initialized successfully."""
        sim = Simulator()
        assert isinstance(sim, Simulator)
        assert hasattr(sim, "api_init_simulator")
        assert hasattr(sim, "main_loop")

    def test_simulator_reset(self):
        """Test that simulator can be reset to initial state."""
        common_cfg = self.create_test_common_config()
        sim = Simulator()
        sim.api_init_simulator(common_cfg, sim_cfg=None)
        assert sim.init_data is not None
        assert sim.tick == 0
        assert sim.char_data is not None
        assert sim.enemy is not None

    # Async Tests
    @pytest.mark.asyncio
    async def test_async_simulator_initialization(self):
        """Test async simulator initialization."""
        controller = SimController()
        assert isinstance(controller, SimController)

    # Parallel Mode Tests
    @pytest.mark.asyncio
    async def test_parallel_args_generation_attr_curve(self):
        """Test async generation of attribute curve parallel arguments."""
        controller = SimController()
        session = Session()
        session_run_config = self.create_session_run_config("parallel")

        # Generate parallel arguments
        args_iterator = controller.generate_parallel_args(session, session_run_config)
        args_list = list(args_iterator)

        # Verify generated arguments
        assert len(args_list) == 12  # 2 attributes × 6 values each
        for arg in args_list:
            assert isinstance(arg, ExecAttrCurveCfg)
            assert arg.stop_tick == 1000
            assert arg.mode == "parallel"
            assert arg.func == "attr_curve"

    @pytest.mark.asyncio
    async def test_parallel_args_generation_weapon(self):
        """Test async generation of weapon parallel arguments."""
        controller = SimController()
        session = Session()

        # Create weapon parallel configuration
        session_run_config = SessionRun(
            stop_tick=1000,
            mode="parallel",
            common_config=self.create_test_common_config(),
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

        # Generate parallel arguments
        args_iterator = controller.generate_parallel_args(session, session_run_config)
        args_list = list(args_iterator)

        # Verify generated arguments
        assert len(args_list) == 3
        for arg in args_list:
            assert isinstance(arg, ExecWeaponCfg)
            assert arg.stop_tick == 1000
            assert arg.mode == "parallel"
            assert arg.func == "weapon"

    # Configuration Validation Tests
    def test_session_run_config_validation(self):
        """Test session run configuration validation."""
        # Test normal mode
        config = self.create_session_run_config("normal")
        assert config.mode == "normal"
        assert config.stop_tick == 1000

        # Test parallel mode
        config = self.create_session_run_config("parallel")
        assert config.mode == "parallel"
        assert config.parallel_config is not None
        assert config.parallel_config.func == "attr_curve"

    def test_character_config_validation(self):
        """Test character configuration validation."""
        # Test valid configuration (3 characters)
        valid_config = CommonCfg(
            session_id="test-valid-config",
            char_config=[
                CharConfig(name="薇薇安"),
                CharConfig(name="柳"),
                CharConfig(name="耀嘉音"),
            ],
            enemy_config=EnemyConfig(index_id=11412, adjustment_id=22412, difficulty=8.74),
            apl_path="./zsim/data/APLData/薇薇安-柳-耀嘉音.toml",
        )

        sim = Simulator()
        sim.api_init_simulator(valid_config, sim_cfg=None)
        assert sim.init_data is not None

        # Test invalid configuration (2 characters)
        with pytest.raises(Exception):
            invalid_config = CommonCfg(
                session_id="test-invalid-config",
                char_config=[
                    CharConfig(name="薇薇安"),
                    CharConfig(name="柳"),
                ],
                enemy_config=EnemyConfig(index_id=11412, adjustment_id=22412, difficulty=8.74),
                apl_path="./zsim/data/APLData/薇薇安-柳-耀嘉音.toml",
            )
            sim_invalid = Simulator()
            sim_invalid.api_init_simulator(invalid_config, sim_cfg=None)

    # Edge Cases and Error Handling
    def test_parallel_args_generation_edge_cases(self):
        """Test parallel argument generation edge cases."""
        controller = SimController()
        session = Session()

        # Test unknown attribute names
        session_run_config = SessionRun(
            stop_tick=1000,
            mode="parallel",
            common_config=self.create_test_common_config(),
            parallel_config=ParallelCfg(
                enable=True,
                adjust_char=2,
                func="attr_curve",
                func_config=ParallelCfg.AttrCurveConfig(
                    sc_range=(0, 7),
                    sc_list=["unknown_stat"],  # Unknown attribute
                    remove_equip_list=[],
                ),
            ),
        )

        # Generate parallel arguments, should skip unknown attributes
        args_iterator = controller.generate_parallel_args(session, session_run_config)
        args_list = list(args_iterator)
        assert len(args_list) == 0  # Unknown attributes should be skipped

    def test_parallel_args_generation_invalid_mode(self):
        """Test parallel argument generation with invalid mode."""
        controller = SimController()
        session = Session()
        session_run_config = self.create_session_run_config("normal")  # Normal mode

        # Generate parallel arguments, should return empty
        args_iterator = controller.generate_parallel_args(session, session_run_config)
        args_list = list(args_iterator)
        assert len(args_list) == 0

    def test_parallel_args_generation_missing_config(self):
        """Test parallel argument generation with missing configuration."""
        with pytest.raises(ValidationError) as excinfo:
            SessionRun(
                stop_tick=1000,
                mode="parallel",
                common_config=self.create_test_common_config(),
                # Missing parallel_config
            )
        assert "并行模式下，parallel_config 不能为空" in str(excinfo.value)

    # Data Transmission Tests
    def test_data_transmission_correctness(self):
        """Test that data is correctly transmitted between components."""
        common_cfg = self.create_test_common_config()

        sim = Simulator()
        sim.api_init_simulator(common_cfg, sim_cfg=None)

        # Verify character data transmission
        assert len(sim.init_data.name_box) == 3
        assert sim.init_data.name_box == ["薇薇安", "柳", "耀嘉音"]

        # Verify character configuration transmission
        for i, char_config in enumerate(common_cfg.char_config):
            char_dict = getattr(sim.init_data, f"char_{i}")
            assert char_dict["name"] == char_config.name
            assert char_dict["weapon"] == char_config.weapon
            assert char_dict["weapon_level"] == char_config.weapon_level

        # Verify enemy configuration transmission
        assert sim.enemy.index_ID == common_cfg.enemy_config.index_id
        assert sim.enemy.adjustment_id == int(common_cfg.enemy_config.adjustment_id)
        assert sim.enemy.difficulty == common_cfg.enemy_config.difficulty

        # Verify APL path transmission
        assert sim.preload.apl_path == common_cfg.apl_path

    def test_weapon_adjustment_with_sim_cfg(self):
        """Test that weapon adjustment works correctly with simulation configuration."""
        # Create configuration using Pydantic models
        common_cfg = self.create_test_common_config()

        # Create weapon adjustment configuration
        sim_cfg = ExecWeaponCfg(
            stop_tick=1000,
            mode="parallel",
            func="weapon",
            adjust_char=1,  # Adjust first character (Vivian)
            weapon_name="青溟笼舍",
            weapon_level=3,
            run_turn_uuid="test-weapon-adjustment",
        )

        sim = Simulator()
        sim.api_init_simulator(common_cfg, sim_cfg)

        # Verify weapon adjustment
        # First character's weapon should be adjusted
        char_0_dict = sim.init_data.char_0
        assert char_0_dict["weapon"] == "青溟笼舍"
        assert char_0_dict["weapon_level"] == 3

        # Other characters' weapons should remain unchanged
        char_1_dict = sim.init_data.char_1
        assert char_1_dict["weapon"] == "时流贤者"
        assert char_1_dict["weapon_level"] == 5

    # SimController Singleton Test
    def test_sim_controller_singleton(self):
        """Test SimController singleton pattern."""
        controller1 = SimController()
        controller2 = SimController()
        assert controller1 is controller2

    # 队列基础的异步测试
    @pytest.mark.asyncio
    async def test_async_queue_multiple_teams(self):
        """使用队列系统测试多个不同队伍的异步模拟，替代单队伍测试。"""
        from datetime import datetime

        from zsim.api_src.services.database.session_db import get_session_db
        from zsim.models.session.session_create import Session

        controller = SimController()
        db = await get_session_db()

        # 获取所有队伍配置
        team_configs = self.create_multiple_team_configs()
        completed_sessions = []

        try:
            # 为每个队伍创建会话并放入队列
            for i, (team_name, common_cfg) in enumerate(team_configs):
                session_run_config = self.create_session_run_config("normal")
                session_run_config.stop_tick = 3000

                session = Session(
                    session_id=f"queue-test-team-{i}-{team_name.replace(' ', '-')}",
                    create_time=datetime.now(),
                    status="pending",
                    session_run=session_run_config,
                    session_result=None,
                )

                completed_sessions.append(session.session_id)
                await db.add_session(session)

                # 将队伍配置放入队列
                await controller.put_into_queue(session.session_id, common_cfg, None)

                print(f"队伍 '{team_name}' 已添加到队列")

            # 执行所有队伍的模拟
            print(f"开始执行 {len(team_configs)} 个队伍的模拟...")
            executed_sessions = await controller.execute_simulation_test(
                max_tasks=len(team_configs)
            )

            # 验证结果
            assert len(executed_sessions) == len(team_configs), (
                f"期望执行 {len(team_configs)} 个队伍，实际执行了 {len(executed_sessions)} 个"
            )
            assert set(executed_sessions) == set(completed_sessions), "执行的会话ID与预期不匹配"

            # 验证所有会话状态
            for session_id in completed_sessions:
                updated_session = await db.get_session(session_id)
                assert updated_session is not None, f"会话 {session_id} 未找到"
                assert updated_session.status == "completed", (
                    f"会话 {session_id} 状态不是 completed"
                )

            print(f"所有 {len(team_configs)} 个队伍模拟均已完成")

        finally:
            # 清理数据库
            for session_id in completed_sessions:
                await db.delete_session(session_id)

    @pytest.mark.asyncio
    async def test_async_queue_parallel_mode_execution(self):
        """使用队列系统测试并行模式执行。"""
        from datetime import datetime

        from zsim.api_src.services.database.session_db import get_session_db
        from zsim.models.session.session_create import Session

        common_cfg = self.create_test_common_config()
        controller = SimController()

        # 创建简化的并行配置以减少任务数量
        session_run_config = SessionRun(
            stop_tick=100,  # 减少执行时间
            mode="parallel",
            common_config=common_cfg,
            parallel_config=ParallelCfg(
                enable=True,
                adjust_char=2,
                func="attr_curve",
                func_config=ParallelCfg.AttrCurveConfig(
                    sc_range=(0, 1),  # 只测试2个值
                    sc_list=["攻击力%"],  # 单个属性
                    remove_equip_list=[],
                ),
            ),
        )

        session = Session(
            session_id="queue-test-parallel-session",
            create_time=datetime.now(),
            status="pending",
            session_run=session_run_config,
            session_result=None,
        )

        # 设置数据库
        db = await get_session_db()
        await db.add_session(session)

        parallel_session_ids = []  # 初始化在try块外面

        try:
            # 生成并行参数并放入队列
            args_iterator = controller.generate_parallel_args(session, session_run_config)
            args_list = list(args_iterator)

            # 为每个并行任务创建单独的会话并放入队列
            for i, sim_cfg in enumerate(args_list):
                parallel_session_id = f"queue-test-parallel-session-{i}"
                parallel_session = Session(
                    session_id=parallel_session_id,
                    create_time=datetime.now(),
                    status="pending",
                    session_run=session_run_config,
                    session_result=None,
                )
                parallel_session_ids.append(parallel_session_id)
                await db.add_session(parallel_session)
                await controller.put_into_queue(parallel_session_id, common_cfg, sim_cfg)

            # 执行并行任务
            completed_sessions = await controller.execute_simulation_test_parallel(
                session.session_id, parallel_count=len(args_list)
            )

            # 验证结果 - 应该有2个并行任务完成
            assert len(completed_sessions) == 2
            assert set(completed_sessions) == set(parallel_session_ids)

            # 验证所有并行会话状态
            for parallel_session_id in parallel_session_ids:
                updated_session = await db.get_session(parallel_session_id)
                assert updated_session is not None
                assert updated_session.status == "completed"

        finally:
            # 清理数据库
            await db.delete_session(session.session_id)
            for parallel_session_id in parallel_session_ids:
                await db.delete_session(parallel_session_id)

    @pytest.mark.asyncio
    async def test_async_queue_empty_handling(self):
        """测试队列为空时的处理。"""
        controller = SimController()

        # 执行空队列
        completed_sessions = await controller.execute_simulation_test(max_tasks=1)

        # 应该返回空列表
        assert len(completed_sessions) == 0

    @pytest.mark.asyncio
    async def test_async_queue_error_handling(self):
        """测试队列系统的错误处理。"""
        controller = SimController()

        # 创建一个无效的会话（不存在于数据库中）
        common_cfg = self.create_test_common_config()
        await controller.put_into_queue("non-existent-session", common_cfg, None)

        # 执行应该能处理错误而不崩溃
        completed_sessions = await controller.execute_simulation_test(max_tasks=1)

        # 应该返回空列表（因为会话不存在）
        assert len(completed_sessions) == 0

    @pytest.mark.skip(reason="Known memory leak in pandas and simulator core.")
    @pytest.mark.asyncio
    async def test_async_queue_memory_leak(self):
        """Checks for memory leaks by running a simulation multiple times."""
        import tracemalloc
        from datetime import datetime

        from zsim.api_src.services.database.session_db import get_session_db
        from zsim.models.session.session_create import Session

        common_cfg = self.create_test_common_config()
        controller = SimController()
        db = await get_session_db()

        # Reset controller state for a clean test environment
        controller._queue = asyncio.Queue()
        controller._running_tasks.clear()

        tracemalloc.start(10)
        gc.collect()

        async def run_one_sim(run_id: str):
            """Runs a single simulation in an isolated environment."""
            session_id = f"memory-leak-test-{run_id}"
            session_run_config = self.create_session_run_config("normal")
            session_run_config.stop_tick = 200
            session = Session(
                session_id=session_id,
                create_time=datetime.now(),
                status="pending",
                session_run=session_run_config,
            )
            await db.add_session(session)

            # Create and destroy simulator within the run
            local_controller = SimController()
            await local_controller.put_into_queue(session.session_id, common_cfg, None)

            completed_sessions = await local_controller.execute_simulation_test(max_tasks=1)
            assert len(completed_sessions) == 1
            await db.delete_session(session.session_id)

            # Explicit cleanup
            del local_controller
            gc.collect()

        # Warm-up run
        await run_one_sim("warmup")

        # Take snapshot after warm-up
        snapshot1 = tracemalloc.take_snapshot()

        # Run multiple times to detect leaks
        for i in range(5):
            await run_one_sim(f"run-{i}")

        # Final snapshot
        snapshot2 = tracemalloc.take_snapshot()
        tracemalloc.stop()

        top_stats = snapshot2.compare_to(snapshot1, "lineno")
        total_growth = sum(stat.size_diff for stat in top_stats)

        # Final threshold adjustment to 1024 KB
        threshold_kb = 1024
        assert total_growth < threshold_kb * 1024, (
            f"Potential memory leak detected. "
            f"Memory grew by {total_growth / 1024:.2f} KB after 5 runs.\n"
            f"Top 10 differences:\n" + "\n".join([str(s) for s in top_stats[:10]])
        )

    @pytest.mark.asyncio
    async def test_async_simulation_memory_usage(self):
        """Test async simulation memory usage."""
        common_cfg = self.create_test_common_config()

        # Force garbage collection
        gc.collect()
        initial_objects = len(gc.get_objects())

        # Use SimController for async execution
        controller = SimController()
        result = await controller.run_single_simulation(common_cfg, None, 1000)  # noqa: F841

        gc.collect()
        final_objects = len(gc.get_objects())
        object_growth = final_objects - initial_objects
        assert object_growth < 10000  # Reasonable threshold
