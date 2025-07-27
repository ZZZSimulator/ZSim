import streamlit as st

from zsim.lib_webui.clean_results_cache import (
    delete_result,
    get_all_results,
    rename_result,
)
from zsim.lib_webui.constants import IDDuplicateError


@st.fragment
def _result_manager():
    id_cache = get_all_results()
    options = list(id_cache.keys())[::-1]
    if not options:
        st.warning("没有找到任何结果缓存。请先运行模拟器生成结果。", icon="⚠️")
        st.stop()

    st.markdown("选择一个结果：")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        selected_key = st.selectbox("选择你要查看的结果", options, label_visibility="collapsed")
    with col2:
        st.markdown(
            f'<span style="color:gray;">备注：<br>{id_cache.get(selected_key, "N/A")}</span>',
            unsafe_allow_html=True,
        )
    with col3:

        @st.dialog("重命名结果")
        def rename_dialog(current_key, current_comment):
            new_name = st.text_input("请输入新的ID", value=current_key)
            new_comment = st.text_input("请输入新的备注信息", value=current_comment)
            col1_dialog, col2_dialog = st.columns(2)
            with col1_dialog:
                if st.button("保存", key="save_rename", use_container_width=True):
                    try:
                        rename_result(current_key, new_name or "", new_comment or "")
                        st.rerun()
                    except FileNotFoundError:
                        st.warning("请检查文件是否存在或ID是否正确。", icon="⚠️")
                    except IDDuplicateError as e:
                        st.warning(e, icon="⚠️")
            with col2_dialog:
                if st.button("取消", key="cancel_rename", use_container_width=True):
                    st.rerun()

        if st.button("重命名", use_container_width=True):
            rename_dialog(selected_key, id_cache.get(selected_key, ""))
    with col4:

        @st.dialog("删除结果")
        def delete_dialog(key_to_delete):
            st.warning(f"你确定要删除 {key_to_delete} 吗？", icon="⚠️")
            col1_dialog, col2_dialog = st.columns(2)
            with col1_dialog:
                if st.button("确定", key="confirm_del_result", use_container_width=True):
                    delete_result(key_to_delete)
                    st.rerun()
            with col2_dialog:
                if st.button("取消", key="cancel", use_container_width=True):
                    st.rerun()

        if st.button("删除", use_container_width=True):
            delete_dialog(selected_key)

    return selected_key


def page_data_analysis():
    from zsim.lib_webui.process_buff_result import show_buff_result
    from zsim.lib_webui.process_dmg_result import show_dmg_result
    from zsim.lib_webui.process_parallel_data import (
        judge_parallel_result,
        process_parallel_result,
    )

    st.title("ZZZ Simulator - 数据分析")

    selected_key = _result_manager()

    if not st.toggle("开启数据分析"):
        st.stop()

    # Ensure selected_key is valid before proceeding
    if not selected_key:
        st.error("无法获取选定的结果键。")
        st.stop()

    if judge_parallel_result(selected_key):
        st.write("这是一个并行模式（多进程）的结果。")
        process_parallel_result(selected_key)
    else:
        st.write("这是一个普通模式（单进程）的结果。")
        show_dmg_result(selected_key)
        show_buff_result(selected_key)


page_data_analysis()
