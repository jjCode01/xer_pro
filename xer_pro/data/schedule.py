from datetime import datetime, timedelta
from statistics import mean
from collections import Counter
from typing import Iterator, Optional
from functools import cached_property
from xer_pro.data.sched_calendar import SchedCalendar
from xer_pro.data.wbs import WbsNode
from xer_pro.data.task import Task
from xer_pro.data.logic import Relationship
from xer_pro.data.resource import ResourceValues, TaskResource
from xer_pro.data.financial import FinancialPeriod, ResourceFinancial


class Schedule:
    def __init__(self, proj_id: str, **tables) -> None:
        self._id = proj_id
        self._project = self._get_project(tables.get("PROJECT", []))
        self._calendars = {
            cal["clndr_id"]: SchedCalendar(**cal) for cal in tables.get("CALENDAR", {})
        }

        self._fin_dates = {
            fin["fin_dates_id"]: FinancialPeriod(**fin)
            for fin in tables.get("FINDATES", {})
        }

        self._wbs = {
            wbs["wbs_id"]: WbsNode(**wbs)
            for wbs in tables.get("PROJWBS", {})
            if wbs["proj_id"] == proj_id
        }

        for wbs in self._wbs.values():
            wbs.parent = self._wbs.get(wbs._attr["parent_wbs_id"])

        self.name = self._get_schedule_name()

        self._tasks = {
            id: task for id, task in self._generate_tasks(tables.get("TASK", []))
        }
        self._logic = {
            id: rel for id, rel in self._generate_logic(tables.get("TASKPRED", []))
        }
        self._resources = {r["rsrc_id"]: r for r in tables.get("RSRC", [])}
        self._accounts = {acct["acct_id"]: acct for acct in tables.get("ACCOUNT", [])}
        self._task_resources = {
            res["taskrsrc_id"]: res
            for res in self._generate_resources(tables.get("TASKRSRC", []))
        }
        self._financials = {
            id: fin for id, fin in self._generate_financials(tables.get("TRSRCFIN", []))
        }
        self._task_code_to_id_map = {t["task_code"]: t["task_id"] for t in self.tasks()}

        _cal_counter = Counter([t["clndr_id"] for t in self.tasks()])
        for cal in self.calendars:
            cal.assignments = _cal_counter.get(cal["clndr_id"], 0)

        _wbs_counter = Counter([t["wbs_id"] for t in self.tasks()])
        for node in self.wbs:
            node.assignments = _wbs_counter.get(node["wbs_id"], 0)

    def __str__(self) -> str:
        return self.name

    def __ge__(self, o: object) -> bool:
        return self.data_date >= o.data_date

    @property
    def calendars(self) -> list[SchedCalendar]:
        """List of all Calendar objects included in the schedule"""
        return self._calendars.values()

    @cached_property
    def cost(self) -> ResourceValues:
        return ResourceValues(
            budget=sum((r.cost.budget for r in self.resources)),
            actual=sum((r.cost.actual for r in self.resources)),
            this_period=sum((r.cost.this_period for r in self.resources)),
            remaining=sum((r.cost.remaining for r in self.resources)),
        )

    @property
    def data_date(self) -> datetime:
        """Schedule Data Date"""
        return self._project.get("last_recalc_date")

    @property
    def duration(self) -> int:
        """Total duration in calendar days"""
        return (self.finish - self.start).days

    @property
    def finish(self) -> datetime:
        """Finish date of last activity in schedule"""
        return self._project.get("scd_end_date")

    def iter_performance_dates(self, remaining_only: bool = True) -> Iterator[datetime]:
        """
        Iterates through all dates from the start date through
        the schedule end date.

        Returns:
            iter: dates between the project start and finish dates

        Yields:
            Iterator[iter]: datetime object
        """
        next_date = self.data_date if remaining_only else self.start
        while next_date <= self.end_date:
            yield next_date
            next_date += timedelta(days=1)

    @property
    def last_financial_period(self) -> Optional[FinancialPeriod]:
        if not self._project["last_fin_dates_id"]:
            return None

        return self._fin_dates.get(self._project["last_fin_dates_id"])

    def logic(
        self, fs: bool = False, ff: bool = False, ss: bool = False, sf: bool = False
    ) -> list[Relationship]:
        """List of Relationship objects included in the schedule"""
        rels = sorted(
            self._logic.values(),
            key=lambda x: [x.predecessor.activity_id, x.successor.activity_id],
        )
        if not any([fs, ff, ss, sf]):
            return rels

        return [
            rel
            for rel in rels
            if (
                (rel.link == "FS" and fs)
                or (rel.link == "FF" and ff)
                or (rel.link == "SS" and ss)
                or (rel.link == "SF" and sf)
            )
        ]

    @property
    def must_finish_date(self) -> datetime:
        """Must Finish By date set in the Project Date settings"""
        return self._project.get("plan_end_date")

    @cached_property
    def percent_complete(self) -> float:
        od_sum = sum((t.original_duration for t in self.tasks()))
        rd_sum = sum((t.remaining_duration for t in self.tasks()))
        dur_comp = 1 - (rd_sum / od_sum)

        status_cnt = Counter([t.status for t in self.tasks()])
        status_comp = (status_cnt["In Progress"] / 2 + status_cnt["Complete"]) / len(
            self.tasks()
        )

        return mean([dur_comp, status_comp]) * 100

    @property
    def project_start_date(self) -> datetime:
        """Planned start date set in the Project Date settings"""
        return self._project.get("plan_start_date")

    @property
    def remaining_duration(self) -> int:
        """Sum of all activities remaining duration"""
        if self.finish <= self.data_date:
            return 0
        return (self.finish - self.data_date).days

    @property
    def resources(self) -> list[TaskResource]:
        """List of all TaskResource objects included in the schedule"""
        return self._task_resources.values()

    @cached_property
    def start(self) -> datetime:
        """Start date of first activity in schedule"""
        return min((t.start for t in self.tasks()))

    def tasks(
        self,
        not_started: bool = False,
        in_progress: bool = False,
        completed: bool = False,
    ) -> tuple[Task]:
        """List of all Task objects included in the schedule."""
        if not any((not_started, in_progress, completed)):
            return set(self._tasks.values())

        return tuple(
            t
            for t in self._tasks.values()
            if (
                (t.is_not_started and not_started)
                or (t.is_in_progress and in_progress)
                or (t.is_completed and completed)
            )
        )

    @cached_property
    def unit_qty(self) -> ResourceValues:
        return ResourceValues(
            budget=sum((r.unit_qty.budget for r in self.resources)),
            actual=sum((r.unit_qty.actual for r in self.resources)),
            this_period=sum((r.unit_qty.this_period for r in self.resources)),
            remaining=sum((r.unit_qty.remaining for r in self.resources)),
        )

    @property
    def wbs(self) -> list[WbsNode]:
        """List of all Wbs objects included in the schedule"""
        return self._wbs.values()

    @cached_property
    def average_tf(self) -> float:
        return mean(
            (t.total_float for t in self.tasks(not_started=True, in_progress=True))
        )

    @cached_property
    def lowest_tf(self) -> float:
        return min(
            (t.total_float for t in self.tasks(not_started=True, in_progress=True))
        )

    def group_by_float(
        self, near_critical: int = 20, high_float: int = 50
    ) -> dict[str, list[Task]]:
        def parse_tf(tf: int, near_critical: int, high_float: int) -> str:
            if tf <= 0:
                return "Critical"
            if 0 < tf <= near_critical:
                return "Near Critical"
            if near_critical < tf < high_float:
                return "Normal Float"
            if tf >= high_float:
                return "High Float"

        float = {"Critical": 0, "Near Critical": 0, "Normal Float": 0, "High Float": 0}

        for t in self.tasks(in_progress=True, not_started=True):
            float[parse_tf(t.total_float, near_critical, high_float)] += 1

        return float

    def _generate_tasks(self, table: list) -> dict[str, Task]:
        for row in table:
            if row["proj_id"] == self._id:
                row["calendar"] = self._calendars.get(row["clndr_id"])
                row["wbs"] = self._wbs.get(row["wbs_id"])
                yield (row["task_id"], Task(**row))

    def _generate_logic(self, table: list) -> dict[tuple[str, str, str], Relationship]:
        for row in table:
            if row["pred_proj_id"] == self._id and row["proj_id"] == self._id:
                pred = self._tasks.get(row["pred_task_id"])
                succ = self._tasks.get(row["task_id"])
                yield (
                    (pred["task_code"], succ["task_code"], row["pred_type"]),
                    Relationship(pred, succ, **row),
                )

    def _generate_resources(
        self, table: list
    ) -> dict[tuple[str, str, str], TaskResource]:
        for row in table:
            if row["proj_id"] == self._id:
                task: Task = self._tasks.get(row["task_id"])
                row["task"] = task
                row["resource"] = self._resources.get(row["rsrc_id"], {})
                row["calendar"] = self._calendars.get(row["task"]["clndr_id"])
                row["name"] = row["resource"].get("rsrc_name", "")
                row["account"] = self._accounts.get(row["acct_id"])

                res = TaskResource(**row)
                yield res

    def _generate_financials(self, table: list) -> dict[tuple[str, ResourceFinancial]]:
        if table:
            for row in table:
                if row["proj_id"] == self._id:
                    row["period"] = self._fin_dates[row["fin_dates_id"]]
                    row["task_resource"] = self._task_resources[row["taskrsrc_id"]]
                    row["task"] = self._tasks.get(row["task_id"])
                    id = (
                        row["period"].name,
                        row["task"]["task_code"],
                        row["task_resource"].name,
                    )

                    yield (id, ResourceFinancial(**row))

    def _get_project(self, table: list) -> dict:
        for row in table:
            if row["proj_id"] == self._id:
                return row

    def _get_schedule_name(self) -> str:
        for w in self.wbs:
            if w.is_project_node:
                return w["wbs_name"]

        return ""


def _interval_date(date: datetime) -> datetime:
    return datetime(date.year, date.month, 1, 0, 0, 0)


def _date_str(date: datetime) -> str:
    return datetime.strftime(date, "%Y-%m-%d")
