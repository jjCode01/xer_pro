from dataclasses import dataclass, field
from data.sched_calendar import SchedCalendar
from data.task import Task

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

    def __post_init__(self):
        self.at_completion = self.actual + self.remaining
        self.variance = self.at_completion - self.budget

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
        self._data = kwargs

    def __getitem__(self, name: str):
        return self._data[name]

    def __eq__(self, other) -> bool:
        return (self._data['task'] == other._data['task'] and
                self._data['name'] == other._data['name'] and
                self._data['account'] == other._data['account'])

    def __hash__(self) -> int:
        return hash((self._data['task']['task_code'],
                     self._data['name'],
                     self._data['account']))

    @property
    def name(self) -> str:
        """Resouce name"""
        return self._data.get('name')

    @property
    def resource_type(self) -> str:
        """Resource type (Labor, Material, Non-Labor)"""
        return self._data.get('rsrc_type')[3:]

    @property
    def calendar(self) -> SchedCalendar:
        """Calendar assigned to resource"""
        return self._data.get('calendar')

    @property
    def task(self) -> Task:
        """Task the resource is assigned to"""
        return self._data.get('task')

    @property
    def account(self) -> dict:
        """Account assigned to resource"""
        return self._data.get('account')

    @property
    def cost(self) -> ResourceValues:
        """
        Cost values for resource
            budget: float
            actual: float
            this_period: float
            remaining: float
            at_completion: float (calculated)
            variance: float (calculated)
        """
        return ResourceValues(
            budget = self._data.get('target_cost'),
            actual = self._data.get('act_reg_cost') + self._data.get('act_ot_cost'),
            this_period = self._data.get('act_this_per_cost'),
            remaining = self._data.get('remain_cost'))

    @property
    def unit_qty(self) -> ResourceValues:
        """
        Unit quantity values for resource
            budget: float
            actual: float
            this_period: float
            remaining: float
            at_completion: float (calculated)
            variance: float (calculated)
        """
        return ResourceValues(
            budget = self._data.get('target_qty'),
            actual = self._data.get('act_reg_qty') + self._data.get('act_ot_qty'),
            this_period = self._data.get('act_this_per_qty'),
            remaining = self._data.get('remain_qty'))

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
            return rem_hours / self.cost.remaining

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

