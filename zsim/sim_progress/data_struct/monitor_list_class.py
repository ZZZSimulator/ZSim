def monitor_list_operation(func):
    """装饰器：监视列表操作并打印变化信息"""

    def wrapper(self, *args, **kwargs):
        # 操作前状态
        # print(f"Before {func.__name__}: {self}")
        # 执行原始操作
        result = func(self, *args, **kwargs)
        # 操作后状态
        # print(f"After {func.__name__}: {self}")
        return result

    return wrapper


class MonitoredList(list):
    """自定义列表类，监视 append/remove 操作"""

    @monitor_list_operation
    def append(self, item):
        # print(f"添加了{item.ft.index}dot")
        super().append(item)  # 调用父类方法

    @monitor_list_operation
    def remove(self, item):
        # print(f"移除了{item.ft.index}dot")
        super().remove(item)  # 调用父类方法
