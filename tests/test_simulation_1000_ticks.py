import os
from pathlib import Path

import pytest

from zsim.models.session.session_run import (
    CharConfig,
    CommonCfg,
    EnemyConfig,
    SessionRun,
)
from zsim.simulator.simulator_class import Simulator


class TestSimulation1000Ticks:
    """Test suite for 1000-tick simulation."""

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
        """Create a test common configuration using Pydantic models."""
        return CommonCfg(
            session_id="test-session-1000-ticks",
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

    def test_simulator_initialization(self):
        """Test that simulator can be initialized successfully."""
        sim = Simulator()
        assert isinstance(sim, Simulator)
        assert hasattr(sim, "api_init_simulator")
        assert hasattr(sim, "main_loop")

    def test_simulator_reset(self):
        """Test that simulator can be reset to initial state."""
        # Create configuration using Pydantic models
        common_cfg = self.create_test_common_config()

        sim = Simulator()
        sim.api_init_simulator(common_cfg, sim_cfg=None)

        assert sim.init_data is not None
        assert sim.tick == 0
        assert sim.char_data is not None
        assert sim.enemy is not None

    def test_1000_tick_simulation_runs(self):
        """Test that simulation runs for 1000 ticks successfully."""
        # Create configuration using Pydantic models
        common_cfg = self.create_test_common_config()

        # Create fresh simulator instance
        sim = Simulator()

        # Initialize simulator
        sim.api_init_simulator(common_cfg, sim_cfg=None)

        # Run simulation for 1000 ticks
        sim.main_loop(stop_tick=1000, use_api=True)

        # Verify simulation completed
        assert sim.tick >= 1000
        assert sim.init_data is not None
        assert sim.char_data is not None
        assert sim.enemy is not None

    def test_simulation_data_integrity(self):
        """Test that simulation data remains consistent after 1000 ticks."""
        # Create configuration using Pydantic models
        common_cfg = self.create_test_common_config()

        sim = Simulator()
        sim.api_init_simulator(common_cfg, sim_cfg=None)

        # Store initial state
        initial_char_count = len(sim.char_data.char_obj_list)

        # Run simulation
        sim.main_loop(stop_tick=1000, use_api=True)

        # Verify data integrity
        assert len(sim.char_data.char_obj_list) == initial_char_count
        assert sim.enemy.max_HP is not None
        assert sim.enemy.max_HP >= 0

    def test_simulation_memory_usage(self):
        """Test that simulation doesn't leak memory over 1000 ticks."""
        import gc

        # Create configuration using Pydantic models
        common_cfg = self.create_test_common_config()

        sim = Simulator()
        sim.api_init_simulator(common_cfg, sim_cfg=None)

        # Force garbage collection before simulation
        gc.collect()

        # Store initial memory usage (rough approximation)
        initial_objects = len(gc.get_objects())

        # Run simulation
        sim.main_loop(stop_tick=1000, use_api=True)

        # Force garbage collection after simulation
        gc.collect()

        # Verify memory usage is reasonable
        final_objects = len(gc.get_objects())

        # Allow for some object growth, but not excessive
        object_growth = final_objects - initial_objects
        assert object_growth < 10000  # Reasonable threshold for 1000 ticks

    def test_simulation_tick_progression(self):
        """Test that simulation progresses tick by tick correctly."""
        # Create configuration using Pydantic models
        common_cfg = self.create_test_common_config()

        sim = Simulator()
        sim.api_init_simulator(common_cfg, sim_cfg=None)

        # Run simulation in smaller chunks to verify progression
        target_ticks = 1000
        chunk_size = 100

        for chunk_start in range(0, target_ticks, chunk_size):
            chunk_end = min(chunk_start + chunk_size, target_ticks)
            sim.main_loop(stop_tick=chunk_end, use_api=True)

            # Verify tick progression
            assert sim.tick >= chunk_end

        # Verify final tick count
        assert sim.tick >= target_ticks

    @pytest.mark.slow
    def test_full_1000_tick_simulation(self):
        """Full integration test for 1000-tick simulation."""
        # Create configuration using Pydantic models
        common_cfg = self.create_test_common_config()

        # Create session run configuration
        session_run_config = SessionRun(  # noqa: F841
            stop_tick=1000,
            mode="normal",
            common_config=common_cfg,
        )

        # Create simulator instance
        sim = Simulator()

        # Initialize and run simulation
        sim.api_init_simulator(common_cfg, sim_cfg=None)
        sim.main_loop(stop_tick=1000, use_api=True)

        # Verify simulation completed successfully
        assert sim.tick >= 1000
        assert sim.init_data is not None
        assert sim.char_data is not None
        assert sim.enemy is not None

        print(f"✓ Simulation completed successfully at tick {sim.tick}")

    def test_api_run_simulator(self):
        """Test the API run simulator method."""
        # Create configuration using Pydantic models
        common_cfg = self.create_test_common_config()

        # Create session run configuration
        session_run_config = SessionRun(  # noqa: F841
            stop_tick=1000,
            mode="normal",
            common_config=common_cfg,
        )

        # Create simulator instance
        sim = Simulator()

        # Run simulation using API method
        result = sim.api_run_simulator(common_cfg, None, 1000)

        # Verify result
        assert result.session_id == common_cfg.session_id
        assert result.status == "completed"
        assert result.sim_cfg is None
        assert sim.tick >= 1000

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
        # This should not raise an exception
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

    def test_data_transmission_correctness(self):
        """Test that data is correctly transmitted between components."""
        # Create configuration using Pydantic models
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
            assert char_dict["CID"] == char_config.CID
            assert char_dict["weapon"] == char_config.weapon
            assert char_dict["weapon_level"] == char_config.weapon_level

        # Verify enemy configuration transmission
        assert sim.enemy.index_ID == common_cfg.enemy_config.index_id
        assert sim.enemy.adjustment_id == int(common_cfg.enemy_config.adjustment_id)
        assert sim.enemy.difficulty == common_cfg.enemy_config.difficulty

        # Verify APL path transmission
        assert sim.preload.apl_path == common_cfg.apl_path

    def test_parallel_simulation_config_transmission(self):
        """Test that parallel simulation configuration is correctly transmitted."""
        from zsim.models.session.session_run import ExecAttrCurveCfg

        # Create configuration using Pydantic models
        common_cfg = self.create_test_common_config()

        # Create parallel simulation configuration
        sim_cfg = ExecAttrCurveCfg(
            stop_tick=1000,
            mode="parallel",
            func="attr_curve",
            adjust_char=2,
            sc_name="scATK_percent",
            sc_value=10,
            run_turn_uuid="test-parallel-config",
        )

        sim = Simulator()
        sim.api_init_simulator(common_cfg, sim_cfg)

        # Verify parallel configuration transmission
        assert sim.in_parallel_mode is True
        assert sim.sim_cfg is not None
        assert isinstance(sim.sim_cfg, ExecAttrCurveCfg)
        assert sim.sim_cfg.sc_name == "scATK_percent"
        assert sim.sim_cfg.sc_value == 10
        assert sim.sim_cfg.adjust_char == 2

    def test_weapon_adjustment_with_sim_cfg(self):
        """Test that weapon adjustment works correctly with simulation configuration."""
        from zsim.models.session.session_run import ExecWeaponCfg

        # Create configuration using Pydantic models
        common_cfg = self.create_test_common_config()

        # Create weapon adjustment configuration
        sim_cfg = ExecWeaponCfg(
            stop_tick=1000,
            mode="parallel",
            func="weapon",
            adjust_char=1,  # 调整第一个角色（薇薇安）
            weapon_name="青溟笼舍",
            weapon_level=3,
            run_turn_uuid="test-weapon-adjustment",
        )

        sim = Simulator()
        sim.api_init_simulator(common_cfg, sim_cfg)

        # Verify weapon adjustment
        # 第一个角色的武器应该被调整
        char_0_dict = sim.init_data.char_0
        assert char_0_dict["weapon"] == "青溟笼舍"
        assert char_0_dict["weapon_level"] == 3

        # 其他角色的武器应该保持不变
        char_1_dict = sim.init_data.char_1
        assert char_1_dict["weapon"] == "时流贤者"
        assert char_1_dict["weapon_level"] == 5


if __name__ == "__main__":
    # Run the test directly for debugging
    test = TestSimulation1000Ticks()
    test.setup_test_environment()

    try:
        test.test_full_1000_tick_simulation()
        print("✓ All simulation tests passed!")
    except Exception as e:
        print(f"✗ Simulation test failed: {e}")
        raise
