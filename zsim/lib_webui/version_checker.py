import json
import webbrowser
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import streamlit as st
from define import GITHUB_REPO_NAME, GITHUB_REPO_OWNER, __version__


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

    def _compare_versions(self, version1: str, version2: str) -> int:
        """
        比较两个版本号

        Args:
            version1: 版本号1
            version2: 版本号2

        Returns:
            -1: version1 < version2
             0: version1 == version2
             1: version1 > version2
        """
        # 移除版本号前的 'v' 前缀
        v1 = version1.lstrip("v")
        v2 = version2.lstrip("v")

        # 分割版本号
        v1_parts = [int(x) for x in v1.split(".")]
        v2_parts = [int(x) for x in v2.split(".")]

        # 补齐长度
        max_len = max(len(v1_parts), len(v2_parts))
        v1_parts.extend([0] * (max_len - len(v1_parts)))
        v2_parts.extend([0] * (max_len - len(v2_parts)))

        # 比较
        for i in range(max_len):
            if v1_parts[i] < v2_parts[i]:
                return -1
            elif v1_parts[i] > v2_parts[i]:
                return 1

        return 0

    def check_for_updates(self, timeout: int = 10) -> Optional[Dict[str, Any]]:
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
    def show_update_dialog(self, update_info: Dict[str, Any]) -> None:
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
