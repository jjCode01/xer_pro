from collections import defaultdict
from itertools import groupby
from data.schedule import Schedule
from data.logic import Relationship
from data.task import Task


def get_duplicate_names(tasks: list[Task]) -> list[tuple[Task]]:
    def sort_key(task: Task):
        return task.name

    groupby_name = groupby(
        sorted(tasks, key=sort_key), sort_key)

    duplicate_names = [
        sorted(tasks, key=lambda t: t.activity_id)
        for _, group in groupby_name
        if len(tasks := tuple(group)) > 1]

    return sorted(duplicate_names, key=lambda t: t[0].name)


def get_duplicate_logic(logic: list[Relationship]) -> list[tuple[Relationship]]:
    def sort_key(rel: Relationship):
        return (rel.predecessor.activity_id, rel.successor.activity_id)

    groupby_pred_succ = groupby(
        sorted(logic, key=sort_key), sort_key)

    duplicate_logic = set()
    for _, group in groupby_pred_succ:
        if len(rels := tuple(group)) > 1:
            for rel in rels:
                if rel.link in ('FS', 'SF'):
                    duplicate_logic.add(rels)

    return sorted(
        list(duplicate_logic),
        key=lambda r: (r[0].predecessor.activity_id, r[0].successor.activity_id))


def get_redundant_logic(logic: list[Relationship]) -> list[Relationship]:
    def sort_pred(rel: Relationship):
        return rel.predecessor.activity_id

    def sort_succ(rel: Relationship):
        return rel.successor.activity_id

    redundant_logic = set()

    groupby_predecessor = {
        key: list(group)
        for key, group in groupby(
            sorted(logic, key=sort_pred),
            lambda rel: rel.predecessor)}

    groupby_successor = {
        key: list(group)
        for key, group in groupby(
            sorted(logic, key=sort_succ),
            lambda rel: rel.successor)}

    def _check_logic(epoch_relationship: Relationship, relationship: Relationship):
        for pred_rel in groupby_successor.get(relationship.successor, []):
            if pred_rel.predecessor == epoch_relationship.predecessor:
                redundant_logic.add(pred_rel)

        next_relationships = groupby_predecessor.get(relationship.successor, [])
        for succ_rel in next_relationships:
            if succ_rel in rel_cache:
                return

            rel_cache.add(succ_rel)
            _check_logic(epoch_relationship, succ_rel)

        return

    for relationships in groupby_predecessor.values():
        if len(relationships) <= 1:
            continue
        rel_cache = set()
        for relationship in relationships:
            for next_relationship in groupby_predecessor.get(relationship.successor, []):
                rel_cache.add(next_relationship)
                _check_logic(relationship, next_relationship)

    return sorted(
        list(redundant_logic),
        key=lambda r: [r.predecessor.activity_id, r.successor.activity_id])


def get_open_ends(schedule: Schedule) -> dict[str, list[Task]]:
    open_ends = defaultdict(list)
    groupby_predecessor = {
        key: list(group)
        for key, group in groupby(
            schedule.logic(),
            lambda x: x.predecessor)}

    groupby_successor = {
        key: list(group)
        for key, group in groupby(
            schedule.logic(),
            lambda x: x.successor)}

    for task in schedule.tasks():
        if task not in groupby_predecessor:
            open_ends['open_successor'].append(task)
        else:
            for rel in groupby_predecessor.get(task):
                if rel.lag in ('FS', 'FF'):
                    break
            else:
                open_ends['open_finish'].append(task)

        if task not in groupby_successor:
            open_ends['open_predecessor'].append(task)
        else:
            for rel in groupby_successor.get(task):
                if rel.lag in ('FS', 'FF'):
                    break
            else:
                open_ends['open_finish'].append(task)

    return open_ends


def get_schedule_warnings(schedule: Schedule, other_schedule: Schedule) -> dict[str, dict]:
    warnings = defaultdict(set)
    warnings['duplicate_names'] = get_duplicate_names(schedule.tasks())
    warnings['duplicate_logic'] = get_duplicate_logic(schedule.logic())
    warnings['redundant_logic'] = get_redundant_logic(schedule.logic())
    warnings.update(get_open_ends(schedule))

    return warnings
