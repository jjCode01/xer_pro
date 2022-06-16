from datetime import datetime, timedelta, time
from importlib.metadata import requires
from typing import Iterator

from data.calendar import Calendar

def calc_time_var_hrs(start: time, end: time, ordered: bool = False) -> float:
    """Calculate the hours between two time objects

    Args:
        start (time): start time
        end (time): end time
        ordered (bool, optional): If False, reorder start and end times if start is greater than end. Defaults to False.

    Returns:
        float: Duration between two times in hours
    """

    if not all(isinstance(t, time) for t in [start, end]):
        raise ValueError("Value Error: Arguments must be a time object")
    
    if not ordered:
        # put dates in proper order so that the smaller date
        # is subtracted from the larger date.
        start, end = min(start, end), max(start, end)

    start_date = datetime.combine(datetime.today(), start)      
    end_date = datetime.combine(datetime.today(), end)

    return round((end_date - start_date).total_seconds() / 3600, 2)

def clean_date(date: datetime) -> datetime:
    """Sets time value to 00:00:00 (12AM)

    Args:
        date (datetime): _description_

    Returns:
        datetime: _description_
    """
    if not isinstance(date, datetime):
        raise ValueError("Value Error: Argument must be a datetime object")

    return date.replace(microsecond=0, second=0, minute=0, hour=0)

def clean_dates(*dates: datetime) -> list[datetime]:
    """Remove time values from a list of datetime objects"""
    return [clean_date(d) for d in dates]

def conv_excel_date(ordinal: int, _epoch0=datetime(1899, 12, 31)) -> datetime:
    """Convert Excel date format to datetime object

    Args:
        ordinal (str): Excel date format
        _epoch0 (datetime, optional): Start date for conversion. Defaults to datetime(1899, 12, 31).

    Returns:
        datetime: Excel date format converted to datetime object
    """
    if ordinal < 0 or not isinstance(ordinal, int):
        raise ValueError("Innappropiate value passed, should be positive integer.")

    # Excel leap year bug, 1900 is not a leap year
    if ordinal >= 60:
        ordinal -= 1

    return (_epoch0 + timedelta(days=ordinal)).replace(
        microsecond=0,
        second=0,
        minute=0,
        hour=0)

def conv_time(time_str: str) -> time:
    """Convert a string representing time into a datetime.time object.

    Args:
        time_str (str): time as string

    Returns:
        time: time as datetime.time object
    """
    return datetime.strptime(time_str, '%H:%M').time()

def is_workday(clndr: Calendar, date_to_check: datetime) -> bool:
    """Checks if a date is a workday in a Calendar object

    Args:
        clndr (Calendar): Calendar used to determine workdays and hours
        date_obj (datetime): date to check

    Raises:
        ValueError: argument is not a datetime object

    Returns:
        bool: [True] is a workday [False] is not a workday
    """

    if not isinstance(date_to_check, datetime):
        raise ValueError("Argument date_to_check must be a datetime object")

    # Clean date to match format stored in holidays and work_exceptions
    _date = clean_date(date_to_check)        

    # date is set as a non-workday in the calendar
    if _date in clndr.holidays:
        return False

    # date is set as workday exception in the calendar
    if _date in clndr._work_exceptions.keys():
        return True
    
    return bool(clndr._work_week[f'{date_to_check:%A}'])

def iter_nonwork_exceptions(clndr: Calendar, start: datetime, end: datetime) -> Iterator[datetime]:
    """Iterate through nonwork exceptions (i.e. holidays) between two dates.

    This is useful for getting nonwork exceptions during the projects period of performance.

    Args:
        clndr (Calendar): Calendar used to determine workdays and hours
        start (datetime): start date
        end (datetime): end date

    Raises:
        ValueError: argument is not a dateime object

    Yields:
        Iterator[datetime]: Valid workday
    """        
    if not isinstance(start, datetime) or not isinstance(end, datetime):
        raise ValueError("Arguments must be a datetime object")

    # Clean start and end dates to remove time values
    cl_dates = clean_dates(start, end)

    check_date = min(cl_dates)
    while check_date <= max(cl_dates):
        if check_date in clndr.holidays:
            yield check_date

        check_date += timedelta(days=1)

def iter_workdays(clndr: Calendar, start_date: datetime, end_date: datetime) -> Iterator[datetime]:
    """Yields valid workdays between 2 dates

    Args:
        clndr (Calendar): Calendar used to determine workdays and hours
        start (datetime): start date
        end (datetime): end date

    Raises:
        ValueError: argument is not a dateime object

    Yields:
        Iterator[datetime]: Valid workdays between 2 dates
    """

    if not isinstance(start_date, datetime) or not isinstance(end_date, datetime):
        raise ValueError("Arguments must be a datetime object")

    # Clean start and end dates to remove time values
    _dates = clean_dates(start_date, end_date)

    check_date = min(_dates)
    while check_date <= max(_dates):
        if is_workday(clndr, check_date):
            yield check_date

        check_date += timedelta(days=1)

def rem_hours_per_day(clndr: Calendar, start_date: datetime, end_date: datetime) -> list[tuple[datetime, float]]:
    """
    Calculate the remaining workhours per day in a given date range.
    Will only return valid workdays in a list of tuples containing the date and workhour values.
    This is usefull for calculating projections like cash flow.

    Args:
        clndr (Calendar): Calendar used to determine workdays and hours
        start_date (datetime): start of date range (inclusive)
        end_date (datetime): end of date range (inclusive)

    Raises:
        ValueError: datetime objects are not passed in as arguments

    Returns:
        list[tuple[datetime, float]]: date and workhour pairs
    """
    if not isinstance(start_date, datetime) or not isinstance(end_date, datetime):
        raise ValueError("Arguments must be a datetime object")
    
    # edge case start date and end date are equal
    if start_date.replace(microsecond=0, second=0) == end_date.replace(microsecond=0, second=0):
        return [(clean_date(start_date), 0.0)]

    # make sure dates were passed in the correct order
    start_date, end_date = min(start_date, end_date), max(start_date, end_date)

    # edge case that start and end dates are equal
    if start_date.date() == end_date.date():
        work_hrs = clndr._calc_work_hours(start_date, start_date.time(), end_date.time())
        return [(clean_date(start_date), round(work_hrs, 3))]

    # Get a list of all workdays between the start and end dates
    date_range = list(iter_workdays(start_date, end_date))

    # edge cases that only 1 valid workday between start date and end date
    # these may never actually occur since the dates are pulled directly from the schedule
    # did not find any case where these occur in testing, but leaving it just in case
    if len(date_range) == 1 and end_date.date() > start_date.date():
        if start_date.date() == date_range[0].date():
            work_day = clndr._get_workday(start_date)
            work_hrs = clndr._calc_work_hours(start_date, start_date.time(), work_day.finish)
            return [(clean_date(start_date), round(work_hrs, 3))]

        if end_date.date() == date_range[0].date():
            work_day = clndr._get_workday(end_date)
            work_hrs = clndr._calc_work_hours(end_date, work_day.start, end_date.time())
            return [(clean_date(end_date), round(work_hrs, 3))]

        work_day = clndr._get_workday(date_range[0])
        return [(clean_date(date_range[0]), round(work_day.hours, 3))]

    # cases were multiple valid workdays between start and end date
    # initialize hours with start date
    rem_hrs = [(clean_date(start_date),
                round(clndr._calc_work_hours(
                    date_to_calc=start_date,
                    start_time=start_date.time(),
                    end_time=clndr._get_workday(start_date).finish), 3))]

    # loop through 2nd to 2nd to last day in date range
    # these would be a full workday
    for dt in date_range[1:len(date_range)-1]:
        if (wd := clndr._get_workday(dt)):
            rem_hrs.append((dt, round(wd.hours, 3)))

    # calculate work hours for the last day
    rem_hrs.append((clean_date(end_date),
                    round(clndr._calc_work_hours(
                        date_to_calc=end_date,
                        start_time=clndr._get_workday(end_date).start,
                        end_time=end_date.time()), 3)))

    return rem_hrs