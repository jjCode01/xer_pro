from datetime import datetime, timedelta, time

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

