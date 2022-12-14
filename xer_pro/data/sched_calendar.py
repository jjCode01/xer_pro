"""
xer_calendar.py

Represents Calendar object parsed from an .xer file generated by
Primavera P6.
"""

from datetime import datetime, timedelta, time
import re
from dataclasses import dataclass, field
from typing import Iterator

from xer_pro.services.calendar_services import (
    calc_time_var_hrs,
    conv_excel_date,
    conv_time,
    clean_dates,
    clean_date,
)

CALENDAR_TYPES = {"CA_Base": "Global", "CA_Rsrc": "Resource", "CA_Project": "Project"}

WEEKDAYS = [
    "Sunday",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
]

# Regular Expressions used to parse the Calendar Data
REGEX_WEEKDAYS = (
    r"(?<=0\|\|)[1-7]\(\).+?(?=\(0\|\|[1-7]\(\)|\(0\|\|VIEW|\(0\|\|Exceptions|\)$)"
)
REGEX_SHIFT = r"[sf]\|[0-2]?\d:[0-5]\d\|[sf]\|[0-2]?\d:[0-5]\d"
REGEX_HOUR = r"[0-2]?\d:[0-5]\d"
REGEX_HOL = r"(?<=d\|)\d{5}(?=\)\(\))"
REGEX_EXCEPT = r"(?<=d\|)\d{5}\)\([^\)]{1}.+?\(\)\)\)"

# Reference https://en.wikipedia.org/wiki/ANSI_escape_code#Colors
TERM_COLORS = {
    "CYAN_FG": "\033[38;5;51m",
    "BLUE_FG": "\033[38;5;45m",
    "NATIVE_FG": "\033[m",
}


@dataclass(frozen=True)
class WeekDay:
    """
    A class to represent a weekday.

    ...

    Attributes
    ----------
    week_day: str
        Day of week (Monday, Tuesday, Wednesday, etc...)
    shifts: list
        List of start and stop work times
    hours: int
        Total work hours for the day
    start: time
        Start work time
    finish: time
        Finish work time
    """

    week_day: str
    shifts: list[time] = field(default_factory=list)
    hours: float = field(init=False, default=0)
    start: time = field(init=False, default=time(0, 0, 0, 0))
    finish: time = field(init=False, default=time(0, 0, 0, 0))

    def __post_init__(self):
        """
        Calculate properties after the object has been initialized
        """
        if self.shifts:
            shift_times = [hr for shift in self.shifts for hr in shift]
            object.__setattr__(
                self,
                "hours",
                sum(calc_time_var_hrs(shift[0], shift[1]) for shift in self.shifts),
            )

            object.__setattr__(self, "start", min(shift_times))
            object.__setattr__(self, "finish", max(shift_times))

    def __len__(self) -> int:
        """
        Returns the number of shifts in the workday
        """
        return len(self.shifts)

    def __str__(self) -> str:
        """
        Returns a string representation of a WeekDay object
        """

        clr_cyan = TERM_COLORS["CYAN_FG"]
        clr_native = TERM_COLORS["NATIVE_FG"]
        clr = clr_cyan if self.hours else clr_native

        hour_ct = (
            f"{clr}{self.hours:04.1f}{clr_native}" if self else f"{clr_native}   -"
        )
        hour_wk = (
            f"{clr}{self.start:%I:%M %p}{clr_native} to {clr}{self.finish:%I:%M %p}{clr_native}"
            if self
            else f"{clr_native}Non-work day        "
        )

        return f"{clr}{self.week_day[:3]}{clr_native} | {hour_ct} hrs | {hour_wk}"

    def __bool__(self) -> bool:
        """
        Returns a boolean representation of a WeekDay Object.
        [False] if hours == 0; [True] is hours > 0.

        Returns:
            bool: [True] weekday is a workday [False] weekday is not a workday
        """
        return self.hours != 0


class SchedCalendar:
    """
    A class to represent a schedule Calendar.

    ...

    Attributes
    ----------
    week_day: str
        Day of week (Monday, Tuesday, Wednesday, etc...)
    shifts: list
        List of start and stop work times
    hours: int
        Total work hours for the day
    start: time
        Start work time
    finish: time
        Finish work time

    Methods
    ----------
    is_workday -> bool
        Checks if datetime object is a workday
    iter_workdays -> Iterable
        Yields valid workdays between 2 dates
    remaining_hrs_per_day -> list
        Calculates the remaining work hours per date for a given date range.
        Only returns valid workdays.
    """

    def __init__(self, **kwargs) -> None:
        self._data = kwargs
        self.assignments = 0

    def __getitem__(self, name: str):
        return self._data[name]

    def __eq__(self, o: object) -> bool:
        """
        Compare two Calendar objects and return True if equal, False if not equal.
        """
        return (
            self._data["clndr_name"] == o._data["clndr_name"]
            and self._data["clndr_type"] == o._data["clndr_type"]
        )

    def __hash__(self) -> int:
        """
        Return a hash representation of a Calendar object.
        """
        return hash((self._data["clndr_name"], self._data["clndr_type"]))

    def __str__(self) -> str:
        """
        Return a string representation of a Calendar object.
        """
        return f'{self._data["clndr_name"]} [{self.type}]'

    def print_cal(self) -> str:
        clr_blue = TERM_COLORS["BLUE_FG"]
        clr_native = TERM_COLORS["NATIVE_FG"]

        lines = [f'{clr_blue}{self["clndr_name"]}{clr_native}']
        lines.append(f"Calendar Type:       {clr_blue}{self.type}{clr_native}")
        lines.append(f"Non-work Exceptions: {clr_blue}{len(self.holidays)}{clr_native}")
        lines.append(
            f"Work Exceptions:     {clr_blue}{len(self.work_exceptions)}{clr_native}"
        )

        # Table of weekday objects
        lines.append("\nDay | Hours    | Time Period")
        lines.append(f'{"-"*4}+{"-"*10}+{"-"*22}')
        for day in self.work_week:
            lines.append(f"{day}")
        lines.append(f'{"-"*38}')

        return "\n".join(lines)

    @property
    def name(self) -> str:
        """Returns Calendar Name"""
        return self._data.get("clndr_name")

    @property
    def type(self) -> str:
        """Returns Calendar Type (Project, Global, Resource)"""
        return CALENDAR_TYPES[self._data["clndr_type"]]

    @property
    def work_week(self) -> dict[str, WeekDay]:
        """Returns list of WeekDay objects"""
        if self._data.get("work_week") is None:
            self._data["work_week"] = _parse_work_week(self)

        return self._data["work_week"]

    @property
    def holidays(self) -> list[datetime]:
        """Returns list of non-work days"""
        if self._data.get("holidays") is None:
            self._data["holidays"] = _parse_nonwork_exceptions(self)

        return self._data["holidays"].values()

    @property
    def work_exceptions(self) -> dict[str, WeekDay]:
        """Returns list of work-day exceptions"""
        if self._data.get("exceptions") is None:
            self._data["exceptions"] = _parse_work_exceptions(self)
        return self._data["exceptions"]


def _calc_work_hours(
    clndr: SchedCalendar, date_to_calc: datetime, start_time: time, end_time: time
) -> float:
    """
    Calculate the work hours for a given day based on a start time, end time,
    and work shifts apportioned for that day of the week.

    Internal to class.

    Args:
        date_to_calc (datetime): date to calculate workhours for
        start_time (time): start time for work
        end_time (time): end time for work

    Returns:
        float: work hours for a date
    """
    work_day = _get_workday(clndr, date_to_calc)

    # date is not a workday
    if not work_day:
        return 0.0

    # reassign times if they were passed in the wrong order
    start_time, end_time = min(start_time, end_time), max(start_time, end_time)

    # ensure start and end times do not fall outside the workhours for the Week Day
    start_time = max(start_time, work_day.start)
    end_time = min(end_time, work_day.finish)

    # date is a full day of work
    if start_time == work_day.start and end_time == work_day.finish:
        return round(work_day.hours, 3)

    day_work_hrs = work_day.hours

    for shift in work_day.shifts:
        # start time falls within this shift
        if shift[0] <= start_time < shift[1]:
            day_work_hrs -= calc_time_var_hrs(shift[0], start_time)

            # end time also falls within this shift
            if end_time < shift[1]:
                day_work_hrs -= calc_time_var_hrs(end_time, shift[1])

            continue

        # only end time falls within this shift
        if shift[0] <= end_time <= shift[1]:
            day_work_hrs -= calc_time_var_hrs(end_time, shift[1])
            continue

        # neither start nor end time falls within this shift
        # deduct shift work hours from the day work hours
        day_work_hrs -= calc_time_var_hrs(shift[0], shift[1])

    return round(day_work_hrs, 3)


def _get_workday(cldnr: SchedCalendar, date: datetime) -> WeekDay:
    """
    Get the WeekDay object associated with a date.

    Internal to class.
    """
    clean_date = date.replace(microsecond=0, second=0, minute=0, hour=0)
    if clean_date in cldnr.work_exceptions.keys():
        return cldnr.work_exceptions[clean_date]

    return cldnr.work_week.get(f"{clean_date:%A}")


def _parse_work_week(clndr: SchedCalendar) -> dict[str, WeekDay]:
    """
    Parse work week from Calendar data property.

    Internal to class.
    """
    return {
        WEEKDAYS[int(day[0]) - 1]: _parse_work_day(day)
        for day in _parse_clndr_data(clndr._data["clndr_data"], REGEX_WEEKDAYS)
    }


def _parse_clndr_data(clndr_data: str, reg_ex: str) -> list:
    """
    Searches Calendar data property and returns strings
    matching reg_ex argument.

    Internal to class
    """
    return re.findall(reg_ex, clndr_data)


def _parse_nonwork_exceptions(clndr: SchedCalendar) -> dict[str, datetime]:
    """
    Parse non-workday exceptions from Calendar data property.

    Internal to class.
    """
    nonwork_dict = {}
    for e in _parse_clndr_data(clndr._data["clndr_data"], REGEX_HOL):
        _date = conv_excel_date(int(e))

        # Verify exception is not already a non-work day on the standard calendar
        if clndr.work_week.get(f"{_date:%A}"):
            nonwork_dict[e] = _date

    return nonwork_dict


def _parse_work_exceptions(clndr: SchedCalendar) -> dict[datetime, WeekDay]:
    """
    Parse work-day exceptions from Calendar data property.

    Internal to class.
    """
    exception_dict = {}
    for exception in _parse_clndr_data(clndr._data["clndr_data"], REGEX_EXCEPT):
        _date = conv_excel_date(int(exception[:5]))
        _day = _parse_work_day(exception)

        # Verify exception object is different than standard weekday object
        if _day != clndr.work_week.get(_day.week_day):
            exception_dict[_date] = _day

    return exception_dict


def _parse_work_day(day: str) -> WeekDay:
    """
    Parse WeekDay objects from string representing a work day.

    Internal to class.
    """
    weekday = WEEKDAYS[int(day[0]) - 1]
    shift_hours = sorted([conv_time(hr) for hr in re.findall(REGEX_HOUR, day)])

    shift_hours_tuple = []
    for hr in range(0, len(shift_hours), 2):
        shift_hours_tuple.append((shift_hours[hr], shift_hours[hr + 1]))

    return WeekDay(weekday, shift_hours_tuple)


def is_workday(clndr: SchedCalendar, date_to_check: datetime) -> bool:
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
    if _date in clndr.work_exceptions.keys():
        return True

    return bool(clndr.work_week[f"{date_to_check:%A}"])


def iter_nonwork_exceptions(
    clndr: SchedCalendar, start: datetime, end: datetime
) -> Iterator[datetime]:
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


def iter_workdays(
    clndr: SchedCalendar, start_date: datetime, end_date: datetime
) -> Iterator[datetime]:
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


def rem_hours_per_day(
    clndr: SchedCalendar, start_date: datetime, end_date: datetime
) -> list[tuple[datetime, float]]:
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
    if start_date.replace(microsecond=0, second=0) == end_date.replace(
        microsecond=0, second=0
    ):
        return [(clean_date(start_date), 0.0)]

    # make sure dates were passed in the correct order
    start_date, end_date = min(start_date, end_date), max(start_date, end_date)

    # edge case that start and end dates are equal
    if start_date.date() == end_date.date():
        work_hrs = _calc_work_hours(
            clndr, start_date, start_date.time(), end_date.time()
        )
        return [(clean_date(start_date), round(work_hrs, 3))]

    # Get a list of all workdays between the start and end dates
    date_range = list(iter_workdays(clndr, start_date, end_date))

    # edge cases that only 1 valid workday between start date and end date
    # these may never actually occur since the dates are pulled directly from the schedule
    # did not find any case where these occur in testing, but leaving it just in case
    if len(date_range) == 1 and end_date.date() > start_date.date():
        if start_date.date() == date_range[0].date():
            work_day = _get_workday(clndr, start_date)
            work_hrs = _calc_work_hours(
                clndr, start_date, start_date.time(), work_day.finish
            )
            return [(clean_date(start_date), round(work_hrs, 3))]

        if end_date.date() == date_range[0].date():
            work_day = _get_workday(clndr, end_date)
            work_hrs = _calc_work_hours(
                clndr, end_date, work_day.start, end_date.time()
            )
            return [(clean_date(end_date), round(work_hrs, 3))]

        work_day = _get_workday(clndr, date_range[0])
        return [(clean_date(date_range[0]), round(work_day.hours, 3))]

    # cases were multiple valid workdays between start and end date
    # initialize hours with start date
    rem_hrs = [
        (
            clean_date(start_date),
            round(
                _calc_work_hours(
                    clndr,
                    date_to_calc=start_date,
                    start_time=start_date.time(),
                    end_time=_get_workday(clndr, start_date).finish,
                ),
                3,
            ),
        )
    ]

    # loop through 2nd to 2nd to last day in date range
    # these would be a full workday
    for dt in date_range[1 : len(date_range) - 1]:
        if wd := _get_workday(clndr, dt):
            rem_hrs.append((dt, round(wd.hours, 3)))

    # calculate work hours for the last day
    rem_hrs.append(
        (
            clean_date(end_date),
            round(
                _calc_work_hours(
                    clndr,
                    date_to_calc=end_date,
                    start_time=_get_workday(clndr, end_date).start,
                    end_time=end_date.time(),
                ),
                3,
            ),
        )
    )

    return rem_hrs
