# -*- coding: utf-8 -*-
"""基础模拟器测试"""

from zsim.simulator.simulator_class import Simulator

# 使用标准的相对导入，IDE 可以识别
from ..test_simulator import TestSimulator as _SimulatorTestHelper


class TestBasicSimulator:
    """基础模拟器功能测试"""

    def test_init_simulator_without_config(self):
        """Test that simulator can be initialized successfully."""
        sim = Simulator()
        assert isinstance(sim, Simulator)
        assert hasattr(sim, "api_init_simulator")
        assert hasattr(sim, "main_loop")

    def test_simulator_reset(self):
        """Test that simulator can be reset to initial state."""

        test_sim = _SimulatorTestHelper()

        # 使用原有的测试方法创建配置
        common_cfg = test_sim.create_test_common_config()
        sim = Simulator()
        sim.api_init_simulator(common_cfg, sim_cfg=None)
        assert sim.init_data is not None
        assert sim.tick == 0
        assert sim.char_data is not None
        assert sim.enemy is not None
