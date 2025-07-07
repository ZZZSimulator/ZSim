def detect_edge(pair, mode_func):
    # 使用自定义的mode_func函数来判断是否为上升沿或下降沿
    return mode_func(pair[0], pair[1])


def mode_func(a, b):
    return a is False and b is True


if __name__ == "__main__":
    list1 = [False, True]
    a = detect_edge(list1, mode_func)
    print(a)
