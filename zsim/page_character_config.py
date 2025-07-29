import streamlit as st
import toml


def page_character_config():
    st.title("ZZZ Simulator - 角色配置")
    from zsim.define import saved_char_config
    from zsim.lib_webui.constants import default_chars

    if "name_box" in saved_char_config:
        default_chars = saved_char_config["name_box"]
    from zsim.lib_webui.constants import (
        equip_set2_options,
        equip_set4_options,
        weapon_options,
        weapon_profession_map,
        weapon_rarity_map,
        weapon_char_map,
        char_profession_map,
        profession_chars_map,
    )

    col0, col1, col2, col3, col4, col5, col6, col7 = st.columns([1, 1, 1, 1, 1, 1, 1, 1])
    with col0:
        profession_0 = st.selectbox(
            "角色1特性",
            list(profession_chars_map.keys()),
            index=list(profession_chars_map.keys()).index("不限特性"),
            key="profession_select_0",
        )
    with col1:
        name_box_0 = [
            st.selectbox(
                "角色1",
                profession_chars_map[profession_0],
                index=profession_chars_map[profession_0].index(default_chars[0])
                if len(default_chars) > 0 and default_chars[0] in profession_chars_map[profession_0]
                else 0,
                key="char_select_0",
            )
        ]
    with col3:
        profession_1 = st.selectbox(
            "角色2特性",
            list(profession_chars_map.keys()),
            index=list(profession_chars_map.keys()).index("不限特性"),
            key="profession_select_1",
        )
    with col4:
        name_box_1 = [
            st.selectbox(
                "角色2",
                profession_chars_map[profession_1],
                index=profession_chars_map[profession_1].index(default_chars[1])
                if len(default_chars) > 1 and default_chars[1] in profession_chars_map[profession_1]
                else 0,
                key="char_select_1",
            )
        ]
    with col6:
        profession_2 = st.selectbox(
            "角色3特性",
            list(profession_chars_map.keys()),
            index=list(profession_chars_map.keys()).index("不限特性"),
            key="profession_select_2",
        )
    with col7:
        name_box_2 = [
            st.selectbox(
                "角色3",
                profession_chars_map[profession_2],
                index=profession_chars_map[profession_2].index(default_chars[2])
                if len(default_chars) > 2 and default_chars[2] in profession_chars_map[profession_2]
                else 0,
                key="char_select_2",
            )
        ]
    name_box = name_box_0 + name_box_1 + name_box_2
    if len(name_box) != 3:
        st.stop()
    if len(name_box) != len(set(name_box)):
        st.error("请选择三个不同的角色")
        st.stop()
    for name in name_box:
        with st.expander(f"{name}的配置"):
            col_weapon, col_level, col_cinema = st.columns(3)
            with col_weapon:
                show_adapted_weapon = st.session_state.get(f"{name}_show_adapted_weapon", True)
                show_rarity_s = st.session_state.get(f"{name}_show_rarity_s", True)
                show_rarity_a = st.session_state.get(f"{name}_show_rarity_a", True)
                show_rarity_b = st.session_state.get(f"{name}_show_rarity_b", False)
                char_profession = char_profession_map.get(name)
                if show_adapted_weapon and char_profession:
                    filtered_weapon_options = [
                        w for w in weapon_options if weapon_profession_map.get(w) == char_profession
                    ]
                else:
                    filtered_weapon_options = list(weapon_options)

                # 根据稀有度筛选
                filtered_weapon_options = [
                    w
                    for w in filtered_weapon_options
                    if (show_rarity_s and weapon_rarity_map.get(w) == "S")
                    or (show_rarity_a and weapon_rarity_map.get(w) == "A")
                    or (show_rarity_b and weapon_rarity_map.get(w) == "B")
                ]
                rarity_order = {"S": 0, "A": 1, "B": 2}
                filtered_weapon_options = sorted(
                    filtered_weapon_options,
                    key=lambda w: (rarity_order.get(weapon_rarity_map.get(w), 3), w),
                )

                if name in saved_char_config:
                    current_weapon = saved_char_config[name].get("weapon")
                else:
                    current_weapon = None
                # 如果当前音擎不在可选列表，或未设置，则默认选第一个
                if not filtered_weapon_options:
                    st.selectbox(
                        "音擎",
                        [],
                        key=f"{name}_weapon",
                    )
                else:
                    if current_weapon not in filtered_weapon_options:
                        current_weapon = filtered_weapon_options[0]
                    st.selectbox(
                        "音擎",
                        filtered_weapon_options,
                        index=filtered_weapon_options.index(current_weapon),
                        key=f"{name}_weapon",
                        format_func=lambda x: (
                            f"({weapon_rarity_map.get(x, '未知')}"
                            f"{' ' + weapon_char_map.get(x) if weapon_char_map.get(x) else ''}) {x}"
                        ),
                    )

                col_rarity = st.columns(4)
                with col_rarity[0]:
                    show_adapted_weapon = st.checkbox(
                        "只显示适配音擎",
                        value=show_adapted_weapon,
                        key=f"{name}_show_adapted_weapon",
                    )
                with col_rarity[1]:
                    show_rarity_s = st.checkbox(
                        "S",
                        value=show_rarity_s,
                        key=f"{name}_show_rarity_s",
                    )
                with col_rarity[2]:
                    show_rarity_a = st.checkbox(
                        "A",
                        value=show_rarity_a,
                        key=f"{name}_show_rarity_a",
                    )
                with col_rarity[3]:
                    show_rarity_b = st.checkbox(
                        "B",
                        value=show_rarity_b,
                        key=f"{name}_show_rarity_b",
                    )
            with col_level:
                st.number_input(
                    "音擎精炼等级",
                    min_value=1,
                    max_value=5,
                    value=saved_char_config[name].get("weapon_level", 1)
                    if name in saved_char_config
                    else 1,
                    key=f"{name}_weapon_level",
                )
            with col_cinema:
                st.number_input(
                    "影画等级",
                    min_value=0,
                    max_value=6,
                    value=saved_char_config[name].get("cinema", 0)
                    if name in saved_char_config
                    else 0,
                    key=f"{name}_cinema_level",
                )
            equip_style = st.radio(
                "驱动盘搭配方式",
                ["4+2", "2+2+2"],
                index=0
                if name not in saved_char_config or "equip_style" not in saved_char_config[name]
                else (0 if saved_char_config[name]["equip_style"] == "4+2" else 1),
                key=f"{name}_equip_style",
            )
            col1, col2 = st.columns(2)
            with col1:
                if equip_style == "4+2":
                    st.selectbox(
                        "四件套",
                        equip_set4_options,
                        index=equip_set4_options.index(saved_char_config[name]["equip_set4"])
                        if name in saved_char_config and "equip_set4" in saved_char_config[name]
                        else 0,
                        key=f"{name}_equip_set4",
                    )
                    st.selectbox(
                        "二件套",
                        equip_set2_options,
                        index=equip_set2_options.index(
                            saved_char_config[name].get("equip_set2_a", "啄木鸟电音")
                        )
                        if name in saved_char_config
                        else 0,
                        key=f"{name}_equip_set2",
                    )
                else:
                    st.selectbox(
                        "二件套A",
                        equip_set2_options,
                        index=equip_set2_options.index(
                            saved_char_config[name].get("equip_set2_a", "啄木鸟电音")
                        )
                        if name in saved_char_config
                        else 0,
                        key=f"{name}_equip_set2A",
                    )
                    st.selectbox(
                        "二件套B",
                        equip_set2_options,
                        index=equip_set2_options.index(
                            saved_char_config[name].get("equip_set2_b", "啄木鸟电音")
                        )
                        if name in saved_char_config and "equip_set2_b" in saved_char_config[name]
                        else 0,
                        key=f"{name}_equip_set2B",
                    )
                    st.selectbox(
                        "二件套C",
                        equip_set2_options,
                        index=equip_set2_options.index(
                            saved_char_config[name].get("equip_set2_c", "啄木鸟电音")
                        )
                        if name in saved_char_config and "equip_set2_c" in saved_char_config[name]
                        else 0,
                        key=f"{name}_equip_set2C",
                    )
            with col2:
                from zsim.lib_webui.constants import (
                    main_stat4_options,
                    main_stat5_options,
                    main_stat6_options,
                )

                st.selectbox(
                    "四号位主词条",
                    main_stat4_options,
                    index=main_stat4_options.index(saved_char_config[name].get("drive4", "攻击力%"))
                    if name in saved_char_config
                    else 0,
                    key=f"{name}_main_stat4",
                )
                st.selectbox(
                    "五号位主词条",
                    main_stat5_options,
                    index=main_stat5_options.index(saved_char_config[name].get("drive5", "攻击力%"))
                    if name in saved_char_config
                    else 0,
                    key=f"{name}_main_stat5",
                )
                st.selectbox(
                    "六号位主词条",
                    main_stat6_options,
                    index=main_stat6_options.index(
                        saved_char_config[name].get("drive6 ", "攻击力%")
                    )
                    if name in saved_char_config
                    else 0,
                    key=f"{name}_main_stat6",
                )
            from zsim.lib_webui.constants import sc_max_value
            from zsim.lib_webui.constants import sc_max_percent

            st.text("副词条数量：")
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                st.number_input(
                    "攻击力%",
                    min_value=0,
                    max_value=sc_max_percent,
                    value=saved_char_config[name].get("scATK_percent", 0)
                    if name in saved_char_config
                    else 0,
                    key=f"{name}_scATK_percent",
                )
                st.number_input(
                    "攻击力",
                    min_value=0,
                    max_value=sc_max_value,
                    value=saved_char_config[name].get("scATK", 0)
                    if name in saved_char_config
                    else 0,
                    key=f"{name}_scATK",
                )
            with col2:
                st.number_input(
                    "生命值%",
                    min_value=0,
                    max_value=sc_max_percent,
                    value=saved_char_config[name].get("scHP_percent", 0)
                    if name in saved_char_config
                    else 0,
                    key=f"{name}_scHP_percent",
                )
                st.number_input(
                    "生命值",
                    min_value=0,
                    max_value=sc_max_value,
                    value=saved_char_config[name].get("scHP", 0)
                    if name in saved_char_config
                    else 0,
                    key=f"{name}_scHP",
                )
            with col3:
                st.number_input(
                    "防御力%",
                    min_value=0,
                    max_value=sc_max_percent,
                    value=saved_char_config[name].get("scDEF_percent", 0)
                    if name in saved_char_config
                    else 0,
                    key=f"{name}_scDEF_percent",
                )
                st.number_input(
                    "防御力",
                    min_value=0,
                    max_value=sc_max_value,
                    value=saved_char_config[name].get("scDEF", 0)
                    if name in saved_char_config
                    else 0,
                    key=f"{name}_scDEF",
                )
            with col4:
                st.number_input(
                    "暴击率",
                    min_value=0,
                    max_value=sc_max_percent,
                    value=saved_char_config[name].get("scCRIT", 0)
                    if name in saved_char_config
                    else 0,
                    key=f"{name}_scCRIT",
                )
                st.number_input(
                    "暴击伤害",
                    min_value=0,
                    max_value=sc_max_percent,
                    value=saved_char_config[name].get("scCRIT_DMG", 0)
                    if name in saved_char_config
                    else 0,
                    key=f"{name}_scCRIT_DMG",
                )
            with col5:
                st.number_input(
                    "异常精通",
                    min_value=0,
                    max_value=sc_max_percent,
                    value=saved_char_config[name].get("scAnomalyProficiency", 0)
                    if name in saved_char_config
                    else 0,
                    key=f"{name}_scAnomalyProficiency",
                )
                st.number_input(
                    "穿透值",
                    min_value=0,
                    max_value=sc_max_percent,
                    value=saved_char_config[name].get("scPEN", 0)
                    if name in saved_char_config
                    else 0,
                    key=f"{name}_scPEN",
                )
            col1, col2 = st.columns(2)
            with col1:
                if name not in saved_char_config:
                    saved_char_config[name] = {}
                crit_balancing: bool = st.checkbox(
                    "使用暴击配平算法",
                    value=saved_char_config[name].get("crit_balancing", False),
                    key=f"{name}_crit_balancing",
                )
                if st.session_state.get(f"{name}_crit_rate_limit") is None:
                    st.session_state[f"{name}_crit_rate_limit"] = saved_char_config[name].get(
                        "crit_rate_limit", 0.95
                    )
                if crit_balancing:
                    st.number_input(
                        "暴击率上限",
                        min_value=0.0,
                        max_value=1.0,
                        value=st.session_state[f"{name}_crit_rate_limit"],
                        key=f"{name}_crit_rate_limit",
                        help="配平算法会将角色局外面板的暴击率限制在此值以下，适用于会吃到暴击率buff的情况，以防止溢出",
                    )
        char_config = {
            "name": name,
            "weapon": st.session_state[f"{name}_weapon"],
            "weapon_level": st.session_state[f"{name}_weapon_level"],
            "cinema": st.session_state[f"{name}_cinema_level"],
            "crit_balancing": st.session_state[f"{name}_crit_balancing"],
            "crit_rate_limit": st.session_state[f"{name}_crit_rate_limit"],
            "scATK_percent": st.session_state[f"{name}_scATK_percent"],
            "scATK": st.session_state[f"{name}_scATK"],
            "scHP_percent": st.session_state[f"{name}_scHP_percent"],
            "scHP": st.session_state[f"{name}_scHP"],
            "scDEF_percent": st.session_state[f"{name}_scDEF_percent"],
            "scDEF": st.session_state[f"{name}_scDEF"],
            "scAnomalyProficiency": st.session_state[f"{name}_scAnomalyProficiency"],
            "scPEN": st.session_state[f"{name}_scPEN"],
            "scCRIT": st.session_state[f"{name}_scCRIT"],
            "scCRIT_DMG": st.session_state[f"{name}_scCRIT_DMG"],
            "drive4": st.session_state[f"{name}_main_stat4"],
            "drive5": st.session_state[f"{name}_main_stat5"],
            "drive6": st.session_state[f"{name}_main_stat6"],
            "equip_style": st.session_state[f"{name}_equip_style"],
        }
        if st.session_state[f"{name}_equip_style"] == "4+2":
            char_config["equip_set4"] = st.session_state[f"{name}_equip_set4"]
            char_config["equip_set2_a"] = st.session_state[f"{name}_equip_set2"]
        else:
            char_config["equip_set2_a"] = st.session_state[f"{name}_equip_set2A"]
            char_config["equip_set2_b"] = st.session_state[f"{name}_equip_set2B"]
            char_config["equip_set2_c"] = st.session_state[f"{name}_equip_set2C"]
        st.session_state[f"{name}_config"] = char_config
    if not st.button("提交并保存角色配置"):
        st.stop()
    _config_to_save = {"name_box": name_box}
    for name in name_box:
        _config_to_save[name] = st.session_state[f"{name}_config"]
    saved_char_config.update(_config_to_save)
    from zsim.define import char_config_file

    with open(char_config_file, "w", encoding="utf-8") as f:
        toml.dump(saved_char_config, f)
    from zsim.lib_webui.process_char_config import display_character_panels

    display_character_panels(name_box)


page_character_config()
