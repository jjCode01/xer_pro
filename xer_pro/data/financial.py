from datetime import datetime


class FinancialPeriod:
    """A class to represent a Financial Period.

    ...

    Attributes
    ----------
    name: str
        Financial Period name
    start: datetime
        Start date for Financial Period
    finish: datetime
        Finish date for Financial Period
    """
    def __init__(self, **kwargs) -> None:
        self._attr = kwargs

    @property
    def name(self) -> str:
        """Name assigned to Financial Period"""
        return self._attr['fin_dates_name']

    @property
    def start(self) -> datetime:
        """Start date for Financial Period"""
        return self._attr['start_date']

    @property
    def finish(self) -> datetime:
        """End date for Fiancial Period"""
        return self._attr['end_date']


class ResourceFinancial:
    """A class to represent financial period data assigned to a Task.

    ...

    Attributes
    ----------
    cost: float
        Actual cost stored for financial period
    qty: float
        Actual unity quantity stored for financial period
    period: FinancialPeriod
        Financial Period object
    """
    def __init__(self, **kwargs) -> None:
        self._attr = kwargs

    @property
    def cost(self) -> float:
        """Actual cost stored for financial period"""
        return self._attr['act_cost']

    @property
    def qty(self) -> float:
        """Actual unit quantity stored for financial period"""
        return self._attr['act_qty']

    @property
    def period(self) -> FinancialPeriod:
        """Financial Period object assigned to data"""
        return self._attr['period']
