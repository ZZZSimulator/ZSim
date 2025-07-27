import os.path
import re
from typing import Sequence


class APLParser:
    def __init__(self, apl_code: str | None = None, file_path: str | None = None):
        # 如果传入APL代码，使用它；如果传入文件路径，则从文件中读取
        if apl_code is not None:
            self.apl_code = apl_code
        elif file_path is not None:
            self.apl_code = self._read_apl_from_file(file_path)
        else:
            raise ValueError("Either apl_code or file_path must be provided.")

    @staticmethod
    def _read_apl_from_file(file_path: str) -> str:
        """从文件中读取APL代码。"""
        try:
            # 检查文件扩展名
            if file_path.endswith(".toml"):
                import toml

                with open(file_path, "r", encoding="utf-8") as f:
                    toml_dict: dict = toml.load(f)
                    # 如果存在apl_logic表的logic，返回其内容，否则返回空字符串
                    return toml_dict.get("apl_logic", {}).get("logic", "")
            else:
                # 非toml文件按原有方式处理
                with open(file_path, "r", encoding="utf-8") as f:
                    return f.read()
        except FileNotFoundError as e:
            print(f"Error reading file {file_path}: {e}")
            return ""

    def parse(self, mode: int) -> list[dict[str, Sequence[str]]]:
        """
        apl_code本来是一大串str，现在要通过这个函数，将其变为列表内含多字典的模式。
        action下面存的应该是技能ID或是Skill的Triggle_Buff_Level，
        而conditions下面存的则是发动动作的条件。
        这一步应该在初始化的时候执行。
        """
        actions = []
        priority = 0
        if mode == 0:
            priority = 1
            selected_char_cid = []
        for line in self.apl_code.splitlines():
            # 去除空白字符并清理行内注释
            line = line.split("#", 1)[0].strip()
            # 忽略空行
            if not line:
                continue
            try:
                if mode == 0:
                    # 0. 更新CID，
                    if int(line[:4]) not in selected_char_cid:
                        selected_char_cid.append(int(line[:4]))
                # 1. 按 '|' 分割字符串
                parts = line.split("|")
                if len(parts) < 3:
                    raise ValueError(f"Invalid format: {line}")

                # 2. 提取 CID
                CID = parts[0]
                apl_type = parts[1]
                # 3. 提取 action_name 和条件部分
                action_name = parts[2]
                conditions = parts[3:]  # 从第4个元素开始作为条件列表
                # 兼容|作为与门表达式符号的逻辑,转为一整条表达式字符串,统一解析出子条件列表
                condition_expression = " and ".join(conditions).strip()
                conditions, logic_tree = parse_logical_expression(condition_expression)

                # 4. 记录解析后的数据
                actions.append(
                    {
                        "CID": CID,
                        "type": apl_type.strip(),
                        "action": action_name.strip(),
                        "conditions": [cond.strip() for cond in conditions if cond.strip()],
                        "conditions_tree": logic_tree,  # dict表示的逻辑树结构
                        "priority": priority,
                    }
                )
                if mode == 0:
                    priority += 1
            except Exception as e:
                print(f"Error parsing line: {line}, Error: {e}")
                continue
        if mode == 0:
            """
            这个if分枝的功能是：部分角色可能因角色特性而存在一些默认优先级最高的行为，
            在APL代码进行解析和拆分时，这些优先级最高的代码会被安插在所有APL的最前端。
            如果某角色存在着优先级永远最高的默认手法，则可以用这个功能实现，把对应的APL逻辑写到DefaultConfig中即可。
            但是注意，DefaultConfig中的所有APL代码均会以最高优先级进行执行，
            所以一般情况下还是推荐对APL进行全面定制
            """
            for cid in selected_char_cid:
                dir_path = "./data/APLData/default_APL"
                default_file_name = f"{cid}.txt"
                full_path = dir_path + "/" + default_file_name
                if not os.path.isfile(full_path):
                    continue
                else:
                    default_action = APLParser(file_path=full_path).parse(mode=1)
                    actions[:0] = default_action
        return renumber_priorities(actions)


def renumber_priorities(data_list):
    seen = set()  # 记录已使用的优先级值
    current_max = -1  # 跟踪当前最大有效优先级

    for item in data_list:
        original = item["priority"]

        # 策略1：优先保持原有数值（如果未被占用）
        if original not in seen:
            seen.add(original)
            current_max = max(current_max, original)
        # 策略2：分配当前最大+1（当原值已被占用时）
        else:
            current_max += 1
            item["priority"] = current_max
            seen.add(current_max)

    return data_list


def tokenize(expression):
    # 括号、and、or 分割，保留分隔符
    return re.findall(r"\(|\)|\band\b|\bor\b|[^()\s]+", expression)


def extract_conditions(tokens):
    # 提取子条件单元（非运算符和括号）
    return sorted(set(t for t in tokens if t not in ("and", "or", "(", ")")))


def parse_expression(tokens):
    """解析逻辑表达式, 返回逻辑树结构, 优先级为()>and>or"""
    if not tokens:
        return None

    def parse_factor(index):
        """解析基本因子：括号或单个条件"""
        token = tokens[index]
        if token == "(":
            subtree, index = parse_or(index + 1)
            if tokens[index] != ")":
                raise ValueError("缺失右括号")
            return subtree, index + 1
        else:
            return token, index + 1

    def parse_and(index):
        """解析 and 级别表达式"""
        left, index = parse_factor(index)
        items = [left]
        while index < len(tokens) and tokens[index] == "and":
            right, index = parse_factor(index + 1)
            items.append(right)
        return {"and": items} if len(items) > 1 else items[0], index

    def parse_or(index):
        """解析 or 级别表达式"""
        left, index = parse_and(index)
        items = [left]
        while index < len(tokens) and tokens[index] == "or":
            right, index = parse_and(index + 1)
            items.append(right)
        return {"or": items} if len(items) > 1 else items[0], index

    tree, final_index = parse_or(0)  # 从最低优先级开始解析
    if final_index != len(tokens):
        raise ValueError("无法解析整个表达式")
    return tree


def parse_logical_expression(expr):
    tokens = tokenize(expr)
    conditions = extract_conditions(tokens)
    logic_tree = parse_expression(tokens)
    return conditions, logic_tree


if __name__ == "__main__":
    code = "1211|action+=|1211_NA_1|status.enemy:stun==True and !buff.1091:exist→Buff-角色-丽娜-核心被动-穿透率==True"
    # actions_list = APLParser(file_path=APL_PATH).parse(mode=0)
    actions_list = APLParser(apl_code=code).parse(mode=0)
    for sub_dict in actions_list:
        print(sub_dict)
