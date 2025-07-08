from zsim.sim_progress import Load, Preload
from zsim.sim_progress.data_struct import ActionStack


def SkillEventSplit(
    preloaded_action_list: list,
    Load_mission_dict: dict,
    name_dict: dict,
    timenow,
    action_stack: ActionStack,
):
    # 新增新的loading mission
    for i in range(len(preloaded_action_list)):
        skill = preloaded_action_list.pop()
        if not isinstance(skill, Preload.SkillNode):
            raise ValueError(f"本次拆分的{type(skill)}不是SkillNode类！")
        this_mission = Load.LoadingMission(skill)
        this_mission.mission_start(timenow)
        action_stack.push(this_mission)
        if skill.skill_tag in name_dict:
            name_dict[skill.skill_tag] += 1
        else:
            name_dict[skill.skill_tag] = 1
        key = skill.skill_tag + f"[{name_dict[skill.skill_tag]}]"
        Load_mission_dict[key] = this_mission
    return Load_mission_dict


if __name__ == "__main__":  # 测试
    import tqdm

    timelimit = 3600
    load_mission_dict = {}
    p = Preload.Preload()
    name_dict = {}
    for tick in tqdm.trange(timelimit):
        p.do_preload(tick)
        preload_action_list = p.preload_data.preloaded_action
        if not preload_action_list:
            continue
        SkillEventSplit(preload_action_list, load_mission_dict, name_dict)
    for item in load_mission_dict:
        print(f"{item}, {load_mission_dict[item].mission_character_number}")

# TODO: 将SkillEventSplit中，对于load_mission_dict的维护部分单独拆分，并且每个ticks查询，如果当前有hit子任务，则直接向schedule_event_list添加对应的SkillNode
