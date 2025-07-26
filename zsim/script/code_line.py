import os


def count_effective_lines(directory):
    total_lines = 0
    for root, dirs, files in os.walk(directory):
        # 排除 .venv 目录
        if ".venv" in dirs:
            dirs.remove(".venv")
        for file in files:
            if file.endswith((".py", ".txt", ".c", ".cpp", ".h")):
                file_path = os.path.join(root, file)
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    # 根据文件类型过滤掉空行和注释行
                    if file.endswith(".py") or file.endswith(".txt"):
                        effective_lines = [
                            line
                            for line in lines
                            if line.strip() and not line.strip().startswith("#")
                        ]
                    elif file.endswith(".c") or file.endswith(".cpp") or file.endswith(".h"):
                        effective_lines = [
                            line
                            for line in lines
                            if line.strip()
                            and not line.strip().startswith("//")
                            and not line.strip().startswith("/*")
                        ]
                    total_lines += len(effective_lines)
    return total_lines


def count_total_lines(directory):
    total_lines = 0
    for root, dirs, files in os.walk(directory):
        # 排除 .venv 目录
        if ".venv" in dirs:
            dirs.remove(".venv")
        for file in files:
            if file.endswith((".py", ".txt", ".c", ".cpp", ".h")):
                file_path = os.path.join(root, file)
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    total_lines += len(lines)
    return total_lines


if __name__ == "__main__":
    # 指定目录
    directory = "./"
    # 计算有效代码行数
    effective_lines = count_effective_lines(directory)
    print(f"有效代码行数: {effective_lines}")
    # 计算总代码行数
    total_lines = count_total_lines(directory)
    print(f"总代码行数: {total_lines}")
