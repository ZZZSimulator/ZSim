from typing import TYPE_CHECKING

from zsim.sim_progress.data_struct import SingleHit

if TYPE_CHECKING:
    from zsim.sim_progress.Enemy import Enemy


class QETDataUpdater:
    @classmethod
    def apply(cls, qte_data, single_qte, attr_name):
        raise NotImplementedError


class SumStrategy(QETDataUpdater):
    """数值累加策略"""

    @classmethod
    def apply(cls, qte_data, single_qte, attr_name):
        single_qte_value = getattr(single_qte, attr_name, 0) or 0
        qte_data_value = getattr(qte_data, attr_name, 0) or 0
        setattr(qte_data, attr_name, single_qte_value + qte_data_value)


class ListMergeStrategy(QETDataUpdater):
    """列表合并策略"""

    @classmethod
    def apply(cls, qte_data, single_qte, attr_name):
        single_qte_value = getattr(single_qte, attr_name, []) or []
        qte_data_value = getattr(qte_data, attr_name, []) or []
        setattr(qte_data, attr_name, qte_data_value + single_qte_value)


class QTEData:
    def __init__(self, enemy_instance):
        """这个数据结构是管理怪物的QTE的总体数据的，它会随着Enemy类的初始化而一同初始化。
        其中的动态数据（比如qte_received_box qte_triggered_times等，会在每次进入失衡期之前进行重置。"""
        self.enemy_instance: "Enemy" = enemy_instance  # 在初始化时，传入Enemy实例；
        self.qte_received_box: list[str] = []  # 用于接受QTE阶段输入的QTE skill_tag
        self.qte_triggered_times: int = 0  # 已经触发过几次QTE了
        self.qte_triggerable_times: int | None = (
            enemy_instance.QTE_triggerable_times
        )  # 最多可以触发几次QTE
        self.qte_activation_available = False  # 彩色失衡阶段——在StunJudge中被打开，在SingeQTE的merge方法中被关闭，当然，失衡阶段的结束也会关闭该参数（依旧是StunJudge）。
        self.single_qte = None  # 单次QTE的实例
        self.__single_hit_check = (
            lambda hit: all(
                [
                    hit.hitted_count == 1
                    or hit.heavy_hit  # 第一跳、重击（通常为重攻击标签的最后一跳）均能通过判定，
                    # hit.proactive or (not hit.proactive and 'QTE' in hit.skill_tag),  # 筛选出主动技能，所有的被动释放的技能都不能和QTE的激活行为进行互动。
                ]
            )
        )
        self.strategies_map = {
            "qte_received_box": ListMergeStrategy,
            "qte_triggered_times": SumStrategy,
        }
        self.preload_data = None

    def check_myself(self, single_hit: SingleHit = None) -> bool:
        """该函数用于检查自身目前的状态，即当前是彩色失衡还是灰色失衡；"""
        if self.qte_triggered_times > self.qte_triggerable_times:
            raise ValueError(
                f"QTE的实际响应总次数为{self.qte_triggered_times}次，大于其最大次数{self.qte_triggerable_times}次！"
            )
        if len(self.qte_received_box) > self.qte_triggered_times:
            raise ValueError(
                f"QTE总计包含了{len(self.qte_received_box)}个skill_tag，而实际的响应次数为{self.qte_triggered_times}次！"
            )
        if self.enemy_instance.dynamic.stun:
            if self.qte_triggered_times < self.qte_triggerable_times:
                return True
            else:
                self.qte_activation_available = False
                return False
        else:
            """
            v0.3.1b2更新：
            为了复现柚叶2画在非失衡期也能激发一次连携技的机制，
            所以为single_hit以及skill_node添加了一个新参数——force_qte_trigger（强制激发QTE）
            该参数可以让QTE管理器在非失衡期放行这个single_hit，并且使其顺利进入后续的判定。
            后续更新：
            QTE结构仅需要针对两种情况进行特殊放行：
            1、在非失衡期能够激发连携的skill_node——force_qte_trigger==True
            2、在非失衡期激发连携后，进行响应的QTE技能；
            """
            if self.single_qte is None:
                if single_hit is not None:
                    if single_hit.force_qte_trigger:
                        return True
            else:
                if single_hit is not None:
                    if single_hit.skill_node.skill.trigger_buff_level == 5:
                        return True
            return False

    def try_qte(self, hit: SingleHit) -> None:
        """
        该函数是QTEData的最外层接口，是核心调用函数。
        其核心作用为：用传入的SingleHit来尝试激发QTE。
        """
        # 0、 如果是非失衡状态或是灰色失衡状态，那么直接返回
        if not self.check_myself(single_hit=hit):
            return

        # 1、可行性审查，这里，只有主动动作的第一跳、以及含有重击标签的、主动动作的最后一跳能够通过判定。
        if not self.single_hit_filter(hit):
            return

        # 2、是否存在已经激活的SingleQTE实例——连携阶段已经因重攻击而激发、SingleQTE实例也已经创建，但是尚未传入SingleHit的状态
        if self.single_qte is not None:
            if not isinstance(self.single_qte, SingleQTE):
                raise TypeError(
                    f"QTEData的single_qte属性不是SingleQTE类！你往里放入了{type(self.single_qte)}！"
                )
            # 2.1、尝试将已经通过可行性检查的SingleHit传入到SingleQTE中，进行数据更新，
            self.single_qte.receive_hit(hit)
            # print(f'{hit.skill_tag}响应了本次连携技触发！')
        else:
            # 3、如果SingleQTE实例不存在，那么要对传入的SingHit进行判断；
            if self.qte_active_selector(hit):
                # 3.1、如果是能够激发连携的hit，而此时又没有SingleHit存在，那么就是激活了新的QTE阶段，进入下一步判断。
                self.single_qte = SingleQTE(self, single_hit=hit)
                self.enemy_instance.sim_instance.schedule_data.change_process_state()
                print(
                    f"{hit.skill_node.char_name}  的  {hit.skill_node.skill.skill_text}  激发了连携技！当前已经激发过{self.qte_triggered_times + 1}次连携技！"
                )
            else:
                """
                如果不是重攻击，那就只能是某技能的第一跳。
                很明显，在SingleHit并未被创建的时候，技能的第一跳并不能激发连携状态。所以这个分支什么都不做（暂时）
                这个分枝往往发生在：怪物已经失衡，但是重攻击标签还未传入时，可能是前台切人合轴了，也可能是角色的APL本来就不打连携技。
                此时，下一个循环，函数就会触发隔壁分枝，因为有一个SingleQTE是待传入状态，
                """
                # print(f'虽然是彩色失衡状态，但是没有进行响应')
                return

    def single_hit_filter(self, hit: SingleHit):
        """
        该函数用于对传入的SingleHit进行筛选，并返回筛选结果。
        """
        return self.__single_hit_check(hit)

    def reset(self):
        """该函数用于在失衡期开始时的重置QTEdata中的动态数据"""
        self.qte_received_box = []
        self.qte_triggered_times = 0
        self.qte_activation_available = True
        self.single_qte = None

    def restore(self):
        self.qte_received_box = []
        self.qte_triggered_times = 0
        self.qte_activation_available = False
        self.single_qte = None

    def spawn_single_qte(self):
        pass

    def qte_active_selector(self, _hit: SingleHit) -> bool:
        """
        这个函数筛选的是真正能激发QTE的技能，这种技能有两个条件：
        1、重攻击Hit——含有重攻击标签（“heavy_attack”）的技能的最后一跳
        2、函数接收到这个hit信号的同时，角色正处于被操作状态下
            （解释一下，这里为什么不用“前台”属性来进行判断：因为绝区零已经存在多名角色同时处于前台的情况，
            所以这个“前台”的说法并不准确，但是无论如何，玩家操纵的角色始终只有一名，
            所以“角色正处于被操作状态下”才是更准确的描述。）
        """
        if not _hit.heavy_hit:
            return False
        if self.preload_data is None:
            self.preload_data = self.enemy_instance.sim_instance.preload.preload_data
        from zsim.sim_progress.Preload.PreloadDataClass import PreloadData

        if not isinstance(self.preload_data, PreloadData):
            raise TypeError("QTEData的preload_data属性不是PreloadData类！")
        if not self.enemy_instance.dynamic.stun and _hit.skill_node.force_qte_trigger:
            # FIXME: 临时解决方案，理论上2画触发连携技需要柚叶在前台，合轴会导致激发失败；
            #  但是这涉及到的底层逻辑较为复杂，APL也不太好改，所以这里暂时先这么临时解决一下
            return True
        if self.preload_data.operating_now is None:
            """说明目前没有任何角色在前台"""
            return False
        else:
            return int(_hit.skill_tag.split("_")[0]) == self.preload_data.operating_now


class SingleQTE:
    def __init__(self, qte_data: QTEData, single_hit: SingleHit):
        self.qte_data = qte_data
        self.qte_received_box: list[str] = []  # 用于接受QTE阶段输入的QTE skill_tag
        self.qte_triggerable_times: int = (
            self.qte_data.qte_triggerable_times
        )  # 最多可以触发几次QTE
        self.qte_triggered_times: int = 0  # 已经响应了几次QTE
        self.qte_activation_available = False  # 彩色失衡阶段
        self.__is_hitted = False  # 每个SingleHit都只会被响应一次，所以这里用一个bool变量来标记是否已经被响应过。
        self.active_by: SingleHit = single_hit

    def receive_hit(self, _single_hit: SingleHit):
        """SingleQTE接收SingleHit的方法"""
        if self.__is_hitted:
            raise ValueError(
                "SingleQTE实例已经响应过一次了！请检查函数逻辑，查找为何处会多次调用同一个SingleQTE的_receive_hit函数！"
            )
        if not isinstance(_single_hit, SingleHit):
            raise TypeError(
                f"SingleQTE实例的_receive_hit函数被调用时，传入的single_hit参数不是SingleHit类！而是{type(_single_hit)}！"
            )
        if _single_hit.hitted_count != 1:  # 如果传进来的不是第一跳，那直接return
            return
        if not _single_hit.proactive:  # 如果传进来的是一个非主动动作，也直接return
            return
        if self.qte_data.enemy_instance.dynamic.stun:
            """正常的QTE接收逻辑"""
            self.receive_hit_while_stun(_single_hit)
        else:
            """非失衡阶段的QTE接收逻辑（强制触发的QTE）"""
            self.receive_qte_without_stun(_single_hit)


    def receive_hit_while_stun(self, _single_hit: SingleHit):
        """失衡期接收QTE的业务逻辑"""
        self.qte_triggered_times += 1
        if "QTE" not in _single_hit.skill_tag:
            """说明QTE被取消了"""
            self.qte_data.enemy_instance.sim_instance.schedule_data.change_process_state()
            print(
                f"【QTE事件】{_single_hit.skill_node.char_name}  取消第{self.qte_data.qte_triggered_times + 1}次QTE，并释放了  {_single_hit.skill_node.skill.skill_text}  "
            )
        else:
            """角色响应了QTE，释放连携技"""
            if _single_hit.skill_node.char_name == self.active_by.skill_node.char_name:
                raise ValueError(
                    f"{_single_hit.skill_node.char_name}  企图响应自己激发的QTE！"
                )
            self.qte_received_box.append(_single_hit.skill_tag)

            """QTE成功响应之后，返还1秒QTE时间"""
            self.qte_data.enemy_instance.sim_instance.schedule_data.change_process_state()
            self.qte_data.enemy_instance.dynamic.stun_tick_feed_back_from_QTE += 60
            print(
                f"【QTE事件】 {_single_hit.skill_node.char_name}  响应了连携，释放连携技（skill_tag为{_single_hit.skill_tag})，返还1秒失衡时间！"
            )
        self.__is_hitted = True
        self.merge_single_qte()

    def merge_single_qte(self):
        """SingleQTE向QTEData更新数据的方法"""
        for attr_name, strategy in self.qte_data.strategies_map.items():
            if hasattr(self, attr_name):
                strategy.apply(self.qte_data, self, attr_name)
        self.qte_data.single_qte = None
        self.qte_data.check_myself()

    def receive_qte_without_stun(self, _single_hit: SingleHit):
        """在非失衡阶段接收hit"""
        if "QTE" not in _single_hit.skill_tag:
            """说明QTE被取消了"""
            self.qte_data.enemy_instance.sim_instance.schedule_data.change_process_state()
            print(
                f"【QTE事件】{_single_hit.skill_node.char_name}  取消了强制触发的QTE，并释放了  {_single_hit.skill_node.skill.skill_text}  "
            )
        else:
            """角色响应了QTE，释放连携技"""
            if _single_hit.skill_node.char_name == self.active_by.skill_node.char_name and not self.active_by.skill_node.force_qte_trigger:
                raise ValueError(
                    f"{_single_hit.skill_node.char_name}  企图响应自己激发的QTE！"
                )
                # FIXME：由于柚叶2画有强行在非失衡期触发连携技的特性，为了系统稳定暂时让这个激发在后台也能生效。
                #  所以这里的验错也需要避开这个情况，否则就会报“自己响应自己QTE”的错误
            self.qte_data.enemy_instance.sim_instance.schedule_data.change_process_state()
            print(
                f"【QTE事件】 {_single_hit.skill_node.char_name}  响应了强制触发的连携，释放连携技 {_single_hit.skill_node.skill.skill_text}（skill_tag为{_single_hit.skill_tag})"
            )
        self.__is_hitted = True
        self.merge_single_qte()

