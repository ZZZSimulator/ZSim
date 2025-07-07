from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zsim.simulator.simulator_class import Simulator


def get_game_state(sim_instance: "Simulator"):
    """获取game_state"""
    return sim_instance.game_state
