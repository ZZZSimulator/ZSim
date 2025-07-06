from .buff_class import Buff


def buff_add(timenow: float, LOADING_BUFF_DICT: dict, DYNAMIC_BUFF_DICT: dict, enemy):
    """
    该函数是Buff三部曲中的最后一步。
    它负责把LOADING_BUFF_DICT中的待加载的buff添加到对应角色的Dynamic_Buff_List中，
    由于load阶段存在一个小漏洞，导致当前动作中，一些因hit激活的buff，会在start节点漏进来:
    前提：LOAD阶段的这个漏洞系底层逻辑缺陷，无法在LOAD阶段自己解决，只能后面的程序进行找补。
        Bug成因：
        原因是在start那个ticks的BuffLoadLoop函数会因为主要参数对比全部通过，放行这个本不该在start标签处触发的buff。
        举例：
            这个Buff是普攻触发，那么普攻的第一帧（start)，虽然还没有hit，但确实是“正在进行普攻”状态，那么这个buff就是会通过判断。
        该buff会顺利进入LOADING_BUFF_DICT从而被ADD函数无脑执行，添加进DYNAMIC_BUFF_DICT中。
        但是每个buff在添加进DYNAMIC之前，都要执行buff.update方法来更新自身的动态信息（幸亏我当时很菜，把buff实例化和更新信息分开写了！！）
        而该buff会因为当前子任务是start而被归入start分支，从而执行update_cause_start函数，
        但是该buff本身是hit更新类型，所以无法进入start函数的任意一个分支，也就无法获得时间等动态信息的有效更新。
        也就是说，BuffLoadLoop会放行一些buff，这些buff会被实例化，但是时间、层数等完全不会更新，全部是0，actrive状态也是False。
        在下一个tick，这些buff会因为自身endticks小于当前tick，而被Update_Buff函数扫出DYNAMIC_BUFF_DICT
        我记得之前遇到过的“灵异事件”，就是在tick=1的时候，会发现出现了一些没有信息更新的buff，它们漏进了Dynamic_buff_dict，但是在tick=2时消失，也正是因为这个原因。

    虽然这些漏进去的Buff只会存在一个Ticks，但是也很有可能影响当前tick的计算。
    所以，在后续处理DynamicBuffList时，需要schedule阶段多判断一个buff.dy.active 是否是True，如果不是True就不要执行。
    或者，在Buff_Add阶段处理，判断一下active或是buff.dy下面的任意属性是否为0即可。

    所以，LOADING_BUFF_DICT中只会出现本tick该被添加的buff，将所有buff全部add，将容器清空是这个阶段的核心任务。
    所有的buff都会被添加到对应的DYNAMIC_BUFF_DICT中，这样一来，“加buff”这一动作被彻底实现。
    """
    for char in LOADING_BUFF_DICT:
        if not LOADING_BUFF_DICT[char]:
            continue
        for buff in LOADING_BUFF_DICT[char]:
            if not isinstance(buff, Buff):
                raise ValueError(f"loading_buff_dict中的{buff}元素不是Buff类")
            if (
                not buff.dy.active
                or (buff.dy.startticks == 0 and buff.dy.endticks == 0)
                or buff.dy.count == 0
            ):
                # if buff.ft.index == 'Buff-武器-精1燃狱齿轮-叠层冲击力':
                #     print(f'{buff.dy.active, buff.dy.startticks, buff.dy.endticks, buff.dy.count}')
                continue

            buff_existing_check = next(
                (
                    existing_buff
                    for existing_buff in DYNAMIC_BUFF_DICT[char]
                    if existing_buff.ft.index == buff.ft.index
                ),
                None,
            )
            # 这个语句的作用是，检查buff是否已经存在。检查的索引是buff.ft.index。
            if buff_existing_check:
                if buff.ft.alltime:
                    continue
                DYNAMIC_BUFF_DICT[char].remove(buff_existing_check)
                # report_to_log(f'[Buff ADD]:{timenow}:{buff_existing_check.ft.name}刷新了')

            DYNAMIC_BUFF_DICT[char].append(buff)
            add_debuff_to_enemy(buff, char, enemy)
    return DYNAMIC_BUFF_DICT


def add_debuff_to_enemy(buff, char, enemy):
    if char == "enemy":
        debuff_existing_check = next(
            (
                existing_buff
                for existing_buff in enemy.dynamic.dynamic_debuff_list
                if existing_buff.ft.index == buff.ft.index
            ),
            None,
        )
        if debuff_existing_check:
            enemy.dynamic.dynamic_debuff_list.remove(debuff_existing_check)
        enemy.dynamic.dynamic_debuff_list.append(buff)
        # 只有在处理enemy的buff时，需要将改动同时同步到buff中。
        # report_to_log(f'[Buff ADD]:{timenow}:{buff.ft.name}第{buff.history.active_times}次触发:endticks:{buff.dy.endticks}')
