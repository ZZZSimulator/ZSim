# -*- coding: utf-8 -*-
"""安全的并发队伍测试，通过进程隔离避免环境共享"""

import asyncio
import gc
import os
import uuid
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import pytest

from zsim.api_src.services.database.session_db import get_session_db
from zsim.models.session.session_create import Session

# 导入团队配置
from ..teams import auto_register_teams


def run_simulation_in_process(common_cfg_dict, session_id, stop_tick=1000):
    """在独立进程中运行模拟

    Args:
        common_cfg_dict: 配置字典（避免序列化问题）
        session_id: 会话ID
        stop_tick: 停止tick数

    Returns:
        dict: 模拟结果
    """
    try:
        # 导入必要的模块（在子进程中）
        from zsim.models.session.session_run import CommonCfg
        from zsim.simulator.simulator_class import Simulator

        # 重建配置对象
        common_cfg = CommonCfg.model_validate(common_cfg_dict)

        # 创建模拟器实例
        simulator = Simulator()

        # 运行模拟
        simulator.api_run_simulator(common_cfg, None, stop_tick)

        # 清理
        del simulator
        gc.collect()

        return {"success": True, "session_id": session_id, "error": None}

    except Exception as e:
        return {"success": False, "session_id": session_id, "error": str(e)}


class TestSafeConcurrentTeams:
    """安全的并发队伍测试"""

    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Setup test environment before each test."""
        self.original_cwd = os.getcwd()
        os.chdir(Path(__file__).parent.parent.parent)
        yield
        os.chdir(self.original_cwd)

    @pytest.mark.asyncio
    async def test_teams_with_process_isolation(self):
        """使用进程隔离测试多个队伍"""

        # 获取团队配置
        team_registry = auto_register_teams()
        team_configs = team_registry.get_all_team_configs()

        if len(team_configs) < 2:
            pytest.skip("需要至少2个队伍配置进行并发测试")

        print(f"\n开始测试 {len(team_configs)} 个队伍的进程隔离并发执行...")

        db = await get_session_db()
        results = []

        try:
            # 使用进程池执行器
            with ProcessPoolExecutor(max_workers=min(len(team_configs), 4)) as executor:
                # 提交所有任务
                future_to_team = {}

                for i, (team_name, common_cfg) in enumerate(team_configs):
                    session_id = (
                        f"process-test-{uuid.uuid4().hex[:8]}-{team_name.replace(' ', '-')}"
                    )

                    # 创建会话
                    session = Session(
                        session_id=session_id,
                        create_time=datetime.now(),
                        status="pending",
                        session_run=common_cfg.model_copy(deep=True),
                        session_result=None,
                    )
                    await db.add_session(session)

                    print(f"提交队伍 '{team_name}' 到进程池 (session_id: {session_id})")

                    # 提交任务到进程池
                    future = executor.submit(
                        run_simulation_in_process, common_cfg.model_dump(), session_id, 1000
                    )
                    future_to_team[future] = (team_name, session_id)

                # 等待所有任务完成
                for future in as_completed(future_to_team):
                    team_name, session_id = future_to_team[future]
                    try:
                        result = future.result(timeout=60)  # 60秒超时

                        if result["success"]:
                            print(f"队伍 '{team_name}' 模拟成功")
                            results.append(
                                {"team_name": team_name, "session_id": session_id, "success": True}
                            )
                        else:
                            print(f"队伍 '{team_name}' 模拟失败: {result['error']}")
                            results.append(
                                {
                                    "team_name": team_name,
                                    "session_id": session_id,
                                    "success": False,
                                    "error": result["error"],
                                }
                            )

                    except Exception as e:
                        print(f"队伍 '{team_name}' 执行异常: {e}")
                        results.append(
                            {
                                "team_name": team_name,
                                "session_id": session_id,
                                "success": False,
                                "error": str(e),
                            }
                        )

        except Exception as e:
            print(f"进程池执行错误: {e}")
            raise
        finally:
            # 清理数据库
            for result in results:
                try:
                    await db.delete_session(result["session_id"])
                except Exception:
                    pass

        # 验证结果
        successful_teams = [r for r in results if r["success"]]
        failed_teams = [r for r in results if not r["success"]]

        print("\n=== 测试结果 ===")
        print(f"总队伍数: {len(team_configs)}")
        print(f"成功: {len(successful_teams)}")
        print(f"失败: {len(failed_teams)}")

        if failed_teams:
            print("\n失败的队伍:")
            for team in failed_teams:
                print(f"  - {team['team_name']}: {team.get('error', '未知错误')}")

        # 验证所有队伍都成功
        assert len(successful_teams) == len(team_configs), (
            f"期望所有 {len(team_configs)} 个队伍都成功，但只有 {len(successful_teams)} 个成功"
        )

        print(f"\n所有 {len(team_configs)} 个队伍在进程隔离环境下成功完成！")

    @pytest.mark.asyncio
    async def test_teams_sequential_with_delay(self):
        """测试顺序执行队伍，添加延迟确保资源清理"""

        team_registry = auto_register_teams()
        team_configs = team_registry.get_all_team_configs()

        results = []

        for i, (team_name, common_cfg) in enumerate(team_configs):
            print(f"\n执行队伍 {i + 1}/{len(team_configs)}: {team_name}")

            session_id = f"sequential-delay-{i}-{team_name.replace(' ', '-')}"

            try:
                # 使用进程隔离运行
                with ProcessPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(
                        run_simulation_in_process, common_cfg.model_dump(), session_id, 1000
                    )

                    result = future.result(timeout=60)

                    if result["success"]:
                        print(f"队伍 '{team_name}' 成功")
                        results.append(team_name)
                    else:
                        print(f"队伍 '{team_name}' 失败: {result['error']}")
                        pytest.fail(f"队伍 '{team_name}' 模拟失败")

            except Exception as e:
                print(f"队伍 '{team_name}' 执行异常: {e}")
                raise

            # 添加延迟确保资源清理
            await asyncio.sleep(1)

            # 强制垃圾回收
            gc.collect()

        print(f"\n成功顺序执行了 {len(results)} 个队伍")
        assert len(results) == len(team_configs)

    @pytest.mark.asyncio
    async def test_single_team_multiple_times(self):
        """多次运行同一个队伍，验证结果的一致性"""

        team_registry = auto_register_teams()
        team_configs = team_registry.get_all_team_configs()
        if not team_configs:
            pytest.skip("没有可用的团队配置")

        team_name, common_cfg = team_configs[0]

        print(f"\n多次测试队伍: {team_name}")

        results = []

        # 多次运行同一个队伍
        for i in range(3):
            print(f"第 {i + 1} 次运行")

            session_id = f"multiple-test-{i}-{team_name.replace(' ', '-')}"

            try:
                with ProcessPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(
                        run_simulation_in_process, common_cfg.model_dump(), session_id, 1000
                    )

                    result = future.result(timeout=60)

                    if result["success"]:
                        results.append(i + 1)
                        print(f"第 {i + 1} 次运行成功")
                    else:
                        print(f"第 {i + 1} 次运行失败: {result['error']}")
                        pytest.fail(f"第 {i + 1} 次运行失败")

            except Exception as e:
                print(f"第 {i + 1} 次运行异常: {e}")
                raise

            # 延迟
            await asyncio.sleep(0.5)

        print(f"\n队伍 '{team_name}' 的 {len(results)} 次运行都成功")
        assert len(results) == 3
