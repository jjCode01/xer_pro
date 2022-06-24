from datetime import datetime
from typing import Any, Optional

from data.sched_calendar import SchedCalendar, rem_hours_per_day
from data.wbs import Wbs
# from services.calendar_services import rem_hours_per_day

STATUS = {
    'TK_NotStart': 'Not Started',
    'TK_Active': 'In Progress',
    'TK_Complete': 'Complete'
}

PERCENTTYPES = {
    'CP_Phys': 'Physical',
    'CP_Drtn': 'Duration',
    'CP_Units': 'Unit'
}

TASKTYPES = {
    'TT_Mile': 'Start Milestone',
    'TT_FinMile': 'Finish Milestone',
    'TT_LOE': 'Level of Effort',
    'TT_Task': 'Task Dependent',
    'TT_Rsrc': 'Resource Dependent',
    'TT_WBS': 'WBS Summary'
}

CONSTRAINTTYPES = {
    'CS_ALAP': 'As Late as Possible',
    'CS_MEO': 'Finish On',
    'CS_MEOA': 'Finish on or After',
    'CS_MEOB': 'Finish on or Before',
    'CS_MANDFIN': 'Mandatory Finish',
    'CS_MANDSTART': 'Mandatory Start',
    'CS_MSO': 'Start On',
    'CS_MSOA': 'Start On or After',
    'CS_MSOB': 'Start On or Before',
}

class Task:
    def __init__(self, **kwargs) -> None:
        self._attr = kwargs

    def __eq__(self, o: object) -> bool:
        return self._attr['task_code'] == o._attr['task_code']

    def __getitem__(self, name: str):
        return self._attr[name]

    def __hash__(self) -> int:
        return hash(self._attr['task_code'])

    def __str__(self) -> str:
        return f'{self["task_code"]} - {self["task_name"]}'

    @property
    def activity_id(self) -> str:
        return self._attr.get('task_code')

    @property
    def calendar(self) -> SchedCalendar:
        return self._attr.get('calendar')

    @calendar.setter
    def calendar(self, calendar: SchedCalendar):
        if not isinstance(calendar, SchedCalendar):
            raise ValueError("Value Error: argument must be a Calendar object")

        self._attr['calendar'] = calendar

    @property
    def finish(self) -> datetime:
        if self.is_completed:
            return self._attr['act_end_date']

        return self._attr['early_end_date']

    @property
    def free_float(self) -> Optional[int]:
        if self.is_completed:
            return None
        
        return int(self._attr['free_float_hr_cnt'] / 8)
        
    @property
    def is_completed(self) -> bool:
        return self._attr.get('status_code') == 'TK_Complete'
    
    @property
    def is_critical(self) -> bool:
        return (not self.completed and
                self._attr.get('total_float_hr_cnt') <= 0)

    @property
    def is_in_progress(self) -> bool:
        return self._attr.get('status_code') == 'TK_Active'

    @property
    def is_loe(self) -> bool:
        return self.__attr.get('task_type') == 'TT_LOE'
    
    @property
    def is_longest_path(self) -> bool:
        return self._attr.get('driving_pathflag')

    @property
    def is_milestone(self) -> bool:
        return self._attr.get('task_type').endswith('Mile')

    @property
    def is_not_started(self) -> bool:
        return self._attr.get('status_code') == 'TK_NotStart'
    
    @property
    def is_open(self) -> bool:
        return self._attr.get('status_code') != 'TK_Complete'

    @property
    def late_finish(self) -> Optional[datetime]:
        return self._attr['late_end_date']

    @property
    def late_start(self) -> Optional[datetime]:
        return self._attr['late_start_date']

    @property
    def name(self) -> str:
        return self._attr.get('task_name')

    @property
    def original_duration(self) -> int:
        return int(self._attr['target_drtn_hr_cnt'] / 8)

    @property
    def remaining_duration(self) -> int:
        return int(self._attr['remain_drtn_hr_cnt'] / 8)

    @property
    def start(self) -> datetime:
        if self.is_not_started:
            return self._attr['early_start_date']

        return self._attr['act_start_date']

    @property
    def status(self) -> str:
        return STATUS[self._attr.get('status_code')]

    @property
    def total_float(self) -> Optional[int]:
        if self.is_completed:
            return None
        
        return int(self._attr['total_float_hr_cnt'] / 8)

    @property
    def wbs(self) -> Optional[Wbs]:
        return self._attr.get('wbs')

    @wbs.setter
    def wbs(self, wbs_node: Wbs):
        if not isinstance(wbs_node, Wbs):
            raise ValueError("Value Error: argument must be a Wbs object")

        self._attr['wbs'] = wbs_node

    def get_rem_work_days(self) -> list[tuple[datetime, float]]:
        if self.completed:
            return []

        if not self.calendar:
            return []

        return rem_hours_per_day(
            self.calendar,
            self._kwargs['restart_date'],
            self._kwargs['reend_date'])