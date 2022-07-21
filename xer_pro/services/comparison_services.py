from collections import defaultdict, Counter
from fuzzywuzzy import fuzz
from data.schedule import Schedule
from data.resource import TaskResource


def get_schedule_changes(schedule: Schedule, other_schedule: Schedule) -> dict[str, list]:
    changes = defaultdict(list)
    changes.update(get_task_changes(schedule, other_schedule))
    changes.update(get_logic_changes(schedule, other_schedule))
    changes.update(get_resource_changes(schedule.resources, other_schedule.resources))
    return changes


def get_task_changes(schedule: Schedule, other_schedule: Schedule) -> dict[str, list]:
    changes = defaultdict(list)
    changes['added_tasks'] = list(set(schedule.tasks()) - set(other_schedule.tasks()))
    changes['deleted_tasks'] = list(set(other_schedule.tasks()) - set(schedule.tasks()))

    other_tasks = {
        t._attr['task_code']: t
        for t in other_schedule.tasks()}

    for task in schedule.tasks():
        if not (other := other_tasks.get(task.activity_id)):
            continue

        if task.name != other.name:
            changes['name'].append((
                task, other,
                fuzz.ratio(task.name, other.name),
                fuzz.partial_ratio(task.name, other.name)))

        if task.original_duration != other.original_duration:
            changes['orig_duration'].append((task, other))

        else:
            if (task.is_not_started and other.is_not_started) and \
                    task.remaining_duration != other.remaining_duration:
                changes['rem_duration'].append((task, other))

        if not other.is_not_started and task.start.date() != other.start.date():
            changes['act_start'].append((task, other))

        if other.is_completed and task.finish.date() != other.finish.date():
            changes['act_finish'].append((task, other))

        if task.calendar != other.calendar:
            changes['act_calendar'].append((task, other))

        task_wbs_string = u"\U0001F80A".join((w.short_name for w in task.wbs.path(include_proj_node=False)))
        other_wbs_string = u"\U0001F80A".join((w.short_name for w in other.wbs.path(include_proj_node=False)))

        if task_wbs_string != other_wbs_string:
            changes['act_wbs'].append((task, task_wbs_string, other_wbs_string))

        if task._attr['task_type'] != other._attr['task_type']:
            changes['act_type'].append((task, other))

        if task.constraint_prime != other.constraint_prime:
            changes['revised_constraint'].append((task, task.constraint_prime, other.constraint_prime, 'Primary'))

        if task.constraint_second != other.constraint_second:
            changes['revised_constraint'].append((task, task.constraint_second, other.constraint_second, 'Secondary'))

    return changes


def get_logic_changes(schedule: Schedule, other_schedule: Schedule):
    changes = defaultdict(list)
    changes['added_logic'] = list(set(schedule.logic()) - set(other_schedule.logic()))
    changes['deleted_logic'] = list(set(other_schedule.logic()) - set(schedule.logic()))

    for i, a in enumerate(changes['added_logic']):
        for j, d in enumerate(changes['deleted_logic']):
            if a.predecessor == d.predecessor and a.successor == d.successor:
                changes['revised_logic'].append((changes['added_logic'].pop(i), changes['deleted_logic'].pop(j)))
                break

    for id, rel in schedule._logic.items():
        if (other := other_schedule._logic.get(id)):
            if rel.lag != other.lag:
                changes['revised_logic'].append((rel, other))

    return changes


def get_resource_changes(resources: list[TaskResource], other_resources: list[TaskResource]):
    def _shallow_compare1(res_1: TaskResource, res_2: TaskResource) -> bool:
        if res_1.task != res_2.task or \
                res_1.name != res_2.name or \
                res_1.account != res_2.account or \
                res_1.resource_type != res_2.resource_type or \
                res_1.lag != res_2.lag:
            return False
        return True

    resources_changes = defaultdict(list)

    res_counter = Counter(resources)
    res_counter.subtract(Counter(other_resources))

    for res, count in res_counter.items():
        if count > 0:
            resources_changes['added_resource'].extend([res] * count)

        elif count < 0:
            resources_changes['deleted_resource'].extend([res] * abs(count))

    for res in resources_changes['added_resource'][:]:
        for old_res in resources_changes['deleted_resource'][:]:
            if _shallow_compare1(res, old_res):
                budget_change_flag = False
                if res.cost.budget != old_res.cost.budget:
                    resources_changes['revised_cost'].append((res, old_res))
                    budget_change_flag = True

                if res.unit_qty.budget != old_res.unit_qty.budget:
                    resources_changes['revised_qty'].append((res, old_res))
                    budget_change_flag = True

                if not budget_change_flag:
                    resources_changes['revised_resource'].append((res, old_res))

                resources_changes['added_resource'].remove(res)
                resources_changes['deleted_resource'].remove(old_res)
                break

    return resources_changes
