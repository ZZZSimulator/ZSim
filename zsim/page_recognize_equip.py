import os
import mss
import difflib
import streamlit as st

from zsim.define import EQUIP_2PC_DATA_PATH, CHARACTER_IMAGE_PATH


ch2equips = {}

if "running" not in st.session_state:
    st.session_state.running = False

def fuzzy_match(raw_name: str, name_list: list, min_same: int = 2):
    if raw_name in name_list:
        return raw_name

    candidates = []
    for e in name_list:
        if len(e) != len(raw_name):
            continue
        match_found = any(a == b and a != '%' for a, b in zip(e, raw_name))
        if len(e) == len(raw_name) and len(set(e) & set(raw_name)) >= min_same and match_found:
            candidates.append(e)

    best_name = None
    best_ratio = None

    for e in candidates:
        ratio = difflib.SequenceMatcher(None, e, raw_name).ratio()
        if best_name is None or ratio > best_ratio:
            best_name = e
            best_ratio = ratio

    return best_name

def initialization():
    with st.spinner("正在初始化，请稍候..."):
        import re
        import polars as pl

        from cnocr import CnOcr

        ocr = CnOcr()
        df = pl.read_csv(EQUIP_2PC_DATA_PATH)
        equip_list = df.select(colname = df.columns[0]).to_series().to_list()[1:]

        with mss.mss() as sct:
            for i, m in enumerate(sct.monitors[1:], 1):
                print(f"显示器 {i} : 分辨率 {m['width']}x{m['height']}   左上角 ({m['left']}, {m['top']})")

            monitor = sct.monitors[1]
            (current_w, current_h) = (monitor['width'], monitor['height'])
            
            if (current_w, current_h) == (3840, 2160):
                suffix = "4k"
                recog_head_scale = 0.2 # 至少
                recog_words_scale = 0.3 # 至少
            elif (current_w, current_h) == (2560, 1440):
                suffix = "2k"
                recog_head_scale = 1 # 至少
                recog_words_scale = 0.5 # 至少
            elif (current_w, current_h) == (1920, 1080):
                suffix = "1k"
                recog_head_scale = 1 # 至少
                recog_words_scale = 0.5 # 至少
            else:
                raise ValueError(f"当前分辨率 {current_w}x{current_h} 不支持。仅支持 3840x2160, 2560x1440, 1920x1080。")

        template_files = [os.path.join(CHARACTER_IMAGE_PATH, suffix, f) for f in os.listdir(os.path.join(CHARACTER_IMAGE_PATH, suffix)) if f.lower().endswith('.png')]

        equip_name_and_loc_pattern = re.compile(r"^([\u4e00-\u9fa5]+).*?(\d)")
        sub_attr_name_and_num_pattern = re.compile(r"^([\u4e00-\u9fa5]+).*?(\d+)?$")
        sub_attr_value_pattern = re.compile(r"^([1-9]\d*(?:\.\d)?%?)$")

        sub_attr_dict = {
            "攻击力": 19,
            "防御力": 15,
            "生命值": 112,
            "攻击力%": 3,
            "防御力%": 4.8,
            "生命值%": 3,
            "穿透值": 9,
            "穿透率%": (6, 1.2),
            "暴击率%": 2.4,
            "暴击伤害%": 4.8,
            "异常精通": 9,
            "异常掌控%": (7.5, 1.5),
            "冲击力%": (4.5, 0.9),
            "能量自动回复%": (15, 3),
            "物理伤害加成%": (7.5, 1.5),
            "火属性伤害加成%": (7.5, 1.5),
            "冰属性伤害加成%": (7.5, 1.5),
            "电属性伤害加成%": (7.5, 1.5),
            "以太伤害加成%": (7.5, 1.5),
        }

    return ocr, monitor, equip_list, recog_head_scale, recog_words_scale, template_files, equip_name_and_loc_pattern, sub_attr_name_and_num_pattern, sub_attr_value_pattern, sub_attr_dict


def loop_function(ocr, monitor, equip_list, recog_head_scale, recog_words_scale, template_files, equip_name_and_loc_pattern, sub_attr_name_and_num_pattern, sub_attr_value_pattern, sub_attr_dict):
    placeholder = st.empty()
    
    import cv2
    import numpy as np
    with mss.mss() as sct:
        while True:
            try:
                original_img = np.array(sct.grab(monitor))[:, :, :3]
                h, w = original_img.shape[:2]
                y1 = 0
                y2 = h // 3
                x1 = w // 3
                x2 = 2 * w // 3
                img = original_img[y1:y2, x1:x2]
                img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                img = cv2.resize(img, (0, 0), fx=recog_head_scale, fy=recog_head_scale)
                ch2sim = {}
                for template_path in template_files:
                    template = cv2.imread(template_path, 0)
                    template = cv2.resize(template, (0, 0), fx=recog_head_scale, fy=recog_head_scale)
                    character_id = os.path.splitext(os.path.basename(template_path))[0]
                    th, tw = template.shape[:2]
                    res = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
                    score = res.max()
                    ch2sim[character_id] = score

                ch_id = max(ch2sim, key=ch2sim.get)
                max_score = ch2sim[ch_id]
                print(max_score)
                if max_score >= 0.9:
                    img = cv2.resize(original_img, (0, 0), fx=recog_words_scale, fy=recog_words_scale)
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    result = ocr.ocr(img)
                    
                    main_attr = level = equip_name = equip_loc = None
                    sub_attr = []
                    for idx, line in enumerate(result):
                        text = line['text'].strip()

                        match = equip_name_and_loc_pattern.match(text)
                        if match:
                            chs = fuzzy_match(match.group(1), equip_list, min_same=2)
                            digit = int(match.group(2))
                            if chs is not None and 1 <= digit <= 6:
                                equip_name = chs
                                equip_loc = digit
                                continue
                        
                        try_match = []
                        if idx + 1 < len(result):
                            try_match.append((sub_attr_name_and_num_pattern.match(text), 
                                            sub_attr_value_pattern.match(result[idx+1]['text'].strip())))
                        if idx + 2 < len(result) and len(result[idx+1]['text'].strip()) == 2:
                            try_match.append((sub_attr_name_and_num_pattern.match(text+result[idx+1]['text'].strip()), 
                                            sub_attr_value_pattern.match(result[idx+2]['text'].strip())))

                        for match1, match2 in try_match:
                            if not match1 or not match2:
                                continue
                            chs = match1.group(1)
                            digit = int(match1.group(2)) if match1.group(2) is not None else 0
                            value = match2.group(1)

                            chs = fuzzy_match(chs if value[-1] != "%" else (chs + "%"), sub_attr_dict.keys(), min_same=1)
                            value = float(value if value[-1] != "%" else value[:-1])
                            
                            if chs is None:
                                break

                            if 0 <= digit <= 5 and value > 0:
                                if isinstance(sub_attr_dict[chs], (int, float)) and abs(value - sub_attr_dict[chs] * (digit + 1)) < 1e-4:
                                    sub_attr.append((chs, digit + 1, value))
                                    break
                                elif digit == 0 and not main_attr:
                                    if (equip_loc, chs) == (1, "生命值"):
                                        level = (value - 550.0) / 110.0
                                    elif (equip_loc, chs) == (2, "攻击力"):
                                        level_5 = (value - 79.0) // 79.0
                                        cache = (value - 79.0) % 79.0
                                        if cache > 0.0:
                                            level_1 = (cache + 1) / 16.0
                                            level = level_5 * 5 + level_1
                                        else:
                                            level = level_5 * 5
                                    elif (equip_loc, chs) == (3, "防御力"):
                                        level_5 = (value - 46.0) // 46.0
                                        level_1 = ((value - 46.0) % 46.0) / 9.0
                                        level = level_5 * 5 + level_1
                                    elif equip_loc in [4, 5, 6] and chs in ["生命值%", "攻击力%", "防御力%"]:
                                        if chs == "防御力%":
                                            level = (value - 12.0) / 2.4
                                        else:
                                            level = (value - 7.5) / 1.5
                                    elif isinstance(sub_attr_dict[chs], (tuple)) and equip_loc in [5, 6]:
                                        level = (value - sub_attr_dict[chs][0]) / sub_attr_dict[chs][1]
                                    elif equip_loc == 4:
                                        if chs == "暴击率%":
                                            level = (value - 6.0) / 1.2
                                        elif chs == "暴击伤害%":
                                            level = (value - 12.0) / 2.4
                                        elif chs == "异常精通":
                                            level_5 = (value - 23.0) // 23.0
                                            cache = (value - 23.0) % 23.0
                                            level_2 = cache // 9.0
                                            cache = cache % 9.0
                                            level_1 = cache / 4.0
                                            level = level_5 * 5 + level_2 * 2 + level_1
                                    
                                    if level is not None:
                                        main_attr = (chs, value)
                    
                    sub_attr = list(set(sub_attr))
                    if (
                        equip_name in equip_list
                        and level is not None
                        and level.is_integer()
                        and 0 <= int(level) <= 15
                        and (
                            len(sub_attr) == 4
                            or (len(sub_attr) == 3 and 0 <= int(level) <= 2)
                        )
                        and main_attr
                    ):
                        ch2equips[(int(ch_id), int(equip_loc))] = (equip_name, int(level), main_attr, sub_attr)

            except Exception as e:
                print("Error occurred: ", e)

            with placeholder.container():
                if ch2equips:
                    lines = []
                    for k, v in ch2equips.items():
                        line = f"""
                        <div style="padding:4px 0;">
                            <b>角色/位置:</b> {k}　
                            <b>装备:</b> {v[0]} (Lv.{v[1]})　
                            <b>主词条:</b> {v[2][0]}: {v[2][1]}　
                            <b>副词条:</b> {'，'.join([f"{x[0]}({x[1]}):{x[2]}" for x in v[3]])}
                        </div>
                        """
                        lines.append(line)
                    st.markdown('\n'.join(lines), unsafe_allow_html=True)
                else:
                    st.info("暂无装备识别结果")


def page_loop_task():
    st.title("任务运行页面")

    st.markdown("<div style='text-align: center; font-size: 20px;'>请设置参数后开始任务，点击停止结束循环</div>", unsafe_allow_html=True)
    # col1, col2 = st.columns(2)

    # with col1:
    #     param1 = st.text_input("参数 1", key="param1")
    # with col2:
    #     param2 = st.text_input("参数 2", key="param2")

    col_start, col_stop = st.columns(2)

    with col_start:
        if st.button("开始"):
            st.session_state.running = True
            loop_function(*initialization())

    with col_stop:
        if st.button("停止"):
            st.session_state.running = False
            st.success("任务已停止")

page_loop_task()
