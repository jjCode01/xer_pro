from datetime import datetime
from typing import Any, Optional

# from data.calendar import Calendar
# from data.task import Task
# from data.logic import Relationship
# from data.wbs import Wbs
# from data.resource import TaskResource, ResourceValues

# DATA_TABLES = {
#     # 'ACTVCODE': ('actv_code_id', 'actv_code_type_id', 'actv_code_name', 'short_name', 'seq_num', 'total_assignments'),
#     # 'ACTVTYPE': ('actv_code_type_id', 'actv_short_len', 'seq_num', 'actv_code_type', 'proj_id', 'wbs_id', 'actv_code_type_scope'),
#     'CALENDAR': ('clndr_id', 'clndr_name', 'proj_id', 'clndr_type', 'day_hr_cnt', 'clndr_data'),
#     'FINDATES': ('fin_dates_id', 'fin_dates_name', 'start_date', 'end_date'),
#     'PROJECT': (
#         'proj_id', 'proj_short_name', 'last_recalc_date', 'plan_start_date', 
#         'plan_end_date', 'scd_end_date', 'guid', 'last_fin_dates_id', 'export_flag'),
#     'PROJWBS': (
#         'wbs_id', 'proj_id', 'seq_num', 'proj_node_flag', 'status_code', 
#         'wbs_short_name', 'wbs_name', 'parent_wbs_id'),
#     'RSRC': ('rsrc_id', 'clndr_id', 'rsrc_name', 'rsrc_short_name', 'rsrc_title_name', 'rsrc_type'),
#     'TASK': (
#         'task_id', 'proj_id', 'wbs_id', 'clndr_id', 'phys_complete_pct',
#         'complete_pct_type', 'task_type', 'duration_type', 'status_code', 'task_code',
#         'task_name', 'rsrc_id', 'total_float_hr_cnt', 'free_float_hr_cnt', 'remain_drtn_hr_cnt',
#         'target_drtn_hr_cnt', 'cstr_date', 'act_start_date', 'act_end_date',
#         'late_start_date', 'late_end_date', 'early_start_date', 'early_end_date',
#         'restart_date', 'reend_date', 'target_start_date', 'target_end_date',
#         'rem_late_start_date', 'rem_late_end_date', 'expect_end_date', 'cstr_type', 'suspend_date',
#         'resume_date', 'float_path', 'cstr_date2', 'cstr_type2', 'driving_path_flag'),
#     'TASKPRED': ('task_pred_id', 'task_id', 'pred_task_id', 'proj_id', 'pred_proj_id', 'pred_type', 'lag_hr_cnt'),
#     'TASKRSRC': (
#         'taskrsrc_id', 'task_id', 'proj_id', 'rsrc_id', 'remain_qty', 'target_qty', 
#         'act_ot_qty', 'act_reg_qty', 'target_cost', 'act_reg_cost', 'act_ot_cost', 
#         'remain_cost', 'act_start_date', 'act_end_date', 'restart_date', 'reend_date', 
#         'target_start_date', 'target_end_date', 'rem_late_start_date', 'rem_late_end_date', 
#         'act_this_per_cost'),
#     'TRSRCFIN': ('fin_dates_id', 'taskrsrc_id', 'task_id', 'proj_id', 'act_qty', 'act_cost')
# }
REQUIRED_TABLES = ['CALENDAR', 'PROJECT', 'PROJWBS', 'TASK', 'TASKPRED',]

REQUIRED_TABLE_PAIRS = {
    'TASKFIN': 'FINDATES',
    'TRSRCFIN': 'FINDATES',
    'TASKRSRC': 'RSRC',
    'TASKMEMO': 'MEMOTYPE',
    'ACTVCODE': 'ACTVTYPE',
    'TASKACTV': 'ACTVCODE',
}

def _create_table(table: str) -> dict[str, list[dict]]:
    rows = table.split('\r\n')
    name = rows.pop(0).strip()
    cols = rows.pop(0).split('\t')[1:]
    data = [tuple(zip(cols, row.split('\t')[1:])) for row in rows if row]
    return {name: [{label: set_data_type(label, val) 
                    for label, val in item}
                    for item in data]}

def parse_xer_file(file: str) -> dict[str, list[dict]]:
    """Parses a .xer file into a dictionary of the schedule data tables

    Args:
        file (str): .xer file

    Returns:
        dict: Dictionary of the schedule data tables
    """
    return {name: rows for table in file.split('%T\t')[1:] 
            for name, rows in _create_table(table).items()}

# class Schedule:
#     def __init__(self, proj_id: str, **tables) -> None:
#         self._id = proj_id
#         self._project = self._get_project(tables.get('PROJECT', []))
#         self._calendars = {cal['clndr_id']: Calendar(**cal)
#                           for cal in tables.get('CALENDAR', {})}

#         self._wbs = {wbs['wbs_id']: Wbs(**wbs)
#                     for wbs in tables.get('PROJWBS', {})
#                     if wbs['proj_id'] == proj_id}
#         self.name = self._get_schedule_name()

#         self._tasks = {id: task for id, task in self._generate_tasks(tables.get('TASK', []))}
#         self._logic = {id: rel for id, rel in self._generate_logic(tables.get('TASKPRED', []))}
#         self._resources = {r['rsrc_id']: r for r in tables.get('RSRC', [])}
#         self._task_resources = {id: res for id, res in self._generate_resources(tables.get('TASKRSRC', []))}

#         self._task_code_to_id_map = {t['task_code']: t['task_id'] for t in self.tasks}
    
#     def __str__(self) -> str:
#         return self.name

#     def _generate_tasks(self, table: list) -> dict[str, Task]:
#         for row in table:
#             if row['proj_id'] == self._id:
#                 row['calendar'] = self._calendars.get(row['clndr_id'])
#                 yield (row['task_id'], Task(**row))

#     def _generate_logic(self, table: list) -> dict[tuple[str, str, str], Relationship]:
#         for row in table:
#             if row['pred_proj_id'] == self._id and row['proj_id'] == self._id:
#                 pred = self._tasks.get(row['pred_task_id'])
#                 succ = self._tasks.get(row['task_id'])
#                 link = row['pred_type'][-2:]
#                 lag = int(row['lag_hr_cnt']) / 8
#                 yield ((pred['task_code'], succ['task_code'], row['pred_type']),
#                         Relationship(pred, succ, link , lag))

#     def _generate_resources(self, table: list) -> dict[tuple[str, str, str], TaskResource]:
#         for row in table:
#             if row['proj_id'] == self._id:
#                 row['task'] = self._tasks.get(row['task_id'])
#                 resource = self._resources.get(row['rsrc_id'], {})
#                 row['calendar'] = self._calendars.get(resource['clndr_id']) if resource else self._calendars.get(row['task']['clndr_id'])
#                 row['name'] = resource.get('rsrc_name', '')
#                 row['account'] = "" #### Need to work on this

#                 yield ((row['task']['task_code'], row['name'], row['account']),
#                        TaskResource(**row))
    
#     def _get_project(self, table: list) -> dict:
#         for row in table:
#             if row['proj_id'] == self._id:
#                 return row

#     def _get_schedule_name(self) -> str:
#         for w in self.wbs:
#             if w.is_project_node:
#                 return w['wbs_name']

#         return ""

#     @property
#     def data_date(self) -> datetime:
#         """Schedule Data Date

#         Returns:
#             datetime: Schedule Data Date
#         """
#         return self._project.get('last_recalc_date')

#     @property
#     def project_start_date(self) -> datetime:
#         """Planned start date set in the Project Date settings

#         Returns:
#             datetime: Planned start date
#         """
#         return self._project.get('plan_start_date')

#     @property
#     def schedule_start_date(self) -> datetime:
#         """Start date of first activity in schedule

#         Returns:
#             datetime: Start date of first activity
#         """
#         return min((t.start for t in self.tasks))

#     @property
#     def schedule_finish_date(self) -> datetime:
#         """Finish date of last activity in schedule

#         Returns:
#             datetime: Finish date of last activity
#         """
#         return self._project.get('scd_end_date')

#     @property
#     def must_finish_date(self) -> datetime:
#         """Must Finish By date set in the Project Date settings

#         Returns:
#             datetime: Must Finish By date
#         """
#         return self._project.get('plan_end_date')

#     @property
#     def tasks(self) -> list[Task]:
#         """List of all Task objects included in the schedule.

#         Returns:
#             list[Task]: All Task objects
#         """
#         return self._tasks.values()

#     @property
#     def logic(self) -> list[Relationship]:
#         """List of all Relationship objects included in the schedule

#         Returns:
#             list[Relationship]: All Relationship objects
#         """
#         return self._logic.values()

#     @property
#     def calendars(self) -> list[Calendar]:
#         """List of all Calendar objects included in the schedule.

#         Returns:
#             list[Calendar]: All Calendar objects
#         """
#         return self._calendars.values()

#     @property
#     def wbs(self) -> list[Wbs]:
#         """List of all Wbs objects included in the schedule.

#         Returns:
#             list[Wbs]: All Wbs objects
#         """
#         return self._wbs.values()

#     @property
#     def resources(self) -> list[TaskResource]:
#         """List of all TaskResource objects included in the schedule.

#         Returns:
#             list[TaskResource]: All TaskResource objects
#         """
#         return self._task_resources.values()

#     @property
#     def cost(self) -> ResourceValues:
#         return ResourceValues(
#             budget=sum((r.cost.budget for r in self.resources)),
#             actual=sum((r.cost.actual for r in self.resources)),
#             this_period=sum((r.cost.this_period for r in self.resources)),
#             remaining=sum((r.cost.remaining for r in self.resources)))

#     @property
#     def unit_qty(self) -> ResourceValues:
#         return ResourceValues(
#             budget=sum((r.unit_qty.budget for r in self.resources)),
#             actual=sum((r.unit_qty.actual for r in self.resources)),
#             this_period=sum((r.unit_qty.this_period for r in self.resources)),
#             remaining=sum((r.unit_qty.remaining for r in self.resources)))

#     def group_by_status(self) -> dict[str, list[Task]]:
#         return {'Not Started': [t for t in self.tasks if t.not_started],
#                 'In Progress': [t for t in self.tasks if t.in_progress],
#                 'Completed': [t for t in self.tasks if t.completed]}

#     def filter_by_status(self, not_started: bool, in_progress: bool, completed: bool) -> list[Task]:
#         return [t for t in self.tasks if
#                 (t.not_started and not_started) or
#                 (t.in_progress and in_progress) or
#                 (t.completed and completed)]

#     def group_by_float(self, near_critical: int = 20, high_float: int = 50) -> dict[str, list[Task]]:
#         float = {'Critical': list(),
#                  'Near Critical': list(),
#                  'Normal Float': list(),
#                  'High Float': list()}

#         for t in self.tasks:
#             if not t.completed:
#                 tf = t.total_float
#                 if tf <= 0:
#                     float['Critical'].append(t)
#                     continue
#                 if 0 < tf <= near_critical:
#                     float['Near Critical'].append(t)
#                     continue
#                 if near_critical < tf <= high_float:
#                     float['Normal Float'].append(t)
#                     continue
#                 if tf > high_float:
#                     float['High Float'].append(t)
        
#         return float


#     def filter_by_float(self, **float) -> list[Task]:
#         open_tasks = [t for t in self.tasks if not t.completed]
#         if float.keys() >= {'high', 'low'}:
#             low, high = min(float['high'], float['low']), max(float['high'], float['low'])
#             return [t for t in open_tasks if low <= t.total_float <= high]

#         if 'low' in float:
#             return [t for t in open_tasks if float['low'] <= t.total_float]

#         if 'high' in float:
#             return [t for t in open_tasks if t.total_float <= float['high']]

#         if 'equals' in float:
#             return [t for t in open_tasks if t.total_float == float['equals']]

#         return []

#     def group_by_link(self) -> dict[str, list[Relationship]]:
#         links = {'FS': list(),
#                  'FF': list(),
#                  'SS': list(),
#                  'SF': list(),}

#         for rel in self.logic:
#             links[rel.link].append(rel)

#         return links

# def find_xer_errors(tables: dict) -> Optional[list]:
#     errors = []

#     # Check for tables required to be in the XER
#     for t in REQUIRED_TABLES:
#         if not t in tables:
#             errors.append(f'Missing Required Table {t}')

#     # Check for required table pairs
#     for t1, t2 in REQUIRED_TABLE_PAIRS.items():
#         if t1 in tables and not t2 in tables:
#             errors.append(f'Missing Table {t2} Required for Table {t1}')

#     # check for multiple schedules
#     export_xer_projects = tuple(t for t in tables.get('PROJECT', []) if t['export_flag'])
#     if len(export_xer_projects) > 1:
#         errors.append(f'XER Contains {len(export_xer_projects)} Schedules')

#     # check for tasks assigned to an invalid calendar (not included in CALENDAR TABLE)
#     cal_ids = [c['clndr_id'] for c in tables.get('CALENDAR', [])]
#     tasks_with_invalid_calendar = [t for t in tables.get('TASK', []) if not t['clndr_id'] in cal_ids]
#     if tasks_with_invalid_calendar:
#         invalid_cal_count = len(set([t["clndr_id"] for t in tasks_with_invalid_calendar]))
#         errors.append(f'XER is Missing {invalid_cal_count} Calendars Assigned to {len(tasks_with_invalid_calendar)} Tasks')

#     if not errors:
#         return None

#     return errors

def set_data_type(key: str, val: str) -> Any:
    if not val or val == "":
        return None
    if key.endswith(('_date', '_date2')):
        return datetime.strptime(val, '%Y-%m-%d %H:%M')
    if key.endswith('_num'):
        return int(val)
    if key.endswith(('_cnt', '_qty', '_cost')):
        return float(val)
    if key.endswith('_flag'):
        return val == 'Y'

    return val
