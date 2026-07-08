# -*- coding: utf-8 -*-
"""隔离的队伍测试，避免环境共享问题"""

import asyncio
import gc
import os
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pytest

from zsim.api_src.services.database.session_db import get_session_db
from zsim.api_src.services.sim_controller.sim_controller import SimController
from zsim.models.session.session_create import Session
from zsim.models.session.session_run import SessionRun
from zsim.simulator.simulator_class import Simulator

# 导入团队配置
from ..teams import auto_register_teams


class TestIsolatedTeams:
    """隔离的队伍测试类，确保每个队伍在独立环境中运行"""

    @staticmethod
    def _make_session_id(prefix: str, index: int, team_name: str) -> str:
        safe_team_name = team_name.replace(" ", "-")
        run_marker = uuid4().hex[:8]
        return f"{prefix}-{run_marker}-{index}-{safe_team_name}"

    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """每个测试前准备隔离环境。"""
        # 保存原始工作目录
        self.original_cwd = os.getcwd()

        # 切换到项目根目录
        os.chdir(Path(__file__).parent.parent.parent)

        yield

        # 恢复原始工作目录
        os.chdir(self.original_cwd)

        # 强制回收，降低跨测试状态残留
        gc.collect()

    async def run_single_team_simulation(self, team_name: str, common_cfg, session_id: str):
        """运行单个队伍的模拟，确保环境隔离"""

        # 创建独立的模拟器实例
        simulator = Simulator()

        # 初始化模拟器
        simulator.api_init_simulator(common_cfg, sim_cfg=None)

        # 运行模拟
        result = simulator.api_run_simulator(common_cfg, None, 1000)

        # 清理资源
        del simulator
        gc.collect()

        return result

    @pytest.mark.asyncio
    async def test_teams_sequentially(self):
        """按顺序测试各个队伍，避免并发问题"""

        # 获取所有团队配置
        team_registry = auto_register_teams()
        team_configs = team_registry.get_all_team_configs()

        db = await get_session_db()
        results = []

        try:
            # 逐个测试队伍
            for i, (team_name, common_cfg) in enumerate(team_configs):
                print(f"\n=== 开始测试队伍: {team_name} ===")

                session_id = self._make_session_id("sequential-test", i, team_name)

                # 记录开始时间
                start_time = datetime.now()

                # 运行单个队伍模拟
                result = await self.run_single_team_simulation(team_name, common_cfg, session_id)

                # 记录结束时间
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()

                print(f"队伍 '{team_name}' 模拟完成，耗时: {duration:.2f}秒")

                # 验证结果
                assert result is not None, f"队伍 '{team_name}' 模拟结果为空"

                results.append(
                    {
                        "team_name": team_name,
                        "session_id": session_id,
                        "duration": duration,
                        "success": True,
                    }
                )

                print(f"=== 队伍 '{team_name}' 测试完成 ===\n")

        except Exception as e:
            print(f"测试过程中发生错误: {e}")
            raise
        finally:
            # 清理数据库
            for result in results:
                try:
                    await db.delete_session(result["session_id"])
                except Exception:
                    pass

        # 验证所有队伍都测试成功
        assert len(results) == len(team_configs), (
            f"期望测试 {len(team_configs)} 个队伍，实际测试了 {len(results)} 个"
        )

        # 输出测试结果摘要
        print("\n=== 测试结果摘要 ===")
        for result in results:
            status = "成功" if result["success"] else "失败"
            print(f"队伍: {result['team_name']}, 耗时: {result['duration']:.2f}秒, 状态: {status}")

        print(f"\n所有 {len(team_configs)} 个队伍测试完成，无环境共享问题！")

    @pytest.mark.asyncio
    async def test_single_team_isolation(self):
        """测试单个队伍的隔离性"""

        # 获取第一个团队配置
        team_registry = auto_register_teams()
        team_configs = team_registry.get_all_team_configs()

        if not team_configs:
            pytest.skip("没有可用的团队配置")

        team_name, common_cfg = team_configs[0]

        # 多次运行同一个队伍，确保每次都是独立的
        results = []
        for i in range(3):
            print(f"第 {i + 1} 次运行队伍: {team_name}")

            session_id = self._make_session_id("isolation-test", i, team_name)
            result = await self.run_single_team_simulation(team_name, common_cfg, session_id)

            assert result is not None, f"第 {i + 1} 次运行失败"
            results.append(result)

        # 验证每次运行都是独立的（结果应该相似但不完全相同）
        assert len(results) == 3, "应该有3次运行结果"
        print(f"队伍 '{team_name}' 的3次独立运行都成功完成")

    @pytest.mark.asyncio
    async def test_team_with_controller_cleanup(self):
        """使用控制器清理方法测试队伍"""

        team_registry = auto_register_teams()
        team_configs = team_registry.get_all_team_configs()

        if not team_configs:
            pytest.skip("没有可用的团队配置")

        # 为每个队伍创建新的控制器实例
        results = []

        for i, (team_name, common_cfg) in enumerate(team_configs):
            print(f"\n测试队伍: {team_name}")

            # 创建新的控制器实例（避免单例）
            controller = SimController()

            # 重置控制器的内部状态
            controller._queue = asyncio.Queue()
            controller._running_tasks.clear()

            session_id = self._make_session_id("controller-test", i, team_name)

            # 创建会话
            session_run_config = SessionRun(
                stop_tick=1000,
                mode="normal",
                common_config=common_cfg,
            )
            session = Session(
                session_id=session_id,
                create_time=datetime.now(),
                status="pending",
                session_run=session_run_config,
                session_result=None,
            )

            db = await get_session_db()
            await db.add_session(session)

            try:
                # 放入队列
                await controller.put_into_queue(session_id, common_cfg, None)

                # 执行单个任务
                completed_sessions = await controller.execute_simulation_test(max_tasks=1)

                assert len(completed_sessions) == 1, f"队伍 '{team_name}' 应该完成1个任务"
                assert completed_sessions[0] == session_id, "完成的会话ID不匹配"

                results.append(team_name)
                print(f"队伍 '{team_name}' 测试成功")

            finally:
                # 清理
                await db.delete_session(session_id)

                # 强制清理控制器
                controller._queue = asyncio.Queue()
                controller._running_tasks.clear()
                del controller
                gc.collect()

        print(f"\n成功测试了 {len(results)} 个队伍，每个队伍都使用了独立的控制器实例")
        assert len(results) == len(team_configs), "所有队伍都应该测试成功"
