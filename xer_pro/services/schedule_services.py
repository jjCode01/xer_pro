from collections import defaultdict
from datetime import datetime, timedelta
from fuzzywuzzy import fuzz, process

from data.schedule import Schedule
from data.task import Task
from data.logic import Relationship
from data.resource import TaskResource
from data.sched_calendar import rem_hours_per_day

COLORS = {
    'DANGER': "#dc3545",
    'INFO': "#0dcaf0",
    'PRIMARY': "#0d6efd",
    'SUCCESS': "#20c997",
    'WARNING': "#ffc107"}

def _parse_remaining_cash_flow(resource: TaskResource, late_dates: bool=False) -> list[tuple[str, float]]:
    start = resource['rem_late_start_date'] if late_dates else resource['restart_date']
    finish = resource['rem_late_end_date'] if late_dates else resource['reend_date']

    if _interval_date(start) == _interval_date(finish):
        return [(_interval_date(start), resource.cost.remaining)]

    task_rd = resource.task._attr["remain_drtn_hr_cnt"]
    rem_days = rem_hours_per_day(resource.calendar, start, finish)
    calc_rd = sum((d[1] for d in rem_days))
    if calc_rd != task_rd:
        raise ValueError(f'Error: calculated remaining duration does not match task remaining duration')

    rem_cost_per_hr = resource.cost.remaining if calc_rd == 0 else resource.cost.remaining / calc_rd
    return [(_interval_date(day[0]), rem_cost_per_hr * day[1]) for day in rem_days]

def _new_data_set(label: str, data: list, color: str, stack: str) -> dict:
    return {
        'label': label,
        'data': data,
        'backgroundColor': color,
        'stack': stack}

def parse_schedule_cash_flow(schedule: Schedule) -> dict[str, list]:
    """Generate a monthly cash flow."""

    early = defaultdict(float)
    late = defaultdict(float)
    actual = defaultdict(float)
    this_period = defaultdict(float)

    if len(schedule.resources) == 0:
        return {}

    for resource in schedule.resources:
        if resource.cost.remaining != 0:
            for dt in _parse_remaining_cash_flow(resource):
                early[dt[0]] += dt[1]

            for dt in _parse_remaining_cash_flow(resource, late_dates=True):
                late[dt[0]] += dt[1]

        if resource.cost.this_period != 0:
            start = max([resource.start, schedule.last_financial_period.finish + timedelta(days=1)])
            finish = min([resource.finish, schedule.data_date - timedelta(hours=1)])

            if _interval_date(start) >= _interval_date(finish):
                this_period[_interval_date(start)] += resource.cost.this_period
            else:
                period_work_hours = rem_hours_per_day(resource.calendar, start, finish)
                act_cost_per_hr = resource.cost.this_period / sum((hr[1] for hr in period_work_hours))
                for day in period_work_hours:
                    this_period[_interval_date(day[0])] += act_cost_per_hr * day[1]

    for per in schedule._financials.values():
        if _interval_date(per.period.start) == _interval_date(per.period.finish):
            actual[_interval_date(per.period.start)] += per.cost
        else:
            actual[_interval_date(per.period.finish)] += per.cost

    return [
        _new_data_set(
            label='Actual', 
            data=[{'x': dt, 'y': val} for dt, val in actual.items()],
            color=COLORS['PRIMARY'],
            stack='stack 0'),
        _new_data_set(
            label='This Period', 
            data=[{'x': dt, 'y': val} for dt, val in this_period.items()],
            color=COLORS['INFO'],
            stack='stack 0'),
        _new_data_set(
            label='Early', 
            data=[{'x': dt, 'y': val} for dt, val in early.items()],
            color=COLORS['SUCCESS'],
            stack='stack 0'),
        _new_data_set(
            label='Late', 
            data=[{'x': dt, 'y': val} for dt, val in late.items()],
            color=COLORS['DANGER'],
            stack='stack 1'),]

def parse_schedule_work_flow(schedule: Schedule, start: datetime, finish: datetime) -> dict:

    _as = defaultdict(int)
    _af = defaultdict(int)
    _es = defaultdict(int)
    _ef = defaultdict(int)
    _ls = defaultdict(int)
    _lf = defaultdict(int)

    for task in schedule.tasks():
        if start <= task.start <= finish:
            if task.is_not_started:
                _es[_interval_date(task.start)] += 1
                _ls[_interval_date(task.late_start)] += 1
            else:
                _as[_interval_date(task.start)] += 1

        if start <= task.finish <= finish:
            if task.is_completed:
                _af[_interval_date(task.finish)] += 1
            else:
                _ef[_interval_date(task.finish)] += 1
                _lf[_interval_date(task.late_finish)] += 1

    return [
        _new_data_set(
            'Actual Finish',
            [{'x': dt, 'y': val} for dt, val in _af.items()],
            COLORS['PRIMARY'],
            'stack 0'),
        _new_data_set(
            'Actual Start',
            [{'x': dt, 'y': val} for dt, val in _as.items()],
            COLORS['INFO'],
            'stack 0'),
        _new_data_set(
            'Early Finish',
            [{'x': dt, 'y': val} for dt, val in _ef.items()],
            COLORS['SUCCESS'],
            'stack 0'),
        _new_data_set(
            'Early Start',
            [{'x': dt, 'y': val} for dt, val in _es.items()],
            COLORS['SUCCESS'] + 'B3',
            'stack 0'),
        _new_data_set(
            'Late Finish',
            [{'x': dt, 'y': val} for dt, val in _lf.items()],
            COLORS['DANGER'],
            'stack 1'),
        _new_data_set(
            'Late Start',
            [{'x': dt, 'y': val} for dt, val in _ls.items()],
            COLORS['DANGER'] + 'B3',
            'stack 1'),
    ]

def group_by_status(schedule: Schedule) -> dict[str, list[Task]]:
    status = defaultdict(list)
    for t in schedule.tasks:
        status[t.status].append(t)

    return status

def _parse_float_counts(tasks: list[Task], near_critical: int, high_float: int) -> dict[str, int]:
    float_counts = defaultdict(int)

    for task in tasks:
        if task.is_completed:
            continue
        tf = task.total_float
        if tf <= 0:
            float_counts['Critical'] += 1
        elif 0 < tf <= near_critical:
            float_counts['Near Critical'] += 1
        elif near_critical < tf <= high_float:
            float_counts['Normal Float'] +=1
        elif tf > high_float:
            float_counts['High Float'] +=1 
        
    return float_counts

def parse_float_chart_data(curr_tasks: list[Task], prev_tasks: list[Task], near_critical: int = 20, high_float: int = 50) -> dict[str, int]:
    
    curr_counts = _parse_float_counts(curr_tasks, near_critical, high_float)
    prev_counts = _parse_float_counts(prev_tasks, near_critical, high_float)

    return {
        'labels': ['Current', 'Previous'],
        'datasets': [
            {
                'label': 'Critical (TF < 1)',
                'data': [
                    curr_counts['Critical'] / sum(curr_counts.values()) * 100,
                    prev_counts['Critical'] / sum(prev_counts.values()) * 100
                ],
                'backgroundColor': [COLORS['DANGER']],
            },
            {
                'label': f'Near Critical (TF < {near_critical + 1})',
                'data': [
                    curr_counts['Near Critical'] / sum(curr_counts.values()) * 100,
                    prev_counts['Near Critical'] / sum(prev_counts.values()) * 100
                ],
                'backgroundColor': [COLORS['WARNING']],
            },
            {
                'label': f'Normal Float (TF < {high_float})',
                'data': [
                    curr_counts['Normal Float'] / sum(curr_counts.values()) * 100,
                    prev_counts['Normal Float'] / sum(prev_counts.values()) * 100
                ],
                'backgroundColor': [COLORS['SUCCESS']],
            },
            {
                'label': f'High Float (TF > {high_float - 1})',
                'data': [
                    curr_counts['High Float'] / sum(curr_counts.values()) * 100,
                    prev_counts['High Float'] / sum(prev_counts.values()) * 100
                ],
                'backgroundColor': [COLORS['PRIMARY']],
            }]}
    

def group_by_link(self) -> dict[str, list[Relationship]]:
    links = defaultdict(list)
    for rel in self.logic:
        links[rel.link].append(rel)

    return links

def _interval_date(date: datetime) -> str:
    return _date_str(datetime(date.year, date.month, 1, 0, 0, 0))

def _date_str(date: datetime) -> str:
    return datetime.strftime(date, '%Y-%m-%d')

def _clean_date(date: datetime) -> datetime:
    return date.replace(hour=0, minute=0, second=0, microsecond=0)

def get_task_changes(sched_a_tasks: list[Task], sched_b_tasks: list[Task]) -> dict[str, list]:
    b_tasks = {t.activity_id: t for t in sched_b_tasks}

    changes = defaultdict(list)

    changes['added'] = list(set(sched_a_tasks) - set(sched_b_tasks))
    changes['deleted'] = list(set(sched_b_tasks) - set(sched_a_tasks))

    for task in sched_a_tasks:
        if task in sched_b_tasks:
            other = b_tasks.get(task.activity_id)

            if task.name != other.name:
                changes['name'].append((task, other, fuzz.ratio(task.name, other.name)))

            if task.original_duration != other.original_duration:
                changes['orig_duration'].append((task, other))
            else:
                if (task.is_not_started and other.is_not_started) and task.remaining_duration != other.remaining_duration:    
                    changes['rem_duration'].append((task, other))

            if not other.is_not_started:
                if task.start.date() != other.start.date():
                    changes['act_start'].append((task, other))

            if other.is_completed:
                if task.finish.date() != other.finish.date():
                    changes['act_finish'].append((task, other))


    return changes