def find_buff_0(game_state: dict, char, buff_index):
    """
    根据buff的index来找到buff
    通常用于判断“当前是否有该Buff激活”
    """
    for _buff_index, _buff in game_state["load_data"].exist_buff_dict[char.NAME].items():
        if _buff_index == buff_index:
            return _buff
    else:
        return None

    # elif hasattr(data, key):  # 处理类对象
    #     return get_nested_value(getattr(data, key), key_list[1:])
    # else:
    #     raise ValueError(f'无法解析的数据类型！{data, type(data)}')
