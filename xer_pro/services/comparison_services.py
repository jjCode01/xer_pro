from collections import defaultdict, Counter
from fuzzywuzzy import fuzz
from xer_pro.data.logic import Relationship
from xer_pro.data.resource import TaskResource
from xer_pro.data.schedule import Schedule
from xer_pro.data.task import Task
from xer_pro.data.wbs import WbsLinkedList, WbsNode
from xer_pro.data.sched_calendar import SchedCalendar


def get_schedule_changes(
    schedule: Schedule, other_schedule: Schedule
) -> dict[str, list]:
    changes = defaultdict(list)
    changes.update(get_task_changes(schedule, other_schedule))
    changes.update(get_logic_changes(schedule, other_schedule))
    changes.update(get_resource_changes(schedule.resources, other_schedule.resources))
    changes.update(get_wbs_changes(schedule.wbs, other_schedule.wbs))
    changes.update(get_clndr_changes(schedule.calendars, other_schedule.calendars))
    return changes


def get_task_changes(schedule: Schedule, other_schedule: Schedule) -> dict[str, list]:
    changes = defaultdict(list)
    changes["added_tasks"] = list(set(schedule.tasks()) - set(other_schedule.tasks()))
    changes["deleted_tasks"] = list(set(other_schedule.tasks()) - set(schedule.tasks()))

    other_tasks = {t._attr["task_code"]: t for t in other_schedule.tasks()}

    for task in schedule.tasks():
        if not (other := other_tasks.get(task.activity_id)):
            continue

        if task.name != other.name:
            changes["name"].append(
                (
                    task,
                    other,
                    fuzz.ratio(task.name, other.name),
                    fuzz.partial_ratio(task.name, other.name),
                )
            )

        if task.original_duration != other.original_duration:
            changes["orig_duration"].append((task, other))

        else:
            if (
                task.is_not_started and other.is_not_started
            ) and task.remaining_duration != other.remaining_duration:
                changes["rem_duration"].append((task, other))

        if not other.is_not_started and task.start.date() != other.start.date():
            changes["act_start"].append((task, other))

        if other.is_completed and task.finish.date() != other.finish.date():
            changes["act_finish"].append((task, other))

        if task.calendar != other.calendar:
            changes["act_calendar"].append((task, other))

        task_wbs = WbsLinkedList(task.wbs)
        other_wbs = WbsLinkedList(other.wbs)

        if task_wbs != other_wbs:
            changes["act_wbs"].append(
                (task, task_wbs.short_name_path(), other_wbs.short_name_path())
            )

        if task._attr["task_type"] != other._attr["task_type"]:
            changes["act_type"].append((task, other))

        if task.constraint_prime != other.constraint_prime:
            changes["revised_constraint"].append(
                (task, task.constraint_prime, other.constraint_prime, "Primary")
            )

        if task.constraint_second != other.constraint_second:
            changes["revised_constraint"].append(
                (task, task.constraint_second, other.constraint_second, "Secondary")
            )

        if other.is_not_started and not task.is_not_started:
            changes["started"].append(task)

        if not other.is_completed and task.is_completed:
            changes["finished"].append(task)

        def sort_key(val):
            if isinstance(val, Task):
                return val.activity_id
            if isinstance(val, tuple):
                return val[0].activity_id

        for change in changes:
            changes[change].sort(key=sort_key)

    return changes


def get_logic_changes(schedule: Schedule, other_schedule: Schedule):
    changes = defaultdict(list)
    changes["added_logic"] = list(set(schedule.logic()) - set(other_schedule.logic()))
    changes["deleted_logic"] = list(set(other_schedule.logic()) - set(schedule.logic()))

    for i, a in enumerate(changes["added_logic"]):
        for j, d in enumerate(changes["deleted_logic"]):
            if a.predecessor == d.predecessor and a.successor == d.successor:
                changes["revised_logic"].append(
                    (changes["added_logic"].pop(i), changes["deleted_logic"].pop(j))
                )
                break

    for id, rel in schedule._logic.items():
        if other := other_schedule._logic.get(id):
            if rel.lag != other.lag:
                changes["revised_logic"].append((rel, other))

    def sort_key(val):
        if isinstance(val, Relationship):
            return (val.predecessor.activity_id, val.successor.activity_id)
        if isinstance(val, tuple):
            return (val[0].predecessor.activity_id, val[0].successor.activity_id)

    for change in changes:
        changes[change].sort(key=sort_key)

    return changes


def get_resource_changes(
    resources: list[TaskResource], other_resources: list[TaskResource]
) -> dict[str, list]:
    def _shallow_compare1(res_1: TaskResource, res_2: TaskResource) -> bool:
        if (
            res_1.task != res_2.task
            or res_1.name != res_2.name
            or res_1.account != res_2.account
            or res_1.resource_type != res_2.resource_type
            or res_1.lag != res_2.lag
        ):
            return False
        return True

    resources_changes = defaultdict(list)

    res_counter = Counter(resources)
    res_counter.subtract(Counter(other_resources))

    for res, count in res_counter.items():
        if count > 0:
            resources_changes["added_resource"].extend([res] * count)

        elif count < 0:
            resources_changes["deleted_resource"].extend([res] * abs(count))

    for res in resources_changes["added_resource"][:]:
        for old_res in resources_changes["deleted_resource"][:]:
            if _shallow_compare1(res, old_res):
                budget_change_flag = False
                if res.cost.budget != old_res.cost.budget:
                    resources_changes["revised_cost"].append((res, old_res))
                    budget_change_flag = True

                if res.unit_qty.budget != old_res.unit_qty.budget:
                    resources_changes["revised_qty"].append((res, old_res))
                    budget_change_flag = True

                if not budget_change_flag:
                    resources_changes["revised_resource"].append((res, old_res))

                resources_changes["added_resource"].remove(res)
                resources_changes["deleted_resource"].remove(old_res)
                break

    if resources_changes["added_resource"]:
        resources_changes["added_resource"].sort(key=lambda r: r.task.activity_id)

    return resources_changes


def get_wbs_changes(
    wbs_nodes: list[WbsNode], other_wbs_nodes: list[WbsNode]
) -> dict[str, list]:
    wbs_changes = defaultdict(list)

    wbs_node_by_path = {
        WbsLinkedList(wbs): wbs for wbs in wbs_nodes if not wbs.is_project_node
    }

    other_wbs_node_by_path = {
        WbsLinkedList(wbs): wbs for wbs in other_wbs_nodes if not wbs.is_project_node
    }

    wbs_changes["added_wbs"] = sorted(
        [
            (path.short_name_path(), node)
            for path, node in wbs_node_by_path.items()
            if path not in other_wbs_node_by_path
        ],
        key=lambda w: w[0],
    )

    wbs_changes["deleted_wbs"] = [
        (path.short_name_path(), node)
        for path, node in other_wbs_node_by_path.items()
        if path not in wbs_node_by_path
    ]

    for path, node in wbs_node_by_path.items():
        if other_node := other_wbs_node_by_path.get(path):
            if node.name != other_node.name:
                wbs_changes["revised_wbs_name"].append(
                    (
                        path.short_name_path(),
                        node,
                        other_node,
                        fuzz.ratio(node.name, other_node.name),
                        fuzz.partial_ratio(node.name, other_node.name),
                    )
                )

    return wbs_changes


def get_clndr_changes(
    calendars: list[SchedCalendar], other_calendars: list[SchedCalendar]
) -> dict[SchedCalendar, list]:
    clndr_changes = defaultdict(list)
    clndr_changes["added_calendar"] = list(set(calendars) - set(other_calendars))
    clndr_changes["deleted_calendar"] = list(set(other_calendars) - set(calendars))
    for cal in calendars:
        for other_cal in other_calendars:
            if cal == other_cal:
                added_holiday = sorted(
                    list(set(cal.holidays) - set(other_cal.holidays))
                )
                for day in added_holiday:
                    clndr_changes["added_holiday"].append((cal, day))

                deleted_holiday = sorted(
                    list(set(other_cal.holidays) - set(cal.holidays))
                )
                for day in deleted_holiday:
                    clndr_changes["deleted_holiday"].append((cal, day))

                added_workday = sorted(
                    list(set(cal.work_exceptions) - set(other_cal.work_exceptions))
                )
                for day in added_workday:
                    clndr_changes["added_workday"].append((cal, day))

                deleted_workday = sorted(
                    list(set(other_cal.work_exceptions) - set(cal.work_exceptions))
                )
                for day in deleted_workday:
                    clndr_changes["deleted_workday"].append((cal, day))

                break

    return clndr_changes
