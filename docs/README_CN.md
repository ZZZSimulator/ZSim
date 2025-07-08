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

```bash
# 使用pip安装：
pip install uv
```

或参考官方安装指南：[https://docs.astral.sh/uv/getting-started/installation/](https://docs.astral.sh/uv/getting-started/installation/)

### 安装ZZZ模拟器

在项目目录中执行：

```bash
uv venv
uv pip install .  # 这里有个 '.' 代表相对路径
```

## 运行说明

在任意终端中执行：

```bash
zsim run
```

若你不想安装此工具，可直接运行：

```bash
uv run ./zsim/run.py run
```

```bash
# 或使用：
uv run zsim run
```

## 待办事项

详见[贡献指南](https://github.com/ZZZSimulator/ZSim/wiki/%E8%B4%A1%E7%8C%AE%E6%8C%87%E5%8D%97-Develop-Guide)获取最新开发计划。
