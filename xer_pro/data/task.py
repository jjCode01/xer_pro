from datetime import datetime
from typing import Optional

from xer_pro.data.sched_calendar import SchedCalendar, rem_hours_per_day
from xer_pro.data.wbs import WbsNode

STATUS = {
    "TK_NotStart": "Not Started",
    "TK_Active": "In Progress",
    "TK_Complete": "Complete",
}

PERCENTTYPES = {"CP_Phys": "Physical", "CP_Drtn": "Duration", "CP_Units": "Unit"}

TASKTYPES = {
    "TT_Mile": "Start Milestone",
    "TT_FinMile": "Finish Milestone",
    "TT_LOE": "Level of Effort",
    "TT_Task": "Task Dependent",
    "TT_Rsrc": "Resource Dependent",
    "TT_WBS": "WBS Summary",
}

CONSTRAINTTYPES = {
    "CS_ALAP": "As Late as Possible",
    "CS_MEO": "Finish On",
    "CS_MEOA": "Finish on or After",
    "CS_MEOB": "Finish on or Before",
    "CS_MANDFIN": "Mandatory Finish",
    "CS_MANDSTART": "Mandatory Start",
    "CS_MSO": "Start On",
    "CS_MSOA": "Start On or After",
    "CS_MSOB": "Start On or Before",
}


class Task:
    def __init__(self, **kwargs) -> None:
        self._attr = kwargs

    def __eq__(self, o: object) -> bool:
        return self._attr["task_code"] == o._attr["task_code"]

    def __getitem__(self, name: str):
        return self._attr[name]

    def __hash__(self) -> int:
        return hash(self._attr["task_code"])

    def __str__(self) -> str:
        return f'{self["task_code"]} - {self["task_name"]}'

    @property
    def activity_id(self) -> str:
        return self._attr.get("task_code")

    @property
    def calendar(self) -> SchedCalendar:
        return self._attr.get("calendar")

    @calendar.setter
    def calendar(self, calendar: SchedCalendar):
        if not isinstance(calendar, SchedCalendar):
            raise ValueError("Value Error: argument must be a Calendar object")

        self._attr["calendar"] = calendar

    @property
    def constraint_prime(self) -> Optional[dict]:
        if (constraint := self._attr["cstr_type"]) is None:
            return None

        return {"type": CONSTRAINTTYPES[constraint], "date": self._attr["cstr_date"]}

    @property
    def constraint_second(self) -> Optional[dict]:
        if (constraint := self._attr["cstr_type2"]) is None:
            return None

        return {"type": CONSTRAINTTYPES[constraint], "date": self._attr["cstr_date2"]}

    @property
    def finish(self) -> datetime:
        if self.is_completed:
            return self._attr["act_end_date"]

        return self._attr["early_end_date"]

    @property
    def free_float(self) -> Optional[int]:
        if self.is_completed:
            return None

        return int(self._attr["free_float_hr_cnt"] / 8)

    @property
    def is_completed(self) -> bool:
        return self._attr.get("status_code") == "TK_Complete"

    @property
    def is_critical(self) -> bool:
        return not self.completed and self._attr.get("total_float_hr_cnt") <= 0

    @property
    def is_in_progress(self) -> bool:
        return self._attr.get("status_code") == "TK_Active"

    @property
    def is_loe(self) -> bool:
        return self._attr.get("task_type") == "TT_LOE"

    @property
    def is_longest_path(self) -> bool:
        return self._attr.get("driving_path_flag")

    @property
    def is_milestone(self) -> bool:
        return self._attr.get("task_type").endswith("Mile")

    @property
    def is_not_started(self) -> bool:
        return self._attr.get("status_code") == "TK_NotStart"

    @property
    def is_open(self) -> bool:
        return self._attr.get("status_code") != "TK_Complete"

    @property
    def late_finish(self) -> Optional[datetime]:
        return self._attr["late_end_date"]

    @property
    def late_start(self) -> Optional[datetime]:
        return self._attr["late_start_date"]

    @property
    def name(self) -> str:
        return self._attr.get("task_name")

    @property
    def original_duration(self) -> int:
        return int(self._attr["target_drtn_hr_cnt"] / 8)

    @property
    def percent_type(self) -> str:
        return PERCENTTYPES[self._attr["complete_pct_type"]]

    @property
    def percent_complete(self) -> float:
        if self._attr["complete_pct_type"] == "CP_Phys":
            return self._attr["phys_complete_pct"] / 100

        if self._attr["complete_pct_type"] == "CP_Drtn":
            if self.is_not_started or self.original_duration == 0:
                return 0.0
            if self.is_completed:
                return 1.0
            if self.remaining_duration >= self.original_duration:
                return 0.0

            return 1 - self.remaining_duration / self.original_duration

        if self._attr["complete_pct_type"] == "CP_Units":
            target_units = (
                self._attr["target_work_qty"] + self._attr["target_equip_qty"]
            )
            if target_units == 0:
                return 0.0
            actual_units = self._attr["act_work_qty"] + self._attr["act_equip_qty"]
            return 1 - actual_units / target_units

    @property
    def remaining_duration(self) -> int:
        return int(self._attr["remain_drtn_hr_cnt"] / 8)

    @property
    def start(self) -> datetime:
        if self.is_not_started:
            return self._attr["early_start_date"]

        return self._attr["act_start_date"]

    @property
    def status(self) -> str:
        return STATUS[self._attr.get("status_code")]

    @property
    def total_float(self) -> Optional[int]:
        if self.is_completed:
            return None

        return int(self._attr["total_float_hr_cnt"] / 8)

    @property
    def type(self) -> str:
        return TASKTYPES[self._attr["task_type"]]

    @property
    def wbs(self) -> Optional[WbsNode]:
        return self._attr.get("wbs")

    @wbs.setter
    def wbs(self, wbs_node: WbsNode):
        if not isinstance(wbs_node, WbsNode):
            raise ValueError("Value Error: argument must be a Wbs object")

        self._attr["wbs"] = wbs_node

    def get_rem_work_days(self) -> list[tuple[datetime, float]]:
        if self.completed:
            return []

        if not self.calendar:
            return []

        return rem_hours_per_day(
            self.calendar, self._kwargs["restart_date"], self._kwargs["reend_date"]
        )
