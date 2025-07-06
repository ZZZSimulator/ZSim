import streamlit as st


def page_apl_editor():
    st.title("ZZZ Simulator - APL编辑器")
    from zsim.lib_webui.process_apl_editor import go_apl_editor

    go_apl_editor()


page_apl_editor()
