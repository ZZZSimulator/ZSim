from zsim.define import SWAP_CANCEL


def get_last_action(game_state: dict):
    """
    注意，这个函数获取的应该是最新的主动动作的名称，
    """
    if SWAP_CANCEL:
        if game_state is None or game_state["preload"] is None:
            return False
        return game_state["preload"].preload_data.latest_active_generation_node
    else:
        last_node = getattr(game_state["preload"].preload_data, "last_node", None)
        if last_node is None:
            return None
        output = last_node.skill_tag
        return output
