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

def find_xer_errors(tables: dict) -> Optional[list]:
    errors = []

    # Check for tables required to be in the XER
    for t in REQUIRED_TABLES:
        if not t in tables:
            errors.append(f'Missing Required Table {t}')

    # Check for required table pairs
    for t1, t2 in REQUIRED_TABLE_PAIRS.items():
        if t1 in tables and not t2 in tables:
            errors.append(f'Missing Table {t2} Required for Table {t1}')

    # check for multiple schedules
    export_xer_projects = tuple(t for t in tables.get('PROJECT', []) if t['export_flag'])
    if len(export_xer_projects) > 1:
        errors.append(f'XER Contains {len(export_xer_projects)} Schedules')

    # check for tasks assigned to an invalid calendar (not included in CALENDAR TABLE)
    cal_ids = [c['clndr_id'] for c in tables.get('CALENDAR', [])]
    tasks_with_invalid_calendar = [t for t in tables.get('TASK', []) if not t['clndr_id'] in cal_ids]
    if tasks_with_invalid_calendar:
        invalid_cal_count = len(set([t["clndr_id"] for t in tasks_with_invalid_calendar]))
        errors.append(f'XER is Missing {invalid_cal_count} Calendars Assigned to {len(tasks_with_invalid_calendar)} Tasks')

    if not errors:
        return None

    return errors

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
