from datetime import datetime

class FinancialPeriod:
    def __init__(self, **kwargs) -> None:
        self._attr = kwargs

    @property
    def name(self) -> str:
        return self._attr['fin_dates_name']

    @property
    def start(self) -> datetime:
        return self._attr['start_date']
        
    @property
    def finish(self) -> datetime:
        return self._attr['end_date']


class ResourceFinancial:
    def __init__(self, **kwargs) -> None:
        self._attr = kwargs

    @property
    def cost(self) -> float:
        return self._attr['act_cost']

    @property
    def qty(self) -> float:
        return self._attr['act_qty']

    @property
    def period(self) -> FinancialPeriod:
        return self._attr['period']

    

