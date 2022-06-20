from collections import defaultdict

from data.schedule import Schedule
from data.task import Task
from data.logic import Relationship


def group_by_status(schedule: Schedule) -> dict[str, list[Task]]:
    status = defaultdict(list)
    for t in schedule.tasks:
        status[t.status].append(t)

    return status

def filter_by_status(schedule: Schedule, not_started: bool=False, in_progress: bool=False, completed: bool=False) -> list[Task]:
    if not any([not_started, in_progress, completed]):
        return []

    return [
        t for t in schedule.tasks if
        (t.is_not_started and not_started) or
        (t.is_in_progress and in_progress) or
        (t.is_completed and completed)]

def group_by_float(schedule: Schedule, near_critical: int = 20, high_float: int = 50) -> dict[str, list[Task]]:
    float = {
        'Critical': list(),
        'Near Critical': list(),
        'Normal Float': list(),
        'High Float': list()}

    for t in schedule.tasks:
        if t.is_completed:
            continue

        tf = t.total_float
        if tf <= 0:
            float['Critical'].append(t)
            continue
        if 0 < tf <= near_critical:
            float['Near Critical'].append(t)
            continue
        if near_critical < tf <= high_float:
            float['Normal Float'].append(t)
            continue
        if tf > high_float:
            float['High Float'].append(t)
    
    return float


def filter_by_float(self, **float) -> list[Task]:
    open_tasks = [t for t in self.tasks if not t.is_completed]
    if float.keys() >= {'high', 'low'}:
        low, high = min(float['high'], float['low']), max(float['high'], float['low'])
        return [t for t in open_tasks if low <= t.total_float <= high]

    if 'low' in float:
        return [t for t in open_tasks if float['low'] <= t.total_float]

    if 'high' in float:
        return [t for t in open_tasks if t.total_float <= float['high']]

    if 'equals' in float:
        return [t for t in open_tasks if t.total_float == float['equals']]

    return []

def group_by_link(self) -> dict[str, list[Relationship]]:
    links = defaultdict(list)
    for rel in self.logic:
        links[rel.link].append(rel)

    return links