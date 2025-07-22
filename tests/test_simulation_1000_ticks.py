import os
from pathlib import Path

import pytest

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

    def test_simulator_initialization(self):
        """Test that simulator can be initialized successfully."""
        sim = Simulator()
        assert isinstance(sim, Simulator)
        assert hasattr(sim, "cli_init_simulator")
        assert hasattr(sim, "main_loop")

    def test_simulator_reset(self):
        """Test that simulator can be reset to initial state."""
        sim = Simulator()
        sim.cli_init_simulator(sim_cfg=None)

        assert sim.init_data is not None
        assert sim.tick == 0
        assert sim.char_data is not None
        assert sim.enemy is not None

    def test_1000_tick_simulation_runs(self):
        """Test that simulation runs for 1000 ticks successfully."""
        from zsim.simulator.simulator_class import Simulator

        # Create fresh simulator instance
        sim = Simulator()

        # Initialize simulator
        sim.cli_init_simulator(sim_cfg=None)

        # Run simulation for 1000 ticks
        sim.main_loop(stop_tick=1000)

        # Verify simulation completed
        assert sim.tick >= 1000
        assert sim.init_data is not None
        assert sim.char_data is not None
        assert sim.enemy is not None

    def test_simulation_data_integrity(self):
        """Test that simulation data remains consistent after 1000 ticks."""
        sim = Simulator()
        sim.cli_init_simulator(sim_cfg=None)

        # Store initial state
        initial_char_count = len(sim.char_data.char_obj_list)

        # Run simulation
        sim.main_loop(stop_tick=1000)

        # Verify data integrity
        assert len(sim.char_data.char_obj_list) == initial_char_count
        assert sim.enemy.max_HP is not None
        assert sim.enemy.max_HP >= 0

    def test_simulation_memory_usage(self):
        """Test that simulation doesn't leak memory over 1000 ticks."""
        import gc

        sim = Simulator()
        sim.cli_init_simulator(sim_cfg=None)

        # Force garbage collection before simulation
        gc.collect()

        # Store initial memory usage (rough approximation)
        initial_objects = len(gc.get_objects())

        # Run simulation
        sim.main_loop(stop_tick=1000)

        # Force garbage collection after simulation
        gc.collect()

        # Verify memory usage is reasonable
        final_objects = len(gc.get_objects())

        # Allow for some object growth, but not excessive
        object_growth = final_objects - initial_objects
        assert object_growth < 10000  # Reasonable threshold for 1000 ticks

    def test_simulation_tick_progression(self):
        """Test that simulation progresses tick by tick correctly."""
        sim = Simulator()
        sim.cli_init_simulator(sim_cfg=None)

        # Run simulation in smaller chunks to verify progression
        target_ticks = 1000
        chunk_size = 100

        for chunk_start in range(0, target_ticks, chunk_size):
            chunk_end = min(chunk_start + chunk_size, target_ticks)
            sim.main_loop(stop_tick=chunk_end)

            # Verify tick progression
            assert sim.tick >= chunk_end

        # Verify final tick count
        assert sim.tick >= target_ticks

    @pytest.mark.slow
    def test_full_1000_tick_simulation(self):
        """Full integration test for 1000-tick simulation."""
        sim = Simulator()

        # Use configuration from file
        config_path = Path("zsim/config.json")
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                import json

                config = json.load(f)
                config["stop_tick"] = 1000
        else:
            # Fallback to example config
            config_path = Path("zsim/config_example.json")
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    config["stop_tick"] = 1000

        # Initialize and run simulation
        sim.cli_init_simulator(sim_cfg=None)
        sim.main_loop(stop_tick=1000)

        # Verify simulation completed successfully
        assert sim.tick >= 1000
        assert sim.init_data is not None
        assert sim.char_data is not None
        assert sim.enemy is not None

        print(f"✓ Simulation completed successfully at tick {sim.tick}")


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
