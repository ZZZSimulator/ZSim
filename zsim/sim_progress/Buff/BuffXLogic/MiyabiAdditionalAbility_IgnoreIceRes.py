from .. import Buff, JudgeTools, check_preparation

anomaly_name_list = ["frostbite", "assault", "shock", "burn", "corruption"]


class MiyabiAdditionalAbility:
    def __init__(self):
        self.anomaly_state = {name: False for name in anomaly_name_list}
        self.disorder = False
        self.effect_count = 0
        self.action_stack = None
        self.enemy = None


class MiyabiAdditionalAbility_IgnoreIceRes(Buff.BuffLogic):
    """
    该buff为雅的组队被动中，紊乱后蓄力重击无视冰抗，
    该Buff需要检测紊乱，这一判定必须对比：当前tick下enemy的状态  和  本buff逻辑模块内记录的上一次判定过程中的enemy状态，

    重点在于，必须保证当前tick和上一次记录的tick只相差1，这样才不会误判紊乱的发生。
    主要需要规避的情况：
    1、第n个ticks检测到霜寒，
    2、n+1ticks 时，角色被切到后台了，
    3、第n+x个ticks的时候，角色重新回到前台，并且检测到灼烧，
    那么这里就会自然而然判定为“disorder”，这是误判。

    由于紊乱的产生只有1个tick，要准确检测到紊乱，必须每个tick实时获取enemy的状态，
    所以，该buff必须每个tick都被执行一次判定逻辑，
    我修改了buff的backend_active参数，这样，雅在前台时，它能通过Load的主逻辑进行判断
    而角色在后台时，也可以通过Load的副逻辑，passively_updating == True且backend_active == True的分支，来执行判断。

    检测到紊乱发生后，buff的生效次数 effect_count 自增1，最多1层，
    只有当effect_count 的层数是1，且当前的动作（action_stack.peek()获取）
    """

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xjudge = self.special_judge_logic
        self.buff_0 = None
        self.record = None

    def get_prepared(self, **kwargs):
        return check_preparation(buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs)

    def check_record_module(self):
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )["雅"][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = MiyabiAdditionalAbility()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(enemy=1, action_stack=1)

        action_now = self.record.action_stack.peek()
        enemy = self.record.enemy

        current_anomalies = {name: getattr(enemy.dynamic, name) for name in anomaly_name_list}
        # 获取当前状态
        current_count = sum(current_anomalies.values())
        last_count = sum(self.record.anomaly_state.values())
        # 计算两个list中的True的数量

        if last_count >= 2 or current_count >= 2:
            raise ValueError("当前ticks总异常数量为2！")

        self.record.disorder = (
            current_count == 1
            and last_count == 1
            and any(
                current_anomalies[name] != self.record.anomaly_state[name]
                for name in anomaly_name_list
            )
        )
        # 当前后的True的数量都是1（意味着上一个Ticks有异常，这个Ticks也有异常），判断二者是否是同一个异常。如果不是，就修改Disorder为True
        self.record.anomaly_state.update(current_anomalies)

        if self.record.disorder:
            self.record.effect_count = min(self.record.effect_count + 1, 1)
        if self.record.effect_count > 0 and action_now.mission_tag in [
            "1091_SNA_1",
            "1091_SNA_2",
            "1091_SNA_3",
        ]:
            self.record.effect_count = 0
            return True
        return False
