from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from data.sched_calendar import SchedCalendar
from data.task import Task


class CostAccount:
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
            else self.actual / self.budget * 100

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
        return (self._attr['task'] == other._attr['task'] and
                self._attr['name'] == other._attr['name'] and
                self._attr['account'] == other._attr['account'] and
                self._attr['rsrc_type'] == other._attr['rsrc_type'] and
                self._attr['target_qty'] == other._attr['target_qty'] and
                self._attr['target_lag_drtn_hr_cnt'] == other._attr['target_lag_drtn_hr_cnt'] and
                self._attr['target_cost'] == other._attr['target_cost'])

    def __hash__(self) -> int:
        return hash((self._attr['task'],
                     self._attr['name'],
                     self._attr['account'],
                     self._attr['rsrc_type'],
                     self._attr['target_qty'],
                     self._attr['target_lag_drtn_hr_cnt'],
                     self._attr['target_cost'],))

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
    def finish(self) -> datetime:
        if self._attr['act_end_date']:
            return self._attr['act_end_date']

        return self._attr['reend_date']

    @property
    def start(self) -> datetime:
        if self._attr['act_start_date']:
            return self._attr['act_start_date']

        return self._attr['restart_date']

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
            budget=self._attr.get('target_cost'),
            actual=self._attr.get('act_reg_cost') + self._attr.get('act_ot_cost'),
            this_period=self._attr.get('act_this_per_cost'),
            remaining=self._attr.get('remain_cost'))

    @property
    def unit_qty(self) -> ResourceValues:
        return ResourceValues(
            budget=self._attr.get('target_qty'),
            actual=self._attr.get('act_reg_qty') + self._attr.get('act_ot_qty'),
            this_period=self._attr.get('act_this_per_qty'),
            remaining=self._attr.get('remain_qty'))

    @property
    def remaining_start(self) -> Optional[datetime]:
        return self._attr.get('restart_date')

    @property
    def remaining_finish(self) -> Optional[datetime]:
        return self._attr.get('reend_date')

    @property
    def remaining_late_start(self) -> Optional[datetime]:
        return self._attr.get('rem_late_start_date')

    @property
    def remaining_late_finish(self) -> Optional[datetime]:
        return self._attr.get('rem_late_end_date')
