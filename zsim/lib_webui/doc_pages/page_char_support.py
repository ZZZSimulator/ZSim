from pathlib import Path

import polars as pl
import streamlit as st
from zsim.define import DOCS_DIR


@st.dialog("关于：角色支持列表", width="large")
def dialog_about_char_support() -> None:
    docs_path = Path(DOCS_DIR)
    about_doc_path = docs_path / "角色支持介绍.md"
    with open(about_doc_path, "r", encoding="utf-8") as f:
        md_content = f.read()
    st.markdown(md_content, unsafe_allow_html=True)


# 显示角色与CID对应表
def show_char_cid_mapping() -> None:
    """
    显示角色与CID对应表。

    该函数会从 CSV 文件构建一个 Polars DataFrame，计算“角色支持度”，
    并将“角色支持度”、“技能测帧”、“Buff支持”、“影画支持”列的数值转换为图标，
    然后按照指定的列顺序（角色名, CID, 角色支持度, 技能测帧, Buff支持, 影画支持）
    在 Streamlit 界面上展示该表格。

    计算角色支持度
    规则：
    -1: 不支持
     0: 不完全支持
     1: 完全支持

    详细逻辑：
    1. 如果“动作建模”>=1、“Buff支持”>=1、“影画支持”>=1，则“角色支持度”为 1。
    2. 否则，如果“动作建模”>=0 且“Buff支持”>=0，则“角色支持度”为 0。
    3. 其他所有情况，“角色支持度”为 -1。

    """
    st.markdown("### 角色支持列表")
    st.caption("角色与CID的对应关系仅与本模拟器内部功能有关")

    # 从 character.csv 加载数据
    lf = pl.scan_csv("./zsim/data/character.csv")

    def map_support_to_icon(value: float | int) -> str:
        """将支持度数值转换为图标"""
        if value >= 1:
            return "✅ 完全"
        elif value <= -1:
            return "❌ 不支持"
        else:
            return "⚠️ 不完全"

    lf_with_support_level = lf.with_columns(
        pl.when((pl.col("动作建模") >= 1) & (pl.col("Buff支持") >= 1) & (pl.col("影画支持") >= 1))
        .then(pl.lit(1))
        .when((pl.col("动作建模") >= 0) & (pl.col("Buff支持") >= 0))
        .then(pl.lit(0))
        .otherwise(pl.lit(-1))
        .alias("角色支持度")
    )

    # 将支持度相关列的数值转换为图标
    lf_with_icons = lf_with_support_level.with_columns(
        pl.col("name").alias("角色名称"),
        pl.col("角色支持度")
        .map_elements(map_support_to_icon, return_dtype=pl.String)
        .alias("角色支持度"),
        pl.col("动作建模")
        .map_elements(map_support_to_icon, return_dtype=pl.String)
        .alias("动作建模"),
        pl.col("精细测帧")
        .map_elements(map_support_to_icon, return_dtype=pl.String)
        .alias("精细测帧"),
        pl.col("Buff支持")
        .map_elements(map_support_to_icon, return_dtype=pl.String)
        .alias("Buff支持"),
        pl.col("影画支持")
        .map_elements(map_support_to_icon, return_dtype=pl.String)
        .alias("影画支持"),
    )

    # 列顺序: 角色名 (name), CID, 角色支持度, 动作建模, 精细测帧, Buff支持, 影画支持
    selected_columns = [
        "角色名称",
        "CID",
        "角色支持度",
        "动作建模",
        "精细测帧",
        "Buff支持",
        "影画支持",
    ]
    selected_lf = lf_with_icons.select(selected_columns)
    st.dataframe(selected_lf)

    if st.button("关于"):
        dialog_about_char_support()


show_char_cid_mapping()
