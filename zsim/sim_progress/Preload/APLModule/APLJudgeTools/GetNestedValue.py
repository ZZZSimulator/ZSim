def get_nested_value(key_list: list, data):
    """递归获取嵌套结构中的值，一挖到底"""
    if not key_list:
        return data
    if len(key_list) > 1:
        key = key_list[0]
        if isinstance(data, dict) and key in data:
            return get_nested_value(data[key], key_list[1:])
        elif isinstance(data, list | tuple) and isinstance(key, int) and 0 <= key < len(data):
            return get_nested_value(data[key], key_list[1:])
    elif len(key_list) == 1:
        key = key_list[0]
        if isinstance(data, dict) and key in data:
            return data[key]
        elif isinstance(data, list | tuple) and isinstance(key, int) and 0 <= key < len(data):
            return data[key]
        else:
            raise ValueError(f"无法解析的数据类型！{data, type(data)}")
