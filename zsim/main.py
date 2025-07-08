import argparse
import timeit

from zsim.simulator.config_classes import (
    AttrCurveConfig,
    WeaponConfig,
)
from zsim.simulator.simulator_class import Simulator

if __name__ == "__main__":
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="ZZZ模拟器")
    parser.add_argument(
        "--stop-tick", type=int, default=None, help="指定模拟的tick数量 int"
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="normal",
        choices=["normal", "parallel"],
        help="运行模式",
    )
    parser.add_argument(
        "--func",
        type=str,
        default=None,
        choices=["attr_curve", "weapon"],
        help="功能选择",
    )
    parser.add_argument(
        "--adjust-char",
        type=int,
        default=None,
        choices=[1, 2, 3],
        help="调整的角色相对位置",
    )
    parser.add_argument(
        "--sc-name", type=str, default=None, help="要调整的副词条名称 str"
    )
    parser.add_argument(
        "--sc-value", type=int, default=None, help="要调整的副词条数量 int"
    )
    parser.add_argument(
        "--run-turn-uuid", type=str, default=None, help="运行的uuid str"
    )
    parser.add_argument(
        "--remove-equip",
        action="store_true",
        default=False,
        help="移除装备 (存在此标志时移除)",
    )

    parser.add_argument(
        "--weapon-name",
        type=str,
        default=None,
        help="要调整的武器名称 str",
    )

    parser.add_argument(
        "--weapon-level",
        type=int,
        default=None,
        help="要调整的武器精炼等级 int",
    )

    # 解析命令行参数
    args = parser.parse_args()
    print(args)
    if args.mode == "normal":
        print("常规模式")
        # 常规模式，作为单进程运行，读取全部的配置
        simulator_instance = Simulator()

        if args.stop_tick is not None:
            print(
                f"\n主循环耗时: {timeit.timeit(lambda: simulator_instance.main_loop(args.stop_tick), globals=globals(), number=1):.2f} s"
            )
        else:
            print(
                f"\n主循环耗时: {timeit.timeit(simulator_instance.main_loop, globals=globals(), number=1):.2f} s"
            )

        print("\n正在等待IO结束···")
    elif args.mode == "parallel":
        print("并行模式")
        print(args)
        simulator_instance = Simulator()
        # 并行模式，作为子进程运行，角色的指定副词条将被设为传入值，并根据是否移除其他主副词条进行模拟
        if func := args.func == "attr_curve":
            sim_cfg: AttrCurveConfig = AttrCurveConfig(
                stop_tick=args.stop_tick,
                mode=args.mode,
                adjust_char=args.adjust_char,
                sc_name=args.sc_name,
                sc_value=args.sc_value,
                run_turn_uuid=args.run_turn_uuid,
                remove_equip=args.remove_equip,
            )
        elif func := args.func == "weapon":
            sim_cfg: WeaponConfig = WeaponConfig(
                stop_tick=args.stop_tick,
                mode=args.mode,
                adjust_char=args.adjust_char,
                weapon_name=args.weapon_name,
                weapon_level=args.weapon_level,
                run_turn_uuid=args.run_turn_uuid,
            )
        else:
            raise ValueError("func参数错误")
        if args.stop_tick is not None:
            print(
                f"\n主循环耗时: {timeit.timeit(lambda: simulator_instance.main_loop(args.stop_tick, sim_cfg=sim_cfg), globals=globals(), number=1):.2f} s"
            )
        else:
            print(
                f"\n主循环耗时: {timeit.timeit(lambda: simulator_instance.main_loop(sim_cfg=sim_cfg), globals=globals(), number=1):.2f} s"
            )
