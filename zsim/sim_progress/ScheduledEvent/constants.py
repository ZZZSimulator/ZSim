"""
事件常量定义

该模块定义了 ScheduledEvent 模块中使用的各种常量。
"""


class EventConstants:
    """事件相关常量"""

    # 默认优先级
    DEFAULT_PRIORITY = 0

    # 缓存相关
    MAX_CACHE_SIZE = 128

    # 时间精度
    TICK_PRECISION = 0.0000001

    # 二分查找阈值
    BINARY_SEARCH_THRESHOLD = 10

    # 事件列表最大大小
    EVENT_LIST_MAX_SIZE = 1000

    @classmethod
    def validate_constants(cls) -> None:
        """验证常量值的合理性"""
        assert cls.MAX_CACHE_SIZE > 0, "缓存大小必须大于0"
        assert cls.TICK_PRECISION > 0, "时间精度必须大于0"
        assert cls.BINARY_SEARCH_THRESHOLD > 0, "二分查找阈值必须大于0"
        assert cls.EVENT_LIST_MAX_SIZE > 0, "事件列表最大大小必须大于0"
        assert cls.DEFAULT_PRIORITY >= 0, "默认优先级必须大于等于0"

    # 事件类型名称
    EVENT_TYPES = {
        "skill": "技能事件",
        "anomaly": "异常事件",
        "disorder": "紊乱事件",
        "polarity_disorder": "极性紊乱事件",
        "abloom": "薇薇安异放事件",
        "refresh": "数据刷新事件",
        "quick_assist": "快速支援事件",
        "preload": "预加载事件",
        "stun_forced_termination": "眩晕强制终止事件",
        "polarized_assault": "极性强击事件",
    }

    # 执行时间键映射
    EXECUTE_TICK_KEYS = {
        "SkillNode": "preload_tick",
        "QuickAssistEvent": "execute_tick",
        "SchedulePreload": "execute_tick",
        "PolarizedAssaultEvent": "execute_tick",
    }

    # 优先级定义（数字越大优先级越低）
    PRIORITY = {
        "HIGH": 0,  # 高优先级，数字最小
        "MEDIUM": 500,  # 中等优先级
        "LOW": 800,  # 低优先级
        "VERY_LOW": 999,  # 极低优先级，数字最大
    }

    # 异常更新规则
    ANOMALY_UPDATE_RULES = {
        "ALWAYS": -1,
        "NEVER": 0,
    }


class ErrorMessages:
    """错误消息常量"""

    # 参数验证错误
    INVALID_LOADING_BUFF_TYPE = "loading_buff参数必须为字典，但你输入了{}"
    INVALID_TICK_TYPE = "tick参数必须为整数，但你输入了{}"
    TARGET_NOT_FOUND = "[Schedule] target: {} 不在 char_obj_list 中，请检查分配逻辑。"
    CHARACTER_NOT_FOUND = "{} 不在 char_obj_list 中"
    INVALID_EVENT_TYPE = "{}，目前不应存在于 event_list"

    # 事件处理错误
    FUTURE_EVENT_PROCESSING = "event_start主循环正在尝试处理一个名为{}的未来事件"
    ATTRIBUTE_NOT_FOUND = "{} 没有属性 {}"
    INVALID_EVENT_HANDLER = "无法找到适合处理事件类型 {} 的处理器"

    # 缓存错误
    CACHE_SIZE_EXCEEDED = "缓存大小超过限制: {}"
    CACHE_KEY_NOT_FOUND = "缓存键未找到: {}"


class WarningMessages:
    """警告消息常量"""

    # Buff相关警告
    DYNAMIC_BUFF_NOT_FOUND = "[警告] 动态Buff列表内没有角色 {}"
    BUFF_LIST_EMPTY = "[警告] Buff列表为空"

    # 事件处理警告
    EVENT_NOT_HANDLED = "[警告] 事件未被处理: {}"
    HANDLER_NOT_FOUND = "[警告] 未找到事件处理器: {}"

    # 性能警告
    LARGE_EVENT_LIST = "[警告] 事件列表过大: {}"
    SLOW_EVENT_PROCESSING = "[警告] 事件处理耗时过长: {}s"
