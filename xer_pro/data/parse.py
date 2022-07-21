from datetime import datetime
from typing import Any, Optional


REQUIRED_TABLES = ['CALENDAR', 'PROJECT', 'PROJWBS', 'TASK', 'TASKPRED']

REQUIRED_TABLE_PAIRS = {
    'TASKFIN': 'FINDATES',
    'TRSRCFIN': 'FINDATES',
    'TASKRSRC': 'RSRC',
    'TASKMEMO': 'MEMOTYPE',
    'ACTVCODE': 'ACTVTYPE',
    'TASKACTV': 'ACTVCODE',
}


def _create_table(table: str) -> dict[str, list[dict]]:
    lines = table.split('\r\n')
    name = lines.pop(0).strip()
    cols = lines.pop(0).split('\t')[1:]
    rows = [
        tuple(zip(cols, line.split('\t')[1:]))
        for line in lines
        if line and not line.startswith('%E')]

    table = {
        name: [
            {label: _set_data_type(label, value)
             for label, value in row} for row in rows
        ]}

    return table


def parse_xer_file(file: str) -> dict[str, list[dict]]:
    """Parses a .xer file into a dictionary of the schedule data tables

    Args:
        file (str): .xer file

    Returns:
        dict: Dictionary of the schedule data tables
    """
    tables = {
        name: rows
        for table in file.split('%T\t')[1:]
        for name, rows in _create_table(table).items()}

    return tables


def find_xer_errors(tables: dict) -> Optional[list]:
    errors = []

    # Check for tables required to be in the XER
    for t in REQUIRED_TABLES:
        if t not in tables:
            errors.append(f'Missing Required Table {t}')

    # Check for required table pairs
    for t1, t2 in REQUIRED_TABLE_PAIRS.items():
        if t1 in tables and t2 not in tables:
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
        errors.append(
            f'XER is Missing {invalid_cal_count} Calendars Assigned to {len(tasks_with_invalid_calendar)} Tasks')

    if not errors:
        return None

    return errors


def _set_data_type(key: str, val: str) -> Any:
    """Set the data type of a value based on its column label

    Args:
        key (str): column label
        val (str): data value

    Returns:
        Any: data value set to correct data type
    """
    if not val or val == "":
        return None
    if key.endswith(('_date', '_date2')):
        return datetime.strptime(val, '%Y-%m-%d %H:%M')
    if key.endswith('_num'):
        return int(val)
    if key.endswith(('_cnt', '_qty', '_cost', '_pct')):
        return float(val)
    if key.endswith('_flag'):
        return val == 'Y'

    return val
