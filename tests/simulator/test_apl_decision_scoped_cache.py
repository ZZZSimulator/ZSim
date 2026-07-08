from types import SimpleNamespace

from zsim.sim_progress.Preload.apl_unit.ActionAPLUnit import ActionAPLUnit
from zsim.sim_progress.Preload.apl_unit.APLUnit import ExprNode
from zsim.sim_progress.Preload.APLModule.APLOperator import APLOperator
from zsim.sim_progress.Preload.APLModule.SubConditionUnit import BaseSubConditionUnit


class RecordingCondition(BaseSubConditionUnit):
    def __init__(self, name: str, values):
        self.name = name
        self.decision_cache_identity = object()
        self.values = list(values)
        self.calls = []

    def check_myself(self, found_char_dict, game_state, sim_instance=None, *args, **kwargs):
        tick = kwargs.get("tick")
        self.calls.append(tick)
        index = min(len(self.calls) - 1, len(self.values) - 1)
        value = self.values[index]
        return value() if callable(value) else value


class ExplodingCondition(BaseSubConditionUnit):
    def __init__(self, name: str):
        self.name = name
        self.decision_cache_identity = object()

    def check_myself(self, found_char_dict, game_state, sim_instance=None, *args, **kwargs):
        raise AssertionError(f"{self.name} should have been short-circuited")


class RecordingQTEManager:
    def __init__(self, allowed: bool):
        self.allowed = allowed
        self.checked_tags = []

    def check_qte_legality(self, qte_skill_tag: str):
        self.checked_tags.append(qte_skill_tag)
        return self.allowed


def _leaf(condition: BaseSubConditionUnit) -> ExprNode:
    return ExprNode(sub_condition=condition)


def _branch(operator: str, left: ExprNode, right: ExprNode) -> ExprNode:
    return ExprNode(operator=operator, left=left, right=right)


def _sim(qte_allowed: bool = True) -> SimpleNamespace:
    qte_manager = RecordingQTEManager(allowed=qte_allowed)
    enemy = SimpleNamespace(qte_manager=qte_manager)
    schedule_data = SimpleNamespace(enemy=enemy)
    return SimpleNamespace(schedule_data=schedule_data)


def _action_unit(
    *,
    sim_instance,
    priority: int,
    action: str,
    tree: ExprNode | None,
    cid: int = 1311,
) -> ActionAPLUnit:
    unit = ActionAPLUnit(
        {
            "CID": cid,
            "priority": priority,
            "type": "action+=",
            "action": action,
            "conditions": [],
            "conditions_tree": None,
        },
        sim_instance=sim_instance,
    )
    if tree is not None:
        unit.sub_conditions_ast = tree
        unit.sub_conditions_unit_list = _conditions_from_tree(tree)
    return unit


def _conditions_from_tree(node: ExprNode) -> list[BaseSubConditionUnit]:
    if node.is_leaf():
        return [node.sub_condition]
    return [*_conditions_from_tree(node.left), *_conditions_from_tree(node.right)]


def _operator(sim_instance, *units: ActionAPLUnit) -> APLOperator:
    preload_data = SimpleNamespace(atk_manager=SimpleNamespace(attacking=False))
    operator = APLOperator(
        all_apl_unit_list=[],
        game_state={},
        preload_data=preload_data,
        simulator_instance=sim_instance,
    )
    operator.apl_unit_inventory = {unit.priority: unit for unit in units}
    operator._common_apl_units = tuple((unit.priority, unit) for unit in units)
    return operator


def test_same_decision_allows_reusing_repeated_leaf_result_without_changing_action():
    sim = _sim()
    repeated_leaf = RecordingCondition("same-leaf", [True, True])
    unit = _action_unit(
        sim_instance=sim,
        priority=1,
        action="1311_NA",
        tree=_branch("and", _leaf(repeated_leaf), _leaf(repeated_leaf)),
    )

    selected_cid, selected_action, selected_priority, selected_unit = _operator(
        sim, unit
    ).spawn_next_action_in_common_mode(tick=100)

    assert (selected_cid, selected_action, selected_priority, selected_unit) == (
        1311,
        "1311_NA",
        1,
        unit,
    )
    assert repeated_leaf.calls == [100]


def test_decision_cache_must_preserve_and_or_short_circuit_behavior():
    sim = _sim()
    false_left = RecordingCondition("false-left", [False])
    and_unit = _action_unit(
        sim_instance=sim,
        priority=1,
        action="1311_NA",
        tree=_branch("and", _leaf(false_left), _leaf(ExplodingCondition("and-right"))),
    )
    true_left = RecordingCondition("true-left", [True])
    or_unit = _action_unit(
        sim_instance=sim,
        priority=2,
        action="1311_EX",
        tree=_branch("or", _leaf(true_left), _leaf(ExplodingCondition("or-right"))),
    )

    selected = _operator(sim, and_unit, or_unit).spawn_next_action_in_common_mode(tick=120)

    assert selected[:3] == (1311, "1311_EX", 2)
    assert false_left.calls == [120]
    assert true_left.calls == [120]


def test_qte_legality_is_checked_after_reachable_condition_tree_success():
    sim = _sim(qte_allowed=False)
    qte_condition = RecordingCondition("qte-condition", [True])
    qte_unit = _action_unit(
        sim_instance=sim,
        priority=1,
        action="1311_QTE",
        tree=_leaf(qte_condition),
    )
    fallback_unit = _action_unit(
        sim_instance=sim,
        priority=2,
        action="1311_NA",
        tree=_leaf(RecordingCondition("fallback", [True])),
    )

    selected = _operator(sim, qte_unit, fallback_unit).spawn_next_action_in_common_mode(tick=140)

    assert selected[:3] == (1311, "1311_NA", 2)
    assert qte_condition.calls == [140]
    assert sim.schedule_data.enemy.qte_manager.checked_tags == ["1311_QTE"]


def test_separate_decisions_at_same_tick_do_not_reuse_stale_leaf_result():
    sim = _sim()
    state = {"ready": True}
    stateful_condition = RecordingCondition("stateful", [lambda: state["ready"]])
    stateful_unit = _action_unit(
        sim_instance=sim,
        priority=1,
        action="1311_EX",
        tree=_leaf(stateful_condition),
    )
    fallback_unit = _action_unit(
        sim_instance=sim,
        priority=2,
        action="1311_NA",
        tree=_leaf(RecordingCondition("fallback", [True])),
    )
    operator = _operator(sim, stateful_unit, fallback_unit)

    first_selected = operator.spawn_next_action_in_common_mode(tick=160)
    state["ready"] = False
    second_selected = operator.spawn_next_action_in_common_mode(tick=160)

    assert first_selected[:3] == (1311, "1311_EX", 1)
    assert second_selected[:3] == (1311, "1311_NA", 2)
    assert stateful_condition.calls == [160, 160]
