import os
import streamlit as st
from zsim.define import DOCS_DIR


def show_apl_doc():
    apl_doc_path = os.path.abspath(os.path.join(DOCS_DIR, "ReadMe.md"))
    with open(apl_doc_path, "r", encoding="utf-8") as f:
        apl_doc_content = f.read()
    st.markdown(apl_doc_content, unsafe_allow_html=True)


show_apl_doc()
