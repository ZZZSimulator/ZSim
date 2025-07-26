from collections import defaultdict

from zsim.define import SWAP_CANCEL


class ActionStack:
    """
    这个动作栈无法记录所有的动作，只能记录所有的前台角色的主动技能。
    功能类似于wow的插件TrufigGCD。但是长度只有2，因为只需要记录“上一个动作”和“当前动作”
    """

    def __init__(self, length: int = 2):
        # 初始化一个空的栈，用列表作为基础
        """
        关于动作栈的更新：
        在更新了合轴模式后，部分依赖检测ActionStack的状态来判断的函数会出现错误。
        因为旧版本的ActionStack只能记录“全队上一个动作”，但是如果同一个tickPreload阶段抛出了多个动作，
        那么ActionStack只能记录最后一个动作，导致部分该触发的buff无法触发。
        因此，我们更新了ActionStack的结构，为其增加了personal_stack属性，使其可以记录“每个角色上一个动作”。
        并且，我们还更新了ActionStack的各个方法，为它们增加了key参数，当我们打开合轴模式，并且传入Key参数时，
        pop、peek方法会返回对应角色的上一个动作，
        但是相应的，如果我们没有开启合轴模式，那么传入Key参数时就会报错。
        """
        self.length = length
        if SWAP_CANCEL:
            self.personal_stack = defaultdict(list)
            self._swap_cancel_warning_printed = False  # 标志变量，用于控制警告信息只打印一次

        self.stack = []

    def push(self, item, /):
        """向栈中压入一个元素，如果栈内元素超过2个，移除最早的元素"""
        if SWAP_CANCEL:
            key = item.mission_character
            self.personal_stack[key].append(item)
            if len(self.personal_stack[key]) > self.length:
                self.personal_stack[key].pop(0)
        self.stack.append(item)
        # 如果栈的大小超过 2，就删除栈底元素（即最先加入的元素）
        if len(self.stack) > self.length:
            self.stack.pop(0)  # pop(0) 移除栈底元素

    def pop(self, /, key: str = None):
        """从栈顶弹出一个元素"""
        if key:
            if not SWAP_CANCEL:
                raise ValueError("往ActionStack的pop方法中传入key参数时，合轴模式必须开启！")
            if key not in self.personal_stack or len(self.personal_stack[key]) == 0:
                return None
            pop_item = self.personal_stack[key].pop()
            return pop_item
        else:
            if self.is_empty():
                return None
            else:
                return self.stack.pop()

    def peek(self, /, key: str = None):
        """查看栈顶元素"""
        if key:
            if not SWAP_CANCEL:
                raise ValueError("往ActionStack的peek方法中传入key参数时，合轴模式必须开启！")
            if key not in self.personal_stack or len(self.personal_stack[key]) == 0:
                return None
            return self.personal_stack[key][-1]
        else:
            if SWAP_CANCEL and not self._swap_cancel_warning_printed:
                print(
                    "Warning: 在开启合轴模式的情况下，在调用ActionStack的peek方法时并未传入key参数！\n这会导致在含有多个动作的tick，peek方法只会返回最后一个动作，从而让部分buff无法正常触发！"
                )
                self._swap_cancel_warning_printed = True  # 标记为已打印
            if not self.is_empty():
                return self.stack[-1]
            else:
                return None

    def is_empty(self):
        """判断栈是否为空"""
        return len(self.stack) == 0

    def peek_bottom(self, /, key: str = None):
        """查看栈底元素"""
        if key:
            if not SWAP_CANCEL:
                raise ValueError(
                    "往ActionStack的peek_bottom方法中传入key参数时，合轴模式必须开启！"
                )
            if key not in self.personal_stack or len(self.personal_stack[key]) == 0:
                return None
            return self.personal_stack[key][0]
        else:
            if not self.is_empty():
                return self.stack[0]
            else:
                return None

    def __len__(self):
        return len(self.stack)

    def __str__(self):
        return str(self.stack)

    def __iter__(self):
        return iter(self.stack)

    def __getitem__(self, index, /):
        return self.stack[index]

    def __eq__(self, value: object, /) -> bool:
        return self.stack == value or self.stack == getattr(value, "stack", None)

    def __ne__(self, value: object, /) -> bool:
        return not self.__eq__(value)

    def reset_myself(self):
        if SWAP_CANCEL:
            self.personal_stack = defaultdict(list)
            self._swap_cancel_warning_printed = False  # 标志变量，用于控制警告信息只打印一次
        self.stack = []


class NodeStack:
    def __init__(self, length: int = 3):
        self.length = length
        self.stack = []

    def push(self, item, /):
        self.stack.append(item)
        if len(self.stack) > self.length:
            self.stack.pop(0)

    def pop(self):
        if self.is_empty():
            return None
        else:
            return self.stack.pop()

    def peek(self, /):
        if not self.is_empty():
            return self.stack[-1]
        else:
            return None

    def peek_index(self, index: int):
        if self.is_empty():
            return None
        if index > len(self.stack):
            # print(f"index out of range， 当前stack长度为{len(self.stack)}")
            return None
        return self.stack[-index]

    def is_empty(self):
        """判断栈是否为空"""
        return len(self.stack) == 0

    def peek_bottom(self, /):
        """查看栈底元素"""
        if not self.is_empty():
            return self.stack[0]
        else:
            return None

    def get_effective_node(self):
        """排除附加伤害技能，来获取有效的技能。"""
        if self.is_empty():
            return None
        else:
            i = 1
            while i <= len(self.stack):
                if self.stack[-i].skill.labels is not None:
                    if "additional_damage" in self.stack[-i].skill.labels:
                        i += 1
                        continue
                return self.stack[-i]

    def get_on_field_node(self, tick_now: int):
        """
        这个函数是NodeStack的内置方法，用来获取当前Stack中的前台技能
        鉴于合轴模式中，各角色的技能情况比较复杂，所以这个函数返回的结果并不一定准确。
        1、当目前场上没有node时，返回None
        2、当目前场上只有1个ndoe时，无论这个node是什么类型，都返回该node
        3、当目前场上存在多个node时，应返回最新的那个主动动作的SkillNode
        """
        _exist_node_list = []
        _active_node_now = False
        for _node in self.stack:
            if _node.end_tick >= tick_now:
                if _node.active_generation:
                    _active_node_now = True
                _exist_node_list.append(_node)
        # print([nodes.skill_tag for nodes in _exist_node_list])
        if len(_exist_node_list) == 0:
            return None
        elif len(_exist_node_list) == 1:
            return _exist_node_list[0]
        elif len(_exist_node_list) > 1:
            if _active_node_now:
                return max(
                    (x for x in _exist_node_list if x.active_generation),
                    key=lambda x: x.preload_tick,
                )
            else:
                """当场上的node全部都是被动动作时，只取其中最新的那个。"""
                return max((x for x in _exist_node_list), key=lambda x: x.preload_tick)

    def reset(self):
        self.stack = []

    def last_node_is_end(self, tick) -> bool:
        """判断上一个skillnode是否结束"""
        if self.is_empty():
            return True
        last_node = self.peek()
        if last_node.end_tick <= tick:
            return True
        else:
            return False

    def __len__(self):
        return len(self.stack)

    def __str__(self):
        return str(self.stack)

    def __iter__(self):
        return iter(self.stack)

    def __getitem__(self, index, /):
        return self.stack[index]

    def __eq__(self, value: object, /) -> bool:
        return self.stack == value or self.stack == getattr(value, "stack", None)

    def __ne__(self, value: object, /) -> bool:
        return not self.__eq__(value)
