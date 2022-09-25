from collections import defaultdict
from itertools import groupby
from xer_pro.data.schedule import Schedule
from xer_pro.data.logic import Relationship
from xer_pro.data.task import Task
from xer_pro.data.resource import TaskResource
from xer_pro.services.task_services import is_construction_task


def get_duplicate_names(tasks: list[Task]) -> list[tuple[Task]]:
    def sort_key(task: Task):
        return task.name

    groupby_name = groupby(sorted(tasks, key=sort_key), sort_key)
    duplicate_names = [
        sorted(tasks, key=lambda t: t.activity_id)
        for _, group in groupby_name
        if len(tasks := tuple(group)) > 1
    ]

    return sorted(duplicate_names, key=lambda t: t[0].name)


def _sort_pred(rel: Relationship):
    return (rel.predecessor.activity_id, rel.successor.activity_id)


def _sort_succ(rel: Relationship):
    return (rel.successor.activity_id, rel.predecessor.activity_id)


def get_duplicate_logic(logic: list[Relationship]) -> list[tuple[Relationship]]:
    groupby_pred_succ = groupby(sorted(logic, key=_sort_pred), _sort_pred)

    duplicate_logic = list()
    for _, group in groupby_pred_succ:
        if len(rels := tuple(group)) > 1:
            for rel in rels:
                if rel.link in ("FS", "SF"):
                    duplicate_logic.append(rels)
                    break

    return sorted(
        duplicate_logic,
        key=lambda r: (r[0].predecessor.activity_id, r[0].successor.activity_id),
    )


class RedundantLogic:
    def __init__(
        self,
        epoch_relationship: Relationship,
        redundant_relationship: Relationship,
        level: int,
    ) -> None:
        self.epoch = epoch_relationship
        self.redundant = redundant_relationship
        self.level = level

    def __eq__(self, __o: object) -> bool:
        return self.redundant == __o.redundant and self.epoch == __o.epoch

    def __hash__(self) -> int:
        return hash((self.redundant, self.epoch))


def get_redundant_logic(logic: list[Relationship]) -> list[Relationship]:
    def check_logic(
        epoch_relationship: Relationship, relationship: Relationship, level: int
    ):
        for pred_rel in groupby_successor.get(relationship.successor, []):
            if pred_rel.predecessor == epoch_relationship.predecessor and (
                epoch_relationship.link == pred_rel.link
                or epoch_relationship.link in ("FS", "FF")
            ):
                redundant_cache.add(pred_rel)
                redundant[epoch_relationship].add(
                    RedundantLogic(epoch_relationship, pred_rel, level)
                )
                continue

        next_relationships = groupby_predecessor.get(relationship.successor, [])
        for succ_rel in next_relationships:
            if succ_rel in rel_cache:
                continue

            rel_cache.add(succ_rel)
            logic_list.append(succ_rel)
            check_logic(epoch_relationship, succ_rel, level + 1)

    redundant = defaultdict(set)
    redundant_cache = set()
    groupby_predecessor = {
        key: list(group)
        for key, group in groupby(
            sorted(logic, key=_sort_pred), lambda rel: rel.predecessor
        )
    }

    groupby_successor = {
        key: list(group)
        for key, group in groupby(
            sorted(logic, key=_sort_succ), lambda rel: rel.successor
        )
    }

    for relationships in groupby_predecessor.values():
        if len(list(filter(lambda r: not r.successor.is_loe, relationships))) <= 1:
            continue
        rel_cache = set()
        logic_list = list()
        for relationship in relationships:
            if relationship.successor.is_loe:
                continue
            for next_relationship in groupby_predecessor.get(
                relationship.successor, []
            ):
                rel_cache.add(next_relationship)
                logic_list.append(relationship)
                logic_list.append(next_relationship)
                check_logic(relationship, next_relationship, 1)

    return {key: val for key, val in redundant.items() if key not in redundant_cache}


def get_open_ends(schedule: Schedule) -> dict[str, list[Task]]:
    open_ends = defaultdict(list)
    groupby_predecessor = {
        key: list(group)
        for key, group in groupby(
            sorted(schedule.logic(), key=_sort_pred), lambda rel: rel.predecessor
        )
    }

    groupby_successor = {
        key: list(group)
        for key, group in groupby(
            sorted(schedule.logic(), key=_sort_succ), lambda rel: rel.successor
        )
    }

    for task in schedule.tasks():
        if task not in groupby_predecessor:
            open_ends["open_successor"].append(task)
        else:
            for rel in groupby_predecessor.get(task):
                if rel.link in ("FS", "FF"):
                    break
            else:
                open_ends["open_finish"].append(task)

        if task not in groupby_successor:
            open_ends["open_predecessor"].append(task)
        else:
            for rel in groupby_successor.get(task):
                if rel.link in ("FS", "SS"):
                    break
            else:
                open_ends["open_start"].append(task)

    return open_ends


def get_lag_warnings(logic: list[Relationship]) -> list[Relationship]:
    lag_warnings = defaultdict(list)
    for rel in logic:
        if rel.lag < 0:
            lag_warnings["negative_lag"].append(rel)
        elif rel.lag > 10:
            lag_warnings["long_lag"].append(rel)

        if rel.link == "FS" and rel.lag > 0:
            lag_warnings["fs_lag"].append(rel)

        if rel.link == "SS" and rel.lag >= rel.predecessor.original_duration:
            lag_warnings["false_lag"].append(rel)
        elif rel.link == "FF" and rel.lag >= rel.successor.original_duration:
            lag_warnings["false_lag"].append(rel)

    return lag_warnings


def get_cost_warnings(resources: list[TaskResource]) -> list[TaskResource]:
    cost_warnings = defaultdict(list)
    for res in resources:
        if res.cost.variance != 0:
            cost_warnings["cost_variance"].append(res)

        if round(res.cost.actual, 2) != round(res.earned_value, 2):
            cost_warnings["ev_variance"].append(res)

    return cost_warnings


def get_schedule_warnings(
    schedule: Schedule, other_schedule: Schedule
) -> dict[str, dict]:
    warnings = defaultdict(set)
    warnings["duplicate_names"] = get_duplicate_names(schedule.tasks())
    warnings["duplicate_logic"] = get_duplicate_logic(schedule.logic())
    warnings["redundant_logic"] = get_redundant_logic(schedule.logic())
    warnings.update(get_open_ends(schedule))
    warnings.update(get_lag_warnings(schedule.logic()))
    warnings["sf_logic"] = [rel for rel in schedule.logic() if rel.link == "SF"]
    warnings.update(get_cost_warnings(schedule.resources))
    warnings["long_durations"] = [
        task
        for task in schedule.tasks()
        if task.original_duration > 20
        and not task.is_loe
        and is_construction_task(task)
    ]

    return warnings
