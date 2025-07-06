import streamlit as st
from lib_webui.version_checker import check_github_updates

# 页面导航
PAGES = {
    "功能选择": [
        st.Page("page_character_config.py", title="角色配置"),
        st.Page("page_simulator.py", title="模拟器"),
        st.Page("page_data_analysis.py", title="数据分析"),
        st.Page("page_apl_editor.py", title="APL编辑器"),
    ],
    "文档": [
        st.Page("lib_webui/doc_pages/page_char_support.py", title="角色支持列表"),
        st.Page("lib_webui/doc_pages/page_apl_doc.py", title="APL设计书"),
        st.Page("lib_webui/doc_pages/page_contribution.py", title="贡献指南"),
    ],
}


def main():
    st.set_page_config(layout="wide")
    st.markdown(
        """
        <style>
            .reportview-container {
                margin-top: -2em;
            }
            #MainMenu {visibility: hidden;}
            .stDeployButton {display:none;}
            footer {visibility: hidden;}
            #stDecoration {display:none;}
        </style>
        """,
        unsafe_allow_html=True,
    )
    
    # 检查GitHub更新
    check_github_updates()
    
    pg = st.navigation(PAGES, expanded=True)
    pg.run()


if __name__ == "__main__":
    main()
