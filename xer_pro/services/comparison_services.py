from collections import defaultdict
from fuzzywuzzy import fuzz
from data.schedule import Schedule
from services.wbs_services import get_all_wbs_levels


def get_schedule_changes(schedule: Schedule, other_schedule: Schedule) -> dict[str, list]:
    changes = defaultdict(list)
    changes.update(get_task_changes(schedule, other_schedule))
    changes.update(get_logic_changes(schedule, other_schedule))
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

        task_wbs_nodes = _get_task_wbs_string(
            task._attr['wbs_id'],
            schedule._wbs)

        other_wbs_nodes = _get_task_wbs_string(
            other._attr['wbs_id'],
            other_schedule._wbs)

        if task_wbs_nodes != other_wbs_nodes:
            changes['act_wbs'].append((task, task_wbs_nodes, other_wbs_nodes))

        if task._attr['task_type'] != other._attr['task_type']:
            changes['act_type'].append((task, other))

        if task.constraint_prime != other.constraint_prime:
            if (task.constraint_prime and other.constraint_prime is None):
                changes['added_constraint'].append((
                    task,
                    task.constraint_prime,
                    'Primary'))

            elif task.constraint_prime is None and other.constraint_prime:
                changes['deleted_constraint'].append((
                    task,
                    other.constraint_prime,
                    'Primary'))

            elif task.constraint_prime and other.constraint_prime:
                if task.constraint_prime['type'] != other.constraint_prime['type']:
                    changes['added_constraint'].append((
                        task,
                        task.constraint_prime,
                        'Primary'))

                    changes['deleted_constraint'].append((
                        task,
                        other.constraint_prime,
                        'Primary'))

                else:
                    changes['revised_constraint'].append((
                        task,
                        task.constraint_prime,
                        other.constraint_prime,
                        'Primary'))

        if task.constraint_second != other.constraint_second:
            if task.constraint_second and other.constraint_second is None:
                changes['added_constraint'].append((
                    task,
                    task.constraint_second,
                    'Secondary'))

            elif task.constraint_second is None and other.constraint_second:
                changes['deleted_constraint'].append((
                    task,
                    other.constraint_second,
                    'Secondary'))

            elif task.constraint_second and other.constraint_second:
                if task.constraint_second['type'] != other.constraint_second['type']:
                    changes['added_constraint'].append((
                        task,
                        task.constraint_second,
                        'Secondary'))

                    changes['deleted_constraint'].append((
                        task,
                        other.constraint_second,
                        'Secondary'))

                else:
                    changes['revised_constraint'].append((
                        task,
                        task.constraint_second,
                        other.constraint_second,
                        'Secondary'))

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


def get_resource_changes(schedule: Schedule, other_schedule: Schedule):
    pass


def _get_task_wbs_string(id: str, wbs: dict) -> str:
    nodes = get_all_wbs_levels(id, wbs)
    return u"\U0001F80A".join((node._attr['wbs_short_name'] for node in nodes))
