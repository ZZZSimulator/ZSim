import pandas as pd
import os
import sys


def import_csv_to_excel(csv_file, sheet_name, writer):
    """将CSV文件导入到Excel工作表中"""
    try:
        df = pd.read_csv(csv_file)
        df.to_excel(writer, sheet_name=sheet_name, index=False)
        print(f"成功导入 {csv_file} 到工作表 {sheet_name}")
        return True
    except Exception as e:
        print(f"导入 {csv_file} 时出错: {str(e)}")
        return False


def export_excel_to_csv(excel_file, sheet_name, csv_file):
    """将Excel工作表导出到CSV文件"""
    try:
        df = pd.read_excel(excel_file, sheet_name=sheet_name)
        df.to_csv(csv_file, index=False)
        print(f"成功导出工作表 {sheet_name} 到 {csv_file}")
        return True
    except Exception as e:
        print(f"导出工作表 {sheet_name} 时出错: {str(e)}")
        return False


# 定义文件和工作表的映射关系
FILE_SHEET_MAPPING = {
    "character.csv": "character",
    "skill.csv": "skill",
    "default_skill.csv": "default_skill",
    "weapon.csv": "weapon",
    "enemy.csv": "enemy",
    "enemy_adjustment.csv": "enemy_adjustment",
    "equip_set_2pc.csv": "equip_set_2pc",
    "buff_effect.csv": "buff_effect",
    "触发判断.csv": "触发判断",
    "激活判断.csv": "激活判断",
    "enemy_attack_action.csv": "enemy_attack_action",
    "enemy_attack_method.csv": "enemy_attack_method",
}


def csv_to_excel():
    """将所有CSV文件导入到Excel中"""
    # 定义Excel文件路径
    excel_file = "./zsim/data/game_data.xlsx"

    # 获取当前脚本所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # 创建ExcelWriter对象
    with pd.ExcelWriter(excel_file, engine="openpyxl") as writer:
        success_count = 0
        total_count = len(FILE_SHEET_MAPPING)
        # 导入每个CSV文件到对应的工作表
        for csv_file, sheet_name in FILE_SHEET_MAPPING.items():
            csv_path = os.path.join(current_dir, csv_file)
            if os.path.exists(csv_path):
                if import_csv_to_excel(csv_path, sheet_name, writer):
                    success_count += 1
            else:
                print(f"未找到CSV文件: {csv_path}")

    print(f"Excel文件创建完成，成功导入 {success_count}/{total_count} 个文件")


def excel_to_csv():
    """将Excel中的所有工作表导出到CSV文件"""
    # 定义Excel文件路径
    excel_file = "./zsim/data/game_data.xlsx"

    # 获取当前脚本所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # 检查Excel文件是否存在
    if not os.path.exists(excel_file):
        print(f"Excel文件不存在: {excel_file}")
        return

    success_count = 0
    total_count = len(FILE_SHEET_MAPPING)

    # 导出每个工作表到对应的CSV文件
    for csv_file, sheet_name in FILE_SHEET_MAPPING.items():
        csv_path = os.path.join(current_dir, csv_file)
        if export_excel_to_csv(excel_file, sheet_name, csv_path):
            success_count += 1

    print(f"CSV文件导出完成，成功导出 {success_count}/{total_count} 个工作表")


def print_help():
    """打印帮助信息"""
    print("CSV和Excel双向同步工具")
    print("用法:")
    print("  python csv_excel_sync.py [选项]")
    print("选项:")
    print("  -h, --help     显示此帮助信息")
    print("  -i, --import   从CSV导入到Excel")
    print("  -e, --export   从Excel导出到CSV")
    print("如果不提供选项，将进入交互模式")


def main():
    # 处理命令行参数
    if len(sys.argv) > 1:
        if sys.argv[1] in ["-h", "--help"]:
            print_help()
            return
        elif sys.argv[1] in ["-i", "--import"]:
            csv_to_excel()
            return
        elif sys.argv[1] in ["-e", "--export"]:
            excel_to_csv()
            return
        else:
            print(f"未知选项: {sys.argv[1]}")
            print_help()
            return

    # 交互模式
    while True:
        print("\nCSV和Excel双向同步工具")
        print("\033[91m1. 从CSV导入到Excel，会导致Excel的格式配置、表内公式全部丢失\033[0m")
        print("2. 从Excel导出到CSV")
        print("3. 退出")

        choice = input("请选择操作 [1-3]: ")

        if choice == "1":
            confirm = input(
                "\033[91m警告: 此操作会导致Excel的格式配置、表内公式全部丢失，是否继续？[y/n]: \033[0m"
            ).lower()
            if confirm == "y":
                csv_to_excel()
        elif choice == "2":
            confirm = input("确认要从Excel导出到CSV吗？[y/n]: ").lower()
            if confirm == "y":
                excel_to_csv()
        elif choice == "3":
            print("程序已退出")
            break
        else:
            print("无效选择，请重试")


if __name__ == "__main__":
    main()
