#!/usr/bin/env python3
"""
绘制异常轴图的脚本。
该脚本读取本地results目录下的damage.csv文件，并根据其中的信息绘制一个透明背景的异常轴图。


启动命令：python zsim/script/draw_anomaly_timeline.py results/359

"""

import os
import sys
import argparse
try:
    import pandas as pd
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    print("错误: 缺少必要的依赖包。请安装 pandas 和 plotly:")
    print("  pip install pandas plotly")
    sys.exit(1)


def find_consecutive_true_ranges(df, column):
    """查找DataFrame列中连续为True的范围。

    Args:
        df (pd.DataFrame): 输入的DataFrame，需要包含 'tick' 列。
        column (str): 要查找的布尔列名。

    Returns:
        list[tuple[int, int]]: 一个包含 (开始tick, 结束tick) 元组的列表。
    """
    ranges = []
    start = None

    # 获取tick列和指定列的值
    ticks = df["tick"].tolist()
    values = df[column].tolist()

    for i, (tick, value) in enumerate(zip(ticks, values)):
        if value:
            if start is None:
                start = tick
        else:
            if start is not None:
                # 结束tick应该是上一个为True的tick
                prev_tick = ticks[i - 1] if i > 0 else start
                ranges.append((start, prev_tick))
                start = None
    # 处理最后一个区间（如果存在）
    if start is not None:
        ranges.append((start, ticks[-1]))
    return ranges


def prepare_timeline_data(df):
    """准备用于绘制异常状态时间线的数据。

    Args:
        df (pd.DataFrame): 原始伤害数据。

    Returns:
        tuple: (用于绘制Gantt图的DataFrame, 每种异常状态的平均持续时间字典)
    """
    required_columns = [
        "冻结",
        "霜寒",
        "畏缩",
        "感电",
        "灼烧",
        "侵蚀",
        "烈霜霜寒",
        "tick",
    ]
    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        raise ValueError(f"输入数据缺少必要的列: {missing_cols}")

    columns_to_check = ["冻结", "霜寒", "畏缩", "感电", "灼烧", "侵蚀", "烈霜霜寒"]
    gantt_data = []
    duration_stats = {}
    
    for col in columns_to_check:
        if col in df.columns:
            ranges = find_consecutive_true_ranges(df, col)
            durations = [end - start + 1 for start, end in ranges]  # 持续时间包含首尾
            duration_stats[col] = durations
            
            for start, end in ranges:
                gantt_data.append({"Task": col, "Start": start, "Finish": end})

    if not gantt_data:
        return pd.DataFrame(), {}

    gantt_df = pd.DataFrame(gantt_data)
    gantt_df["Duration"] = gantt_df["Finish"] - gantt_df["Start"] + 1  # 持续时间包含首尾
    
    # 计算每种异常状态的平均持续时间
    avg_durations = {}
    for col, durations in duration_stats.items():
        if durations:
            avg_durations[col] = sum(durations) / len(durations)
        else:
            avg_durations[col] = 0
    
    return gantt_df, avg_durations


def draw_anomaly_timeline(gantt_df, output_path=None):
    """绘制异常状态时间线（Gantt图）。

    Args:
        gantt_df (pd.DataFrame): 用于绘制Gantt图的数据。
        output_path (str, optional): 输出图片文件路径（例如 output.png）。
    """
    if gantt_df is not None and len(gantt_df) > 0:
        fig = px.bar(
            gantt_df,
            x="Duration",
            y="Task",
            base="Start",
            orientation="h",
            labels={
                "Start": "开始时间(帧)",
                "Duration": "持续时间(帧)",
                "Task": "状态类型",
            },
            height=350,
        )
        
        # 设置透明背景
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
        )
        
        # 设置网格线颜色
        fig.update_xaxes(showgrid=True, gridwidth=3, gridcolor='rgba(128,128,128,0.2)')
        fig.update_yaxes(showgrid=True, gridwidth=3, gridcolor='rgba(128,128,128,0.2)')
        
        if output_path:
            # 保存为PNG图片
            try:
                fig.write_image(output_path, width=1200, height=300)
                print(f"异常轴图已保存至: {output_path}")
            except ValueError as e:
                if "kaleido" in str(e).lower():
                    print("错误: 缺少kaleido包，无法保存图片。请安装kaleido:")
                    print("  pip install kaleido")
                    print("或者只在浏览器中查看图表，不使用 -o 参数")
                    sys.exit(1)
                else:
                    raise e
        else:
            # 在浏览器中显示
            fig.show()
    else:
        print("没有找到任何连续的状态数据")


def main():
    parser = argparse.ArgumentParser(description="绘制异常轴图")
    parser.add_argument("result_dir", help="战斗日志所在的结果目录，例如 results/123")
    parser.add_argument("-o", "--output", help="输出图片文件路径（例如 output.png）")
    
    args = parser.parse_args()
    
    # 如果指定了输出路径，检查kaleido是否可用
    if args.output:
        try:
            import plotly.io as pio
            # 尝试导入kaleido
            pio.kaleido.scope
        except ImportError:
            print("警告: 如果要保存图片，请安装kaleido:")
            print("  pip install kaleido")
            print("否则请只在浏览器中查看图表，不使用 -o 参数")
    
    # 构建damage.csv文件路径
    damage_csv_path = os.path.join(args.result_dir, "damage.csv")
    
    # 检查文件是否存在
    if not os.path.exists(damage_csv_path):
        print(f"错误: 文件 {damage_csv_path} 不存在")
        sys.exit(1)
    
    # 读取damage.csv文件
    try:
        df = pd.read_csv(damage_csv_path)
        print(f"成功读取文件: {damage_csv_path}")
    except Exception as e:
        print(f"读取文件时出错: {e}")
        sys.exit(1)
    
    # 准备数据
    try:
        gantt_df, avg_durations = prepare_timeline_data(df)
        print("数据准备完成")
    except Exception as e:
        print(f"准备数据时出错: {e}")
        sys.exit(1)
    
    # 输出每种异常状态的平均持续时间
    print("\n各异常状态的平均持续时间:")
    print("-" * 30)
    for anomaly, avg_duration in avg_durations.items():
        if avg_duration == 0:
            continue
        print(f"{anomaly}: {avg_duration/60:.2f} 秒")
    print("-" * 30)
    
    # 绘制图表
    try:
        draw_anomaly_timeline(gantt_df, args.output)
        print("异常轴图绘制完成")
    except Exception as e:
        print(f"绘制图表时出错: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
