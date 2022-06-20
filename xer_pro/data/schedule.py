from datetime import datetime
from statistics import mean
from collections import Counter
from data.sched_calendar import SchedCalendar
from data.wbs import Wbs
from data.task import Task
from data.logic import Relationship
from data.resource import ResourceValues, TaskResource

class Schedule:
    def __init__(self, proj_id: str, **tables) -> None:
        self._id = proj_id
        self._project = self._get_project(tables.get('PROJECT', []))
        self._calendars = {cal['clndr_id']: SchedCalendar(**cal)
                          for cal in tables.get('CALENDAR', {})}

        self._wbs = {wbs['wbs_id']: Wbs(**wbs)
                    for wbs in tables.get('PROJWBS', {})
                    if wbs['proj_id'] == proj_id}

        self.name = self._get_schedule_name()

        self._tasks = {id: task for id, task in self._generate_tasks(tables.get('TASK', []))}
        self._logic = {id: rel for id, rel in self._generate_logic(tables.get('TASKPRED', []))}
        self._resources = {r['rsrc_id']: r for r in tables.get('RSRC', [])}
        self._task_resources = {id: res for id, res in self._generate_resources(tables.get('TASKRSRC', []))}

        self._task_code_to_id_map = {t['task_code']: t['task_id'] for t in self.tasks()}
    
    def __str__(self) -> str:
        return self.name

    def __ge__(self, o: object) -> bool:
        return self.data_date >= o.data_date

    @property
    def duration(self) -> int:
        return (self.finish - self.start).days

    @property
    def remaining_duration(self) -> int:
        if self.finish <= self.data_date:
            return 0

        return (self.finish - self.data_date).days

    @property
    def data_date(self) -> datetime:
        """Schedule Data Date"""
        return self._project.get('last_recalc_date')

    @property
    def project_start_date(self) -> datetime:
        """Planned start date set in the Project Date settings

        Returns:
            datetime: Planned start date
        """
        return self._project.get('plan_start_date')

    @property
    def start(self) -> datetime:
        """Start date of first activity in schedule

        Returns:
            datetime: Start date of first activity
        """
        return min((t.start for t in self.tasks()))

    @property
    def finish(self) -> datetime:
        """Finish date of last activity in schedule

        Returns:
            datetime: Finish date of last activity
        """
        return self._project.get('scd_end_date')

    @property
    def must_finish_date(self) -> datetime:
        """Must Finish By date set in the Project Date settings

        Returns:
            datetime: Must Finish By date
        """
        return self._project.get('plan_end_date')

    
    def tasks(self, not_started: bool=False, in_progress: bool=False, completed: bool=False) -> list[Task]:
        """List of all Task objects included in the schedule.
        """
        if not any([not_started, in_progress, completed]):
            return self._tasks.values()

        return [
            t for t in self._tasks.values()
            if (
                (t.is_not_started and not_started) or
                (t.is_in_progress and in_progress) or
                (t.is_completed and completed)
            )
        ]

    @property
    def logic(self) -> list[Relationship]:
        """List of all Relationship objects included in the schedule

        Returns:
            list[Relationship]: All Relationship objects
        """
        return self._logic.values()

    @property
    def calendars(self) -> list[SchedCalendar]:
        """List of all Calendar objects included in the schedule.

        Returns:
            list[Calendar]: All Calendar objects
        """
        return self._calendars.values()

    @property
    def wbs(self) -> list[Wbs]:
        """List of all Wbs objects included in the schedule.

        Returns:
            list[Wbs]: All Wbs objects
        """
        return self._wbs.values()

    @property
    def resources(self) -> list[TaskResource]:
        """List of all TaskResource objects included in the schedule.

        Returns:
            list[TaskResource]: All TaskResource objects
        """
        return self._task_resources.values()

    @property
    def cost(self) -> ResourceValues:
        return ResourceValues(
            budget=sum((r.cost.budget for r in self.resources)),
            actual=sum((r.cost.actual for r in self.resources)),
            this_period=sum((r.cost.this_period for r in self.resources)),
            remaining=sum((r.cost.remaining for r in self.resources)))

    @property
    def unit_qty(self) -> ResourceValues:
        return ResourceValues(
            budget=sum((r.unit_qty.budget for r in self.resources)),
            actual=sum((r.unit_qty.actual for r in self.resources)),
            this_period=sum((r.unit_qty.this_period for r in self.resources)),
            remaining=sum((r.unit_qty.remaining for r in self.resources)))

    @property
    def percent_complete(self) -> float:
        od_sum = sum((t.original_duration for t in self.tasks()))
        rd_sum = sum((t.remaining_duration for t in self.tasks()))
        dur_comp = 1 - (rd_sum / od_sum)

        status_cnt = Counter([t.status for t in self.tasks()])
        status_comp = (status_cnt['In Progress'] / 2 + status_cnt['Complete']) / len(self.tasks())

        return mean([dur_comp, status_comp]) * 100

    # def tasks_completed(self) -> list[Task]:
    #     return [t for t in self.tasks(completed=True) if t.is_completed]

    def _generate_tasks(self, table: list) -> dict[str, Task]:
        for row in table:
            if row['proj_id'] == self._id:
                row['calendar'] = self._calendars.get(row['clndr_id'])
                yield (row['task_id'], Task(**row))

    def _generate_logic(self, table: list) -> dict[tuple[str, str, str], Relationship]:
        for row in table:
            if row['pred_proj_id'] == self._id and row['proj_id'] == self._id:
                pred = self._tasks.get(row['pred_task_id'])
                succ = self._tasks.get(row['task_id'])
                yield ((pred['task_code'], succ['task_code'], row['pred_type']),
                        Relationship(pred, succ, **row))

    def _generate_resources(self, table: list) -> dict[tuple[str, str, str], TaskResource]:
        for row in table:
            if row['proj_id'] == self._id:
                row['task'] = self._tasks.get(row['task_id'])
                resource = self._resources.get(row['rsrc_id'], {})
                row['calendar'] = self._calendars.get(resource['clndr_id']) if resource else self._calendars.get(row['task']['clndr_id'])
                row['name'] = resource.get('rsrc_name', '')
                row['account'] = "" #### Need to work on this

                id = (row['task']['task_code'], row['name'], row['account'])

                yield (id, TaskResource(**row))
    
    def _get_project(self, table: list) -> dict:
        for row in table:
            if row['proj_id'] == self._id:
                return row

    def _get_schedule_name(self) -> str:
        for w in self.wbs:
            if w.is_project_node:
                return w['wbs_name']

        return ""
