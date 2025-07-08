import copy
import os
import time
from typing import Any, Sequence

import pandas as pd
import streamlit as st
import toml
from streamlit_ace import st_ace

from zsim.define import (
    CHARACTER_DATA_PATH,
    COSTOM_APL_DIR,
    DEFAULT_APL_DIR,
    saved_char_config,
)

from .constants import CHAR_CID_MAPPING


class APLArchive:
    default_apl_map: dict[str, dict]
    custom_apl_map: dict[str, dict]
    options: Sequence[str]
    title_apl_map: dict[str, dict]
    title_file_name_map: dict[str, str]

    def __init__(self):
        self.refresh()

    def refresh(self):
        self.default_apl_map = self.__get_apl_toml(DEFAULT_APL_DIR)
        self.custom_apl_map = self.__get_apl_toml(COSTOM_APL_DIR)
        all_apl_list: list[dict] = list(self.default_apl_map.values()) + list(
            self.custom_apl_map.values()
        )
        all_apl_map: dict[str, dict] = self.default_apl_map | self.custom_apl_map
        self.title_apl_map = {
            apl.get("general", {}).get("title", None): apl for apl in all_apl_list
        }
        self.title_file_name_map = {
            apl.get("general", {}).get("title", None): relative_path
            for relative_path, apl in all_apl_map.items()
        }
        self.options = [
            title for title in self.title_apl_map.keys() if title is not None
        ]

    def save_apl_data(self, title: str, edited_data: dict[str, Any]):
        """保存编辑后的APL数据到对应的TOML文件。

        Args:
            title (str): 要保存的APL的标题。
            edited_data (dict[str, Any]): 包含编辑后APL信息的字典。

        Raises:
            ValueError: 如果找不到标题对应的文件路径或保存失败。
        """
        if self.title_file_name_map is not None:
            relative_path = self.title_file_name_map.get(title)
        if not relative_path:
            raise ValueError(f"错误：找不到标题 '{title}' 对应的文件路径。")

        # 确定绝对路径
        if relative_path in self.default_apl_map:
            base_dir = DEFAULT_APL_DIR
        elif relative_path in self.custom_apl_map:
            base_dir = COSTOM_APL_DIR
        else:
            raise ValueError(f"内部错误：无法确定文件 '{relative_path}' 的所属目录。")

        absolute_path = os.path.abspath(os.path.join(base_dir, relative_path))

        try:
            # 深拷贝以避免修改传入的字典
            data_to_save = copy.deepcopy(edited_data)

            # 注意：角色列表现在直接由 multiselect 提供，无需解析字符串
            # if 'characters' in data_to_save:
            #     chars_info = data_to_save['characters']
            #     # 移除旧的字符串解析逻辑
            #     chars_info.pop('required_str_temp', None)
            #     chars_info.pop('optional_str_temp', None)

            # 更新最后修改时间
            if "general" in data_to_save:
                from datetime import datetime

                now_str = (
                    datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "+08:00"
                )
                data_to_save["general"]["latest_change_time"] = now_str
            else:
                # 如果没有 general 部分，也尝试添加时间戳
                from datetime import datetime

                now_str = (
                    datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "+08:00"
                )
                data_to_save["general"] = {"latest_change_time": now_str}

            # 保存到文件
            with open(absolute_path, "w", encoding="utf-8") as f:
                toml.dump(data_to_save, f)

            # 刷新内部缓存
            self.refresh()

        except FileNotFoundError:
            raise ValueError(f"错误：找不到文件 '{absolute_path}'。")
        except Exception as e:
            raise ValueError(f"保存APL文件时出错：{e}")

    def get_general(self, title: str):
        """获取指定标题的APL的一般信息。"""
        assert self.title_apl_map is not None
        return self.title_apl_map.get(title, {}).get("general", {})

    def get_apl_data(self, title: str) -> dict[str, Any] | None:
        """获取指定标题的完整APL数据"""
        assert self.title_apl_map is not None
        return self.title_apl_map.get(title)

    def get_title_from_path(self, path: str) -> str | None:
        """根据路径获取对应的标题"""
        assert self.title_file_name_map is not None
        for title, apl_path in self.title_file_name_map.items():
            if apl_path in path:
                return title
        return None

    def get_origin_relative_path(self, title: str) -> str | None:
        """根据标题获取其在项目中的相对文件路径。

        Args:
            title (str): APL的标题。

        Returns:
            str | None: APL文件相对于项目根目录的相对路径，如果找不到则返回 None。
        """
        # 从 title_file_name_map 获取相对于 APL 基础目录的路径
        relative_path_in_apl_dir = self.title_file_name_map.get(title)
        if relative_path_in_apl_dir is None:
            # st.error(f"错误：找不到标题 '{title}' 对应的文件路径。")
            return None

        # 确定文件属于哪个基础目录 (default 或 custom)
        assert self.default_apl_map is not None and self.custom_apl_map is not None, (
            "APL映射未初始化。请先调用 refresh() 方法。"
        )
        if relative_path_in_apl_dir in self.default_apl_map:
            base_dir_relative_to_project = DEFAULT_APL_DIR
        elif relative_path_in_apl_dir in self.custom_apl_map:
            base_dir_relative_to_project = COSTOM_APL_DIR
        else:
            # st.error(f"内部错误：无法确定文件 '{relative_path_in_apl_dir}' 的所属目录。")
            return None  # 或者可以抛出异常

        # 组合基础目录的项目相对路径和文件在基础目录内的相对路径
        # 使用 os.path.join 来正确处理路径分隔符
        # 替换反斜杠为正斜杠以保持一致性
        full_relative_path = os.path.join(
            base_dir_relative_to_project, relative_path_in_apl_dir
        ).replace("\\", "/")

        return full_relative_path

    def change_title(
        self, former_title: str, new_title: str, new_comment: str | None = None
    ):
        # Step 1: Check if the former title exists

        if former_title not in self.title_apl_map.keys():
            st.error(f"错误：原标题 '{former_title}' 不存在。")
            return

        # Step 2: Check if the new title already exists (and is not the same as the former title)

        if new_title != former_title and new_title in self.title_apl_map.keys():
            st.error(f"错误：新标题 '{new_title}' 已被其他APL使用。")
            return

        # Step 3: Check if the new title is the same as the former title

        if new_title == former_title and new_comment == self.title_apl_map.get(
            former_title, {}
        ).get("general", {}).get("comment", None):
            st.warning("新旧标题相同，且未提供新注释，无需更改。")
            return

        # Step 4: Get the relative path for the former title
        relative_path = self.title_file_name_map.get(former_title)
        if not relative_path:
            st.error(
                f"内部错误：找不到标题 '{former_title}' 对应的文件路径。"
            )  # Should not happen if step 1 passed
            return

        # Determine the absolute path
        assert self.default_apl_map is not None and self.custom_apl_map is not None, (
            "APL映射未初始化。请先调用 refresh() 方法。"
        )
        if relative_path in self.default_apl_map:
            base_dir = DEFAULT_APL_DIR
        elif relative_path in self.custom_apl_map:
            base_dir = COSTOM_APL_DIR
        else:
            st.error(
                f"内部错误：无法确定文件 '{relative_path}' 的所属目录。"
            )  # Should not happen
            return

        absolute_path = os.path.abspath(os.path.join(base_dir, relative_path))

        # Step 5 & 6: Update the title and comment in the TOML file and save
        try:
            with open(absolute_path, "r", encoding="utf-8") as f:
                apl_data = toml.load(f)

            if "general" not in apl_data:
                apl_data["general"] = {}

            apl_data["general"]["title"] = new_title
            if new_comment is not None:
                apl_data["general"]["comment"] = new_comment

            with open(absolute_path, "w", encoding="utf-8") as f:
                toml.dump(apl_data, f)

            st.success("正在保存...")
            time.sleep(1)

            # Step 7: Refresh the APL archive
            self.refresh()

        except FileNotFoundError:
            st.error(f"错误：找不到文件 '{absolute_path}'。")
        except Exception as e:
            st.error(f"保存APL文件时出错：{e}")

    def __get_apl_toml(self, apl_path: str) -> dict[str, dict]:
        """根据APL地址获取APL toml的内容
        :param apl_path: APL文件或目录路径
        :return: {relative_path: toml_content} 字典，如果路径无效则返回空字典
        """
        toml_dict_map = {}
        # 将输入路径转换为绝对路径
        base_path = os.path.abspath(apl_path)
        try:
            if os.path.isfile(base_path):
                # 如果是文件，直接处理
                if base_path.endswith(".toml"):
                    try:
                        with open(base_path, "r", encoding="utf-8") as f:
                            toml_dict: dict = toml.load(f)
                            if toml_dict.get("apl_logic", {}).get("logic") is not None:
                                relative_path = os.path.basename(base_path)
                                toml_dict_map[relative_path] = toml_dict
                    except Exception as e:
                        st.exception(
                            Exception(f"Error loading TOML file {base_path}: {e}")
                        )
            elif os.path.isdir(base_path):
                # 如果是目录，遍历所有toml文件
                for root, _, files in os.walk(base_path):
                    for file in files:
                        if file.endswith(".toml"):
                            file_path = os.path.join(root, file)
                            try:
                                with open(file_path, "r", encoding="utf-8") as f:
                                    toml_dict: dict = toml.load(f)
                                    if (
                                        toml_dict.get("apl_logic", {}).get("logic")
                                        is not None
                                    ):
                                        relative_path = os.path.relpath(
                                            file_path, base_path
                                        )
                                        toml_dict_map[relative_path] = toml_dict
                            except Exception as e:
                                st.exception(
                                    Exception(
                                        f"Error loading TOML file {file_path}: {e}"
                                    )
                                )
            else:
                # 如果路径既不是文件也不是目录，则记录警告或错误
                st.warning(
                    f"APL path does not exist or is not a file/directory: {apl_path}"
                )
            return toml_dict_map
        except Exception as e:
            raise ValueError(f"读取APL文件失败：{str(e)}")


class APLJudgeTool:
    def __init__(self, raw_apl: dict) -> None:
        self.raw_apl: dict = raw_apl
        self.characters: dict = raw_apl.get("characters", {})
        self.required_chars: list[str] = [
            self._convert_to_name(char) for char in self.characters.get("required", [])
        ]
        self.optional_chars: list[str] = [
            self._convert_to_name(char) for char in self.characters.get("optional", [])
        ]
        self.char_configs: dict[str, dict] = {
            self._convert_to_name(k): v
            for k, v in self.characters.items()
            if k not in ["required", "optional"]
        }  # {name: {config}}
        self.apl_logic: str = raw_apl.get("apl_logic", {}).get("logic", "")

        self.saved_char_config: dict = saved_char_config

    def _convert_to_name(self, char_identifier: str | int) -> str:
        """将任何角色标识（名称或CID）统一转换为角色名称"""
        # 如果输入的是CID，通过反向查找获取名称
        for name, cid in CHAR_CID_MAPPING.items():
            if cid == char_identifier:
                return name
        # 如果输入的是名称或未知标识，直接返回
        return str(char_identifier)

    def judge_requried_chars(self) -> tuple[bool, list[str]]:
        """判断是否满足所有必须角色"""
        missing_chars = []
        for char in self.required_chars:
            if char not in self.saved_char_config.get("name_box", []):
                missing_chars.append(char)
        return len(missing_chars) == 0, missing_chars

    def judge_optional_chars(self) -> tuple[bool, list[str]]:
        """判断是否满足所有可选角色"""
        missing_chars = []
        for char in self.optional_chars:
            if char not in self.saved_char_config.get("name_box", []):
                missing_chars.append(char)
        return len(missing_chars) == 0, missing_chars

    def judge_char_config(self) -> tuple[bool, dict[str, str | int]]:
        """判断是否满足所有角色配置"""
        missing_configs = {}
        char_name: str  # 角色名称
        config: dict  # 角色配置字典
        key: str  # 配置项名称
        value: str | int  # 配置项值
        saved_value: str | int | list[str | int]  # 保存的配置项值
        for char_name, config in self.char_configs.items():
            for key, value in config.items():
                saved_value = self.saved_char_config.get(char_name, {}).get(key)
                target_value = str(value)
                pass_through_values = ["", "None", "-1", "[]"]
                # 如果目标值在pass_through中，直接跳过后续判断
                if target_value in pass_through_values:
                    continue
                # 判断saved_value是否为列表
                if isinstance(saved_value, list):
                    # 如果是列表，检查保存值是否在列表中
                    if any(v in target_value for v in [str(v) for v in saved_value]):
                        missing_configs[char_name] = missing_configs.get(char_name, {})
                        missing_configs[char_name][key] = value
                else:
                    # 如果不是列表，按相等判断
                    if str(saved_value) not in target_value:
                        missing_configs[char_name] = missing_configs.get(char_name, {})
                        missing_configs[char_name][key] = value

        return len(missing_configs) == 0, missing_configs


def display_apl_details(
    apl_data: dict[str, Any], apl_title: str, apl_archive: APLArchive
):  # <-- 添加 apl_archive 参数
    """使用Streamlit组件显示和编辑APL的详细信息。

    Args:
        apl_data (dict[str, Any]): 包含APL信息的字典。
        apl_title (str): 当前编辑的APL标题，用于session_state键。
    """
    if not apl_data:
        st.warning("未找到选定的APL数据。")
        return

    st.divider()
    st.subheader(f"编辑 APL：{apl_title}")  # Use title in subheader

    # Initialize session state for edited data if not present
    session_key = f"edited_apl_{apl_title}"
    if session_key not in st.session_state:
        # Deep copy to avoid modifying the original dict directly
        st.session_state[session_key] = copy.deepcopy(apl_data)

    edited_data: dict = st.session_state[session_key]

    # --- General 信息编辑 ---
    general_info = edited_data.get("general", {})
    cols_general = st.columns(2)
    # Title editing might need special handling due to its use as an identifier
    # For now, make it read-only or handle rename separately as per roadmap
    cols_general[0].markdown(
        f"**标题:**  (重命名请使用上方按钮)</br>**{general_info.get('title', 'N/A')}**  ",
        unsafe_allow_html=True,
    )
    general_info["author"] = cols_general[1].text_input(
        "作者", value=general_info.get("author", "")
    )
    # Display create/change times - typically read-only
    general_info["comment"] = st.text_area(
        "注释", value=general_info.get("comment", "")
    )
    edited_data["general"] = general_info  # Update the edited data

    # --- Characters 信息编辑 (Basic Framework) ---
    st.markdown("**角色信息**")
    characters_info: dict = edited_data.setdefault(
        "characters", {}
    )  # 使用 setdefault 确保存在

    # --- 读取角色列表 ---
    try:
        if os.path.exists(CHARACTER_DATA_PATH):
            df_char = pd.read_csv(CHARACTER_DATA_PATH)
            all_character_names = df_char["name"].unique().tolist()
        else:
            st.error(f"角色数据文件未找到: {CHARACTER_DATA_PATH}")
            all_character_names = []  # 提供空列表以避免后续错误
    except Exception as e:
        st.error(f"读取角色数据时出错: {e}")
        all_character_names = []

    # --- 使用多选框编辑必须/可选角色 ---
    required_list = characters_info.get("required", [])
    optional_list = characters_info.get("optional", [])

    # 过滤掉不在可选列表中的已选角色（可能来自旧数据或手动修改）
    valid_required = [char for char in required_list if char in all_character_names]
    valid_optional = [char for char in optional_list if char in all_character_names]

    # 初始化 session_state
    if f"{session_key}_required_chars" not in st.session_state:
        st.session_state[f"{session_key}_required_chars"] = valid_required
    if f"{session_key}_optional_chars" not in st.session_state:
        st.session_state[f"{session_key}_optional_chars"] = valid_optional

    col1, col2 = st.columns(2)
    with col1:
        # 更新 characters_info 中的列表为过滤后的有效列表
        st.multiselect(
            "必须角色",
            options=all_character_names,
            key=f"{session_key}_required_chars",  # 添加唯一 key
            max_selections=3,
        )
        # 用 session_state 结果同步到 characters_info
        characters_info["required"] = st.session_state[f"{session_key}_required_chars"]
    with col2:
        st.multiselect(
            "可选角色",
            options=all_character_names,
            key=f"{session_key}_optional_chars",
        )
        characters_info["optional"] = st.session_state[f"{session_key}_optional_chars"]

    # 清理掉不在 selected_chars 中的角色配置
    # 需要在这里重新获取最新的 selected_chars 列表
    _selected_chars_for_cleanup = characters_info.get(
        "required", []
    ) + characters_info.get("optional", [])
    _current_config_keys = list(characters_info.keys())
    for _key in _current_config_keys:
        if _key not in _selected_chars_for_cleanup and _key not in [
            "required",
            "optional",
        ]:
            # 确保 key 存在再删除，避免潜在错误
            if _key in characters_info:
                del characters_info[_key]

    # --- 编辑角色配置 ---
    st.markdown("**角色配置编辑**")
    selected_chars = characters_info.get("required", []) + characters_info.get(
        "optional", []
    )

    if not selected_chars:
        st.markdown("- 请先在上方选择“必须角色”或“可选角色”。")
    else:
        # 确保 characters_info 中存在所有选定角色的条目
        cols = st.columns(len(selected_chars))
        i = 0
        for char_name in selected_chars:
            if char_name not in characters_info:
                characters_info[char_name] = {}  # 如果不存在则初始化为空字典

        # 为每个选定的角色显示编辑界面
        for char_name in selected_chars:
            with cols[i]:
                i += 1
                if char_name not in all_character_names:  # 跳过无效的角色名
                    continue

                # 获取或初始化该角色的配置
                char_config = characters_info.setdefault(char_name, {})

                with st.expander(f"编辑角色配置需求: {char_name}", expanded=False):
                    # cinema 编辑 (使用多选框)
                    cinema_options = list(range(7))  # 选项为 0 到 6
                    current_cinema_val = char_config.get("cinema", [])

                    # 确保 current_cinema_val 是列表，并且元素是整数
                    if isinstance(current_cinema_val, int):
                        default_cinema = (
                            [current_cinema_val]
                            if current_cinema_val in cinema_options
                            else []
                        )
                    elif isinstance(current_cinema_val, list):
                        # 过滤掉无效值或非整数值
                        default_cinema = [
                            int(v)
                            for v in current_cinema_val
                            if isinstance(v, (int, str))
                            and str(v).isdigit()
                            and int(v) in cinema_options
                        ]
                    elif (
                        isinstance(current_cinema_val, str)
                        and current_cinema_val.isdigit()
                    ):
                        default_cinema = (
                            [int(current_cinema_val)]
                            if int(current_cinema_val) in cinema_options
                            else []
                        )
                    else:
                        default_cinema = []  # 如果是其他类型或空字符串，默认为空列表

                    # 使用 st.multiselect 控件
                    selected_cinema = st.multiselect(
                        "影画等级 (可多选)",
                        options=cinema_options,
                        default=default_cinema,
                        key=f"{session_key}_{char_name}_cinema",
                    )

                    # 直接将选择的列表（整数）保存到 char_config
                    # 如果用户没有选择任何项，则保存空列表
                    char_config["cinema"] = selected_cinema

                    # weapon 编辑
                    char_config["weapon"] = st.text_input(
                        "音擎",
                        value=str(char_config.get("weapon", "")),
                        key=f"{session_key}_{char_name}_weapon",
                    )
                    # equip_set4 编辑
                    char_config["equip_set4"] = st.text_input(
                        "四件套",
                        value=str(char_config.get("equip_set4", "")),
                        key=f"{session_key}_{char_name}_equip_set4",
                    )

    # 更新 session state 中的 characters 数据
    edited_data["characters"] = characters_info

    # --- APL Logic 编辑 ---
    st.markdown("**APL 逻辑**")

    st.page_link("lib_webui/doc_pages/page_apl_doc.py", icon="📖", label="APL设计书")

    apl_logic_info = edited_data.get("apl_logic", {})
    st.write("逻辑编写：")
    # 使用 st_ace 替换 st.text_area 以获得更好的代码编辑体验
    apl_logic_info["logic"] = st_ace(
        value=apl_logic_info.get("logic", ""),
        language="python",
        theme="github",  # 选择一个主题
        keybinding="vscode",  # 可选：设置键位绑定
        height=800,  # 设置编辑器高度
        auto_update=True,  # 自动更新内容
        key=f"{session_key}_apl_logic_editor",  # 添加唯一 key
    )
    edited_data["apl_logic"] = apl_logic_info  # Update the edited data

    # --- 在保存按钮前添加警告 ---
    relative_path = apl_archive.title_file_name_map.get(apl_title)
    if relative_path and relative_path in apl_archive.default_apl_map:
        st.warning(
            "警告：正在修改非自建APL，这可能会在更新时被覆盖。请考虑复制后修改。",
            icon="⚠️",
        )

    # --- 保存按钮 ---
    st.divider()
    if st.button("保存对 APL 的修改"):
        st.session_state[session_key] = edited_data
        try:
            # 调用保存方法 (edited_data 中的 characters 已包含正确的列表)
            apl_archive.save_apl_data(apl_title, edited_data)
            st.success(f"APL '{apl_title}' 已成功保存！")
            # 清理 session state 并刷新页面
            del st.session_state[session_key]
            time.sleep(1)  # 短暂显示成功消息
            st.rerun()
        except ValueError as e:
            st.error(f"保存失败：{e}")
        except Exception as e:
            st.error(f"保存过程中发生意外错误：{e}")


def go_apl_editor():
    apl_archive = APLArchive()
    st.write("选择一个APL")
    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
    with col1:
        selected_title = st.selectbox(
            "APL选项",
            apl_archive.options,
            key="selected_apl_title",
            label_visibility="collapsed",
        )
    with col2:

        @st.dialog("APL详情")
        def show_apl_detail():
            general = apl_archive.get_general(selected_title)
            st.markdown(
                f"""
                <div style='background-color: var(--secondary-background-color); padding: 20px; border-radius: 10px;
                     border: 1px solid var(--primary-color);'>
                    <h3 style='color: var(--primary-color); margin-bottom: 15px;'>{general.get("title", "无标题")}</h3>
                    <div style='margin-left: 10px;'>
                        <h4 style='color: var(--text-color); margin: 10px 0;'>👤 作者：{general.get("author", "佚名")}</h4>
                        <h4 style='color: var(--text-color); margin: 10px 0;'>📅 创建时间：{general.get("create_time", "无")}</h4>
                        <h4 style='color: var(--text-color); margin: 10px 0;'>🔄 上次修改：{general.get("latest_change_time", "无")}</h4>
                    </div>
                </div>
            """,
                unsafe_allow_html=True,
            )
            st.write("")
            if st.button("确定", use_container_width=True):
                st.rerun()

        if st.button("更多", use_container_width=True):
            show_apl_detail()
    with col3:

        @st.dialog("APL重命名")
        def rename_apl():
            relative_path = apl_archive.title_file_name_map.get(selected_title)
            if relative_path in apl_archive.default_apl_map:
                st.warning("警告：正在修改非自建APL，你需要知道自己在做什么", icon="⚠️")
            new_title = st.text_input("新标题", value=selected_title)
            new_comment = st.text_input(
                "新注释",
                value=apl_archive.get_general(selected_title).get("comment", ""),
            )
            if st.button("确定", use_container_width=True):
                apl_archive.change_title(selected_title, new_title, new_comment)
                # 刷新 APL 列表并切换到新的标题
                apl_archive.refresh()
                st.session_state["selected_apl_title"] = new_title
                st.rerun()

        if st.button("重命名", use_container_width=True):
            rename_apl()
    with col4:
        # 新建 APL 对话框
        @st.dialog("新建APL")
        def create_new_apl():
            st.write("基于模板创建新的APL")
            # 读取模板文件内容
            template_path = os.path.abspath(
                os.path.join(DEFAULT_APL_DIR, "APL template.toml")
            )
            try:
                with open(template_path, "r", encoding="utf-8") as f:
                    template_data = toml.load(f)
            except FileNotFoundError:
                st.error(f"错误：找不到模板文件 '{template_path}'")
                return
            except Exception as e:
                st.error(f"读取模板文件时出错：{e}")
                return

            new_title = st.text_input("新标题", placeholder="请输入新APL的标题")
            new_author = st.text_input("作者 (可选)", placeholder="请输入作者名称")
            new_comment = st.text_input("注释 (可选)", placeholder="请输入注释信息")

            if st.button("创建", use_container_width=True):
                if not new_title:
                    st.warning("请输入新标题。")
                    return
                if new_title in apl_archive.title_apl_map:
                    st.error(f"错误：标题 '{new_title}' 已存在。")
                    return

                # 准备新的 APL 数据
                new_apl_data = template_data.copy()
                if "general" not in new_apl_data:
                    new_apl_data["general"] = {}

                from datetime import datetime

                now_str = (
                    datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "+08:00"
                )

                new_apl_data["general"]["title"] = new_title
                if new_author:
                    new_apl_data["general"]["author"] = new_author
                else:
                    # 如果用户未输入作者，可以保留模板中的或设为默认值
                    new_apl_data["general"]["author"] = template_data.get(
                        "general", {}
                    ).get("author", "未知作者")
                if new_comment:
                    new_apl_data["general"]["comment"] = new_comment
                else:
                    new_apl_data["general"]["comment"] = template_data.get(
                        "general", {}
                    ).get("comment", "")
                new_apl_data["general"]["create_time"] = now_str
                new_apl_data["general"]["latest_change_time"] = now_str

                # 生成文件名 (简单处理，替换空格和特殊字符)
                safe_filename = "".join(
                    c for c in new_title if c.isalnum() or c in "-_ "
                ).rstrip()
                safe_filename = safe_filename.replace(" ", "_") + ".toml"
                new_file_path = os.path.join(COSTOM_APL_DIR, safe_filename)

                try:
                    # 确保目录存在
                    os.makedirs(COSTOM_APL_DIR, exist_ok=True)
                    # 保存新文件
                    with open(new_file_path, "w", encoding="utf-8") as f:
                        toml.dump(new_apl_data, f)

                    st.success(
                        f"APL '{new_title}' 已成功创建并保存至 '{safe_filename}'"
                    )
                    time.sleep(1)
                    # 刷新 APL 列表
                    apl_archive.refresh()
                    st.session_state["selected_apl_title"] = new_title
                    st.rerun()

                except Exception as e:
                    st.error(f"创建或保存新APL文件时出错：{e}")

        # 绑定新建按钮到对话框
        if st.button("新建", use_container_width=True):
            create_new_apl()

    # 在选择框下方显示选定APL的详细信息
    if selected_title:
        selected_apl_data = apl_archive.get_apl_data(selected_title)
        # 传递 apl_archive 实例
        if selected_apl_data is None:
            st.error(f"未找到标题为 '{selected_title}' 的APL数据。")
        else:
            # 调用显示函数
            display_apl_details(selected_apl_data, selected_title, apl_archive)
