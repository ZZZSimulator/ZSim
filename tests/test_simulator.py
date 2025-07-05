from zsim.simulator.simulator_class import Simulator


class TestSimulator:
    def test_init_simulator_without_config(self):
        sim = Simulator()
        assert isinstance(sim, Simulator)

    def test_simulator_reset(self):
        sim = Simulator()
        sim.reset_simulator(sim_cfg=None)
        assert sim.init_data is not None
