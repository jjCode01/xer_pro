from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from data.sched_calendar import SchedCalendar
from data.task import Task

class RsrcAccount:
    def __init__(self) -> None:
        pass

@dataclass
class ResourceValues:
    """
    A class to represent resource cost or unit quantity values.

    ...

    Attributes
    ----------
    budget : float
        Budgeted cost or unit quantity
    actual : float
        Actual cost or unit quantity expended
    this_period : float
        Actual cost or unit quantity expended this period
    remaining : float
        Remaining cost or unit quantity
    at_completion : float
        Sum of actual and remaining cost or unit quantity
    variance : float
        Difference between at_completion and budget cost or unit quantity
    """
    budget: float
    actual: float
    this_period: float
    remaining: float
    at_completion: float = field(init=False)
    variance: float = field(init=False)
    percent: float = field(init=False)

    def __post_init__(self):
        self.at_completion = self.actual + self.remaining
        self.variance = self.at_completion - self.budget
        self.percent = 0.0 \
            if (self.budget == 0 or self.actual == 0) \
            else  self.actual / self.budget * 100

    def __bool__(self) -> bool:
        return (
            self.budget != 0 and
            self.actual != 0)

class TaskResource:
    """
    A class to represent a resource assigned to a schedule activity.

    ...

    Attributes
    ----------
    name: str
        Resource name
    resource_type: str
        Resource type (Labor, Material, Non-Labor)
    calendar: Calendar
        Calendar assigned to resource
    task: Task
        Task the resource is assigned to
    account: dict
        Account assigned to resource
    cost: ResourceValues
        Cost values for resource (budget, actual, this_period, remaining)
    unit_quantity: ResourceValues
        Unity quantity values for resource (budget, actual, this_period, remaining)

    """
    def __init__(self, **kwargs) -> None:
        self._attr = kwargs

    def __getitem__(self, name: str):
        return self._attr[name]

    def __eq__(self, other) -> bool:
        return (self._attr['task'] == other._data['task'] and
                self._attr['name'] == other._data['name'] and
                self._attr['account'] == other._data['account'])

    def __hash__(self) -> int:
        return hash((self._attr['task']['task_code'],
                     self._attr['name'],
                     self._attr['account']))

    @property
    def name(self) -> str:
        """Resouce name"""
        return self._attr.get('name')

    @property
    def resource_type(self) -> str:
        """Resource type (Labor, Material, Non-Labor)"""
        return self._attr.get('rsrc_type')[3:]

    @property
    def calendar(self) -> SchedCalendar:
        """Calendar assigned to resource"""
        return self._attr.get('calendar')

    @calendar.setter
    def calendar(self, cal: SchedCalendar) -> None:
        if not isinstance(cal, SchedCalendar):
            raise ValueError("Value Error: Argument must be type SchedCalendar")
        self._attr['calendar'] = cal

    @property
    def task(self) -> Task:
        """Task the resource is assigned to"""
        return self._attr.get('task')

    @task.setter
    def task(self, task: Task) -> None:
        if not isinstance(task, Task):
            raise ValueError("Value Error: Argument must be type Task")
        self._attr['task'] = task

    @property
    def account(self) -> dict:
        """Account assigned to resource"""
        return self._attr.get('account')

    @property
    def cost(self) -> ResourceValues:
        return ResourceValues(
            budget = self._attr.get('target_cost'),
            actual = self._attr.get('act_reg_cost') + self._attr.get('act_ot_cost'),
            this_period = self._attr.get('act_this_per_cost'),
            remaining = self._attr.get('remain_cost'))

    @property
    def unit_qty(self) -> ResourceValues:
        return ResourceValues(
            budget = self._attr.get('target_qty'),
            actual = self._attr.get('act_reg_qty') + self._attr.get('act_ot_qty'),
            this_period = self._attr.get('act_this_per_qty'),
            remaining = self._attr.get('remain_qty'))

    @property
    def remaining_start(self) -> Optional[datetime]:
        return self._attr.get('restart_date')

    @property
    def remaining_finish(self) -> Optional[datetime]:
        return self._attr.get('reend_date')

    @property
    def remaining_cost_per_hour(self) -> float:
        ###### UNTESTED #######
        """
        Calculates the remaining cost per hour

        Returns:
            float: Remaining cost per hour
        """
        if self.cost.remaining == 0.0:
            return 0.0

        if (rem_hours:=self.task['remain_drtn_hr_cnt']):
            return self.cost.remaining / rem_hours

        return self.cost.remaining

#     def remaining_cost_days(self) -> list[tuple(datetime, float)]:
#         if (start:=self._data['restart_date']) and (finish:=self._data['reend_date']):

#             if start.date() == finish.date():
#                 return [(start.replace(microsecond=0, second=0, minute=0, hour=0),
#                          calc_time_variance_hrs(start.time(), finish.time()))]

#             rem_days = list(self.calendar.iter_workdays(start, finish))

#             if 

#             if start.time() == self.calendar._work_week.get(f'{start:%A}').start:
#                 rcd.append((start, ))


# def calc_time_variance_hrs(start: time, finish: time) -> float:
#     ###### NEEDS TO BE TESTED ########
#     if not isinstance(start, time) or not isinstance(finish, time):
#         raise ValueError('Arguments must be time objects')

#     start_date = datetime.combine(datetime.today().date(), start)
#     finish_date = datetime.combine(datetime.today().date(), start)

#     hrs = (max(start_date, finish_date) - min(start_date, finish_date)).total_seconds() / 3600
#     return hrs

