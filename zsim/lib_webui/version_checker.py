import json
import re
import webbrowser
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import streamlit as st

from zsim.define import GITHUB_REPO_NAME, GITHUB_REPO_OWNER, __version__


class GitHubVersionChecker:
    """GitHub版本检查器"""

    def __init__(self, repo_owner: str, repo_name: str, current_version: str):
        """
        初始化版本检查器

        Args:
            repo_owner: GitHub仓库所有者
            repo_name: GitHub仓库名称
            current_version: 当前版本号
        """
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.current_version = current_version
        self.api_url = (
            f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"
        )
        self.repo_url = f"https://github.com/{repo_owner}/{repo_name}"

    def _parse_version(self, version: str) -> tuple[list, str, int]:
        """
        解析版本号，支持预发布版本

        Args:
            version: 版本号字符串，如 "1.2.3a1" 或 "1.2.3"

        Returns:
            tuple: (主版本号列表, 预发布类型, 预发布版本号)
                  例如: ([1, 2, 3], "a", 1) 或 ([1, 2, 3], "", 0)
        """
        # 移除版本号前的 'v' 前缀
        clean_version = version.lstrip("v")

        # 使用正则表达式匹配版本号格式
        # 匹配格式: 数字.数字.数字[预发布标识符数字]
        pattern = r"^(\d+(?:\.\d+)*?)([a-zA-Z]+)?(\d+)?$"
        match = re.match(pattern, clean_version)

        if not match:
            # 如果不匹配，尝试简单的数字版本
            try:
                main_parts = [int(x) for x in clean_version.split(".")]
                return main_parts, "", 0
            except ValueError:
                # 如果解析失败，返回默认值
                return [0], "", 0

        main_version = match.group(1)
        prerelease_type = match.group(2) or ""
        prerelease_num = int(match.group(3)) if match.group(3) else 0

        # 解析主版本号
        try:
            main_parts = [int(x) for x in main_version.split(".")]
        except ValueError:
            main_parts = [0]

        return main_parts, prerelease_type, prerelease_num

    def _compare_versions(self, version1: str, version2: str) -> int:
        """
        比较两个版本号，支持预发布版本

        Args:
            version1: 版本号1
            version2: 版本号2

        Returns:
            -1: version1 < version2
             0: version1 == version2
             1: version1 > version2
        """
        # 解析版本号
        v1_main, v1_pre_type, v1_pre_num = self._parse_version(version1)
        v2_main, v2_pre_type, v2_pre_num = self._parse_version(version2)

        # 补齐主版本号长度
        max_len = max(len(v1_main), len(v2_main))
        v1_main.extend([0] * (max_len - len(v1_main)))
        v2_main.extend([0] * (max_len - len(v2_main)))

        # 首先比较主版本号
        for i in range(max_len):
            if v1_main[i] < v2_main[i]:
                return -1
            elif v1_main[i] > v2_main[i]:
                return 1

        # 主版本号相同，比较预发布版本
        # 预发布版本的优先级：无预发布 > rc > b > a
        prerelease_priority = {"": 4, "rc": 3, "b": 2, "a": 1}

        v1_priority = prerelease_priority.get(v1_pre_type.lower(), 0)
        v2_priority = prerelease_priority.get(v2_pre_type.lower(), 0)

        if v1_priority != v2_priority:
            return -1 if v1_priority < v2_priority else 1

        # 预发布类型相同，比较预发布版本号
        if v1_pre_type and v2_pre_type:  # 都是预发布版本
            if v1_pre_num < v2_pre_num:
                return -1
            elif v1_pre_num > v2_pre_num:
                return 1

        return 0

    def check_for_updates(self, timeout: int = 10) -> dict[str, Any] | None:
        """
        检查是否有新版本

        Args:
            timeout: 请求超时时间（秒）

        Returns:
            如果有新版本，返回包含版本信息的字典；否则返回None
        """
        try:
            # 创建请求
            request = Request(
                self.api_url,
                headers={
                    "User-Agent": "ZZZ-Simulator-Version-Checker",
                    "Accept": "application/vnd.github.v3+json",
                },
            )

            # 发送请求
            with urlopen(request, timeout=timeout) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))

                    latest_version = data.get("tag_name", "")
                    if not latest_version:
                        return None

                    # 比较版本
                    if self._compare_versions(self.current_version, latest_version) < 0:
                        return {
                            "latest_version": latest_version,
                            "current_version": self.current_version,
                            "release_url": data.get("html_url", self.repo_url),
                            "release_name": data.get("name", latest_version),
                            "release_body": data.get("body", ""),
                            "published_at": data.get("published_at", ""),
                            "download_url": data.get("zipball_url", ""),
                        }

                    return None
                else:
                    print(f"GitHub API请求失败，状态码: {response.status}")
                    return None

        except (URLError, HTTPError, json.JSONDecodeError, ValueError) as e:
            print(f"检查更新时发生错误: {e}")
            return None

    @st.dialog("发现新版本")
    def show_update_dialog(self, update_info: dict[str, Any]) -> None:
        """
        显示更新对话框

        Args:
            update_info: 更新信息字典
        """
        # 使用容器来确保对话框显示在顶部
        with st.container():
            st.success(f"🎉 发现新版本: {update_info['latest_version']}")

            with st.expander("📋 查看更新详情", expanded=False):
                col_info1, col_info2 = st.columns(2)

                with col_info1:
                    st.markdown(f"**当前版本:** `v{update_info['current_version']}`")
                    if update_info.get("published_at"):
                        st.markdown(f"**发布时间:** {update_info['published_at'][:10]}")

                with col_info2:
                    st.markdown(f"**最新版本:** `{update_info['latest_version']}`")
                    if update_info.get("release_name"):
                        st.markdown(f"**发布标题:** {update_info['release_name']}")

                if update_info.get("release_body"):
                    st.markdown("**更新说明:**")
                    # 限制更新说明的长度，避免界面过长
                    release_body = update_info["release_body"]
                    if len(release_body) > 500:
                        release_body = release_body[:500] + "..."
                    st.markdown(release_body)

            # 按钮布局
            col1, col2 = st.columns(2)

            with col1:
                if st.button(
                    "🔗 前往发布页",
                    type="primary",
                    use_container_width=True,
                    key="download_btn",
                ):
                    webbrowser.open(update_info["release_url"])
                    st.success("已在浏览器中打开下载页面")
                    st.session_state.update_dismissed = True

            with col2:
                if st.button(
                    "❌ 暂不更新", use_container_width=True, key="dismiss_btn"
                ):
                    st.session_state.update_dismissed = True
                    st.rerun()


def check_github_updates() -> None:
    """
    检查GitHub更新的主函数

    从pyproject.toml读取当前版本，检查GitHub仓库是否有新版本
    """
    # 避免重复检查
    if st.session_state.get("update_checked", False) or st.session_state.get(
        "update_dismissed", False
    ):
        return

    try:
        current_version = __version__

        # 创建版本检查器
        checker = GitHubVersionChecker(
            repo_owner=GITHUB_REPO_OWNER,
            repo_name=GITHUB_REPO_NAME,
            current_version=current_version,
        )

        # 检查更新
        update_info = checker.check_for_updates()

        if update_info:
            checker.show_update_dialog(update_info)

        # 标记已检查
        st.session_state.update_checked = True

    except Exception as e:
        print(f"检查更新时发生错误: {e}")
        st.session_state.update_checked = True
