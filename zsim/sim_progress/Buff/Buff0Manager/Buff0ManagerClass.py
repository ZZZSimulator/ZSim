import copy
import itertools
from typing import TYPE_CHECKING
from collections import defaultdict
import pandas as pd
from zsim.define import (
    BUFF_0_REPORT,
    CHARACTER_DATA_PATH,
    EXIST_FILE_PATH,
    JUDGE_FILE_PATH,
    saved_char_config,
)

from .. import JudgeTools
from ..buff_class import Buff

if TYPE_CHECKING:
    from zsim.simulator.simulator_class import Simulator
    from zsim.sim_progress.Character.character import Character


class Buff0Manager:
    def __init__(
        self,
        name_box: list[str],
        judge_list_set: list[list[str]],
        weapon_dict: dict[str, list],
        cinema_dict: dict,
        char_obj_dict: dict | None,
        sim_instance: "Simulator",
    ):
        # 加载文件
        self.EXIST_FILE = pd.read_csv(EXIST_FILE_PATH, index_col="BuffName")
        self.JUDGE_FILE = pd.read_csv(JUDGE_FILE_PATH, index_col="BuffName")
        self.CHARACTER_FILE = pd.read_csv(CHARACTER_DATA_PATH, index_col="name")
        self.sim_instance: "Simulator" = sim_instance
        self.judge_list_set = judge_list_set
        self.weapon_dict = weapon_dict
        self.cinema_dict = cinema_dict
        self.char_name_box = name_box  # 角色名列表
        self.name_order_box = self.change_name_box()  # 角色名顺序字典
        self.char_obj_dict = char_obj_dict
        self.buff_info_inventory: dict[str, dict[str, tuple[dict, dict]]] = defaultdict(dict)

        # 设置初始值和数据预处理
        self.allbuff_list = self.EXIST_FILE.index.tolist()  # 将索引列转为列表
        self.buff_name_box: dict[str, list[str]] = {}

        # 初始化exist_buff_dict
        self.exist_buff_dict: dict[str, dict[str, Buff]] = {"enemy": {}}
        for _char_name in self.char_name_box:
            self.exist_buff_dict[_char_name] = {}
        # 把处理judge_list_set
        self.__equip_set2_box = []
        self.char_equip_info: dict[str, dict[str, str]] = {}
        self.__process_judge_list_set()

        self.total_judge_condition_list = (
            list(itertools.chain.from_iterable(self.judge_list_set))
            + self.__equip_set2_box
        )
        self.__selector = self.__selector(self)
        self.__selector.select_buff_into_exist_buff_dict()
        self.__passively_updating_change()
        # self.__process_label()
        """
        由于deepcopy存在问题，导致buff_0这里初始化好的only_active_by参数在后续复制的过程中可能丢失，
        所以这里索性不做处理，直接到data_struct中现场处理。
        """
        self.__process_additional_ability_data()
        # self.initialize_buff_listener()

        if BUFF_0_REPORT:
            self.sim_instance.schedule_data.change_process_state()
            print(self)

    def __str__(self):
        output = ""
        for _char_name, _sub_dict in self.exist_buff_dict.items():
            output += f"本次模拟中{_char_name}可能吃到的Buff为：\n"
            for _i in _sub_dict.values():
                output += f"  {_i.ft.index}\n"
        return output

    def initialize_buff_listener(self):
        """处理buff监听器的初始化"""
        for _char_name, _sub_dict in self.exist_buff_dict.items():
            for _buff_0 in _sub_dict.values():
                if not isinstance(_buff_0, Buff):
                    raise TypeError(f"存在非Buff类型的对象：{_buff_0}")
                if _buff_0.ft.listener_id is not None:
                    _obj = (
                        self.char_obj_dict[_buff_0.ft.operator]
                        if _buff_0.ft.operator != "enemy"
                        else self.sim_instance.schedule_data.enemy
                    )
                    self.sim_instance.listener_manager.listener_factory(
                        listener_owner=_obj, initiate_signal=_buff_0.ft.listener_id
                    )

    def __process_label(self):
        """处理label类型的内容"""
        for _char_name, _dict in self.exist_buff_dict.items():
            for _index, _buff_0 in _dict.items():
                if not _buff_0.ft.label:
                    continue
                if (
                    "only_active_by" in _buff_0.ft.label
                    and _buff_0.ft.label["only_active_by"][0] == "self"
                ):
                    char_obj = JudgeTools.find_char_from_name(
                        _buff_0.ft.operator, sim_instance=self.sim_instance
                    )
                    _buff_0.ft.label["only_active_by"] = [char_obj.CID]

    def __process_judge_list_set(self):
        """将judge_list_set中的信息全部处理到self.char_equip_info 中"""
        for _sub_list in self.judge_list_set:
            _name = _sub_list[0]
            _weapon = _sub_list[1]
            _equip_set4 = _sub_list[2]
            _equip_set2_a = _sub_list[3]
            if saved_char_config[_name]["equip_style"] == "4+2":
                self.char_equip_info[_name] = {
                    "weapon": _weapon,
                    "equip_set4": _equip_set4,
                    "equip_set2_a": _equip_set2_a,
                    "equip_style": "4+2",
                }
            elif saved_char_config[_name]["equip_style"] == "2+2+2":
                _equip_set2_b = saved_char_config[_name]["equip_set2_b"]
                _equip_set2_c = saved_char_config[_name]["equip_set2_c"]
                self.char_equip_info[_name] = {
                    "weapon": _weapon,
                    "equip_set4": None,
                    "equip_set2_a": _equip_set2_a,
                    "equip_set2_b": _equip_set2_b,
                    "equip_set2_c": _equip_set2_c,
                    "equip_style": "2+2+2",
                }
                self.__equip_set2_box.append(_equip_set2_b)
                self.__equip_set2_box.append(_equip_set2_c)
            else:
                raise ValueError("无法解析的驱动盘装备策略！")

    def __process_additional_ability_data(self):
        """修改角色对象的组队被动激活参数"""
        for _char_name, sub_exist_dict in self.exist_buff_dict.items():
            if _char_name == "enemy":
                continue
            char_instance = self.char_obj_dict[_char_name]
            for _buff_index, _buff_instance in sub_exist_dict.items():
                if (
                    _buff_instance.ft.is_additional_ability
                    and _char_name == _buff_instance.ft.bufffrom
                ):
                    char_instance.additional_abililty_active = True
                    break
            else:
                char_instance.additional_abililty_active = False
            # print(char_instance.NAME, char_instance.additional_abililty_active)

    def change_name_box(self):
        """
        生成每个角色对应的namebox列表，以自己作为第0位角色。
        举例：
        name_box = [苍角，艾莲，莱卡恩]
        name_order_dict = {
        苍角：[苍角，艾莲，莱卡恩，enemy],
        艾莲：[艾莲，莱卡恩，苍角，enemy],
        莱卡恩：[莱卡恩，苍角，艾莲，enemy]
        }
        """
        name_box = self.char_name_box
        output_name_dict = {}
        for i in range(len(name_box)):
            new_name_box = name_box[i:] + name_box[:i]
            output_name_dict[name_box[i]] = new_name_box + ["enemy"]
        return output_name_dict

    def __passively_updating_change(self):
        """完成初始化之前，进行最后的参数调整。"""
        for char_name, sub_buff_dict in self.exist_buff_dict.items():
            for _buff_0 in sub_buff_dict.values():
                if not isinstance(_buff_0, Buff):
                    raise TypeError
                if char_name == "enemy":
                    _buff_0.ft.passively_updating = False
                else:
                    if _buff_0.ft.operator != char_name:
                        _buff_0.ft.passively_updating = True
                    else:
                        _buff_0.ft.passively_updating = False

    def search_equipper(self, equipment: str) -> str | None:
        """
        根据输入的装备名称寻找装备者
        临时使用，该函数只能返回找到的第一个，
        buff系统重构后将重写此逻辑
        """
        for _char_name, sub_list in self.weapon_dict.items():
            if sub_list[0] == equipment:
                return _char_name
        else:
            return None

    class __selector:
        def __init__(self, buff_0_manager_instance):
            self.buff_0_manager: Buff0Manager = buff_0_manager_instance
            self.__select_strategy_map = {
                "char_handler": None,
                "weapon_handler": None,
                "drive_handler": None,
            }
            self.__special_set2_dict = {"如影相随": ["Buff-驱动盘-如影相随-二件套"]}
            self.__buff_0_pool: dict[str, tuple] = {}
            self.__additional_ability_data = self.__additional_ability_data(
                self.buff_0_manager
            )
            self.__get_buff_0_pool()

        class __additional_ability_data:
            """组队被动数据，主要负责组队被动激活相关"""

            def __init__(self, buff_0_manager_instance):
                self.buff_0_manager: Buff0Manager = buff_0_manager_instance
                self.condition_list = [
                    "角色属性-中文",
                    "角色阵营",
                    "角色特性",
                    "支援类型",
                ]
                self.additional_ability_judge_info = {}
                self.__get_additional_ability_judge_info()
                # print(self.additional_ability_judge_info)

            def __get_additional_ability_judge_info(self):
                for _char_name in self.buff_0_manager.char_name_box:
                    sub_info_list = []
                    self.additional_ability_judge_info[_char_name] = {}
                    self.additional_ability_judge_info[_char_name][
                        "required_condition"
                    ] = self.buff_0_manager.CHARACTER_FILE.loc[
                        _char_name, "组队被动条件"
                    ]
                    for condition in self.condition_list:
                        sub_info_list.append(
                            self.buff_0_manager.CHARACTER_FILE.loc[
                                _char_name, condition
                            ]
                        )
                    self.additional_ability_judge_info[_char_name]["config_info"] = (
                        sub_info_list
                    )

            def addition_skill_info_trans(self, buff_from: str):
                """
                前置函数的初始化会将组队被动的激活条件原封不动地放入字典中（包含|分隔符的字符串）
                此函数是将字符串根据分隔符分割成list，并且根据具体内容进行翻译，
                最后输出的是翻译后的list。
                例如：苍角的组队被动激活条件是‘同属性|同阵营’
                那么翻译过后就会输出：
                ['冰', '对空6课']
                """
                addition_skill_info = self.additional_ability_judge_info[buff_from]
                required_condition_list = addition_skill_info[
                    "required_condition"
                ].split("|")
                condition_list_after_trans = []
                for conditions in required_condition_list:
                    if conditions == "同阵营":
                        condition_list_after_trans.append(
                            addition_skill_info["config_info"][1]
                        )
                    elif conditions == "同属性":
                        condition_list_after_trans.append(
                            addition_skill_info["config_info"][0]
                        )
                    elif conditions in ["异常", "强攻", "支援", "击破", "防护", "命破"]:
                        condition_list_after_trans.append(conditions)
                    elif conditions in ["招架", "回避"]:
                        condition_list_after_trans.append(conditions)
                    else:
                        raise ValueError(f"无法解析的组队被动激活条件：{conditions}")
                return condition_list_after_trans

        def __get_buff_0_pool(self):
            """筛选出总的buff_0池子。"""
            # 遍历 EXIST_FILE，按条件筛选
            for buff_name, row_data in self.buff_0_manager.EXIST_FILE.iterrows():
                # 判断是否符合所有筛选条件
                buff_from = row_data["from"]

                if row_data["is_weapon"]:
                    """武器Buff"""
                    for charname in self.buff_0_manager.weapon_dict:
                        if (
                            buff_from == self.buff_0_manager.weapon_dict[charname][0]
                            and row_data["refinement"]
                            == self.buff_0_manager.weapon_dict[charname][1]
                        ):
                            self.select_buffs(buff_name, row_data)
                elif (
                    row_data["is_cinema"]
                    and buff_from in self.buff_0_manager.cinema_dict.keys()
                ):
                    """影画Buff"""
                    if (
                        row_data["refinement"]
                        <= self.buff_0_manager.cinema_dict[buff_from]
                    ):
                        self.select_buffs(buff_name, row_data)
                else:
                    """角色Buff 和 Enemy"""
                    if buff_from in self.buff_0_manager.weapon_dict:
                        """组队被动"""
                        if row_data["is_additional_ability"]:
                            """获得【足以使组队被动激活的条件集合】"""
                            condition_list_after_trans = self.__additional_ability_data.addition_skill_info_trans(
                                buff_from
                            )
                            partner_condition_list = []
                            for other_key in self.__additional_ability_data.additional_ability_judge_info:
                                if other_key != buff_from:
                                    partner_condition_list.extend(
                                        self.__additional_ability_data.additional_ability_judge_info[
                                            other_key
                                        ]["config_info"]
                                    )
                            # print(buff_name, condition_list_after_trans, partner_condition_list)
                            for conditions in condition_list_after_trans:
                                if conditions in partner_condition_list:
                                    self.select_buffs(buff_name, row_data)
                                    break
                        else:
                            if buff_from in self.buff_0_manager.char_name_box:
                                self.select_buffs(buff_name, row_data)
                    elif row_data["from"] == "enemy":
                        self.select_buffs(buff_name, row_data)
                    else:
                        if buff_from in self.buff_0_manager.total_judge_condition_list:
                            self.select_buffs(buff_name, row_data)

        def select_buffs(self, buff_name, row_data):
            """
            根据buffname为索引，去dataframe中寻找对应的judge，并且和输入的rowdata打包进入selected buffs
            """
            judge_row_data = self.buff_0_manager.JUDGE_FILE.loc[buff_name]
            row_data["BuffName"] = buff_name
            self.__buff_0_pool[buff_name] = (row_data, judge_row_data)

        def select_buff_into_exist_buff_dict(self):
            for buff_name, buff_info_tuple in self.__buff_0_pool.items():
                buff_from = buff_info_tuple[0]["from"]
                adding_code = str(int(buff_info_tuple[0]["add_buff_to"])).zfill(4)
                if buff_from in self.buff_0_manager.char_name_box:
                    """如果buff来自于角色，那么buff_from就一定指向这个buff的真正来源，也就是buff的拥有者（并非buff的受益者）"""
                    current_name_box = self.buff_0_manager.name_order_box[buff_from]
                    selected_characters = [
                        current_name_box[i]
                        for i in range(len(current_name_box))
                        if adding_code[i] == "1"
                    ]
                    if buff_from not in selected_characters:
                        selected_characters.append(buff_from)
                    for _name in selected_characters:
                        self.initiate_buff(buff_info_tuple, buff_name, _name, buff_from)
                elif buff_from == "enemy":
                    """ 
                    进入这一分支的所有buff实际上都是环境或是其他原因而强加给enemy的，
                    由于buffload函数并不会以“enemy”为主视角来判定buff，
                    所有添加给enemy的buff都是在buffload遍历其他角色时产生、或是其他阶段强行添加的，
                    所以，此处的buff_orner参数传入并不严格，因为用不到。
                    """
                    self.initiate_buff(buff_info_tuple, buff_name, "enemy", "enemy")
                elif buff_from in self.buff_0_manager.total_judge_condition_list:
                    """
                    如果buff不属于角色和enemy，那么buff肯定来自装备。
                    """
                    for (
                        char_name,
                        _sub_equip_info_dict,
                    ) in self.buff_0_manager.char_equip_info.items():
                        if buff_from in _sub_equip_info_dict.values():
                            self.processor_equipment_buff(
                                adding_code, buff_info_tuple, buff_name, char_name
                            )

        def initiate_buff(self, buff_info_tuple, buff_name, benifiter, buff_orner):
            """
            参数中的benifiter和orner不是一个名字。benifiter是buff的受益者，但并不一定是触发buff的角色。
            而buff_orner是触发buff者，哪怕这个buff是加给别人的，作为触发者，它的exist_buff_dict中也应该保留这个buff，
            这样，在BuffLoad函数对buff_0进行判断时，就可以通过buff.ft.passively_updating参数来避开不必要的判断了。
            """
            dict_1 = copy.deepcopy(buff_info_tuple[0])  # 创建 dict_1 的副本
            dict_2 = copy.deepcopy(buff_info_tuple[1])  # 创建 dict_2 的副本
            dict_1["operator"] = buff_orner
            if benifiter == buff_orner:
                dict_1["passively_updating"] = False
            else:
                dict_1["passively_updating"] = True
            buff_new = Buff(
                dict_1, dict_2, sim_instance=self.buff_0_manager.sim_instance
            )
            buff_new.ft.beneficiary = benifiter
            self.buff_0_manager.exist_buff_dict[benifiter][buff_name] = buff_new
            # self.buff_0_manager.buff_info_inventory[benifiter][buff_name] = (dict_1, dict_2)

        def processor_equipment_buff(
            self, adding_code, buff_info_tuple, buff_name, equipment_carrier
        ):
            """处理来源于装备的Buff"""
            """ 为了防止只佩戴了二件套的情况下，筛选出了拥有相同buff_from的四件套效果，之类需要进行额外的判断。"""
            current_name_box = self.buff_0_manager.name_order_box[equipment_carrier]
            personal_equip_dict = self.buff_0_manager.char_equip_info[equipment_carrier]
            buff_from = buff_info_tuple[0]["from"]
            if personal_equip_dict["equip_style"] == "4+2":
                if (
                    personal_equip_dict["equip_set2_a"] in buff_name
                    and personal_equip_dict["equip_set2_a"]
                    not in self.__special_set2_dict
                ):
                    """
                    如果检测到装备者选择配装风格是4+2，并且装备者二件套的名字出现在Buff名中，
                    就说明是出现了“只佩戴了二件套但是错误地筛选出了四件套的情况”，
                    此时能够进入这一分支的情况有两种：
                    1、二件套确实附带了一个Buff——如影2，那么这个Buff就一定在__selector的豁免名单中。
                    2、二件套并未附带Buff，但是因为和四件套拥有相同的buff_from，所以错误地进入了这个分支，需要处理的，也正是这个分支。
                    """
                    return
            elif personal_equip_dict["equip_style"] == "2+2+2":
                """当配装方案是2+2+2时，只要当前任意的二件套处于豁免范围，"""
                if "四件套" in buff_name:
                    return
                """筛除所有和豁免名单无关的套装，无论4、2件套；然后再筛除不在豁免名单上的二件套Buff"""
                if not (
                    buff_from in self.__special_set2_dict
                    and buff_name in self.__special_set2_dict[buff_from]
                ):
                    return
            selected_characters = [
                current_name_box[i]
                for i in range(len(current_name_box))
                if adding_code[i] == "1"
            ]
            if equipment_carrier not in selected_characters:
                selected_characters.append(equipment_carrier)
            for _name in selected_characters:
                self.initiate_buff(buff_info_tuple, buff_name, _name, equipment_carrier)


def change_name_box(name_box):
    """
    生成每个角色对应的namebox列表，以自己作为第0位角色
    """
    output_name_dict = {}
    for i in range(len(name_box)):
        new_name_box = name_box[i:] + name_box[:i]
        output_name_dict[name_box[i]] = new_name_box + ["enemy"]
    return output_name_dict
