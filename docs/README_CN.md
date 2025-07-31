# ZZZ模拟器

[English](../README.md) | 中文

## 项目介绍

`ZZZ模拟器`是一款《绝区零》的伤害计算器。

本工具支持**全自动模拟**，无需手动设置技能释放序列（如需序列模式可以提issue）

您只需配置代理人装备，选择合适的APL（行动优先级列表），点击运行即可。

该工具提供友好的用户界面，可计算队伍整体伤害输出。基于预设的APL自动模拟队伍行动，触发buff，记录并分析结果，最终生成可视化图表报告。

## 功能特性

- 基于队伍配置计算总伤害
- 生成可视化图表
- 提供各角色详细伤害数据
- 编辑代理人装备
- 编写APL代码

## 安装指南

从发布页面下载最新打包源码或使用 `git clone`

### 安装UV（如未安装）

在任意终端中执行：
```bash
# 使用pip安装：
pip install uv
```

```bash
# macOS/Linux：
curl -LsSf https://astral.sh/uv/install.sh | sh
```

```bash
# Windows11 24H2及以上：
winget install --id=astral-sh.uv -e
```

```bash
# 旧版Windows：
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

或参考官方安装指南：[https://docs.astral.sh/uv/getting-started/installation/](https://docs.astral.sh/uv/getting-started/installation/)

### 安装并运行ZZZ模拟器

在项目目录中执行：

```bash
uv sync

uv run zsim run
```

## 开发

### 主要组件
1. **模拟引擎** - `zsim/simulator/` 中的核心逻辑处理战斗模拟
2. **Web API** - `zsim/api_src/` 中基于FastAPI的REST API，提供程序化访问
3. **Web UI** - `zsim/webui.py` 中基于Streamlit的界面以及 `electron-app/` 中的Vue.js + Electron桌面应用
4. **CLI** - 通过 `zsim/run.py` 的命令行接口
5. **数据库** - 基于SQLite的角色/敌人配置存储
6. **Electron应用** - 使用Vue.js和Electron构建的桌面应用，与FastAPI后端通信

### 设置和安装
```bash
# 首先安装UV包管理器
uv sync
# WebUI开发
uv run zsim run 
# FastAPI后端
uv run zsim api

# Electron应用开发，还需安装Node.js依赖
cd electron-app
corepack install
pnpm install
```

### 测试结构
- 单元测试位于 `tests/` 目录
- API测试位于 `tests/api/`
- 测试固件在 `tests/conftest.py` 中定义
- 使用pytest并支持asyncio

```bash
# 运行测试
uv run pytest
# 运行测试并生成覆盖率报告
uv run pytest -v --cov=zsim --cov-report=html
```

## 待办事项

详见[贡献指南](https://github.com/ZZZSimulator/ZSim/wiki/%E8%B4%A1%E7%8C%AE%E6%8C%87%E5%8D%97-Develop-Guide)获取最新开发计划。
