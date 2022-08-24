from xer_pro.data.task import Task


class Relationship:
    def __init__(self, pred: Task, succ: Task, **kwargs) -> None:
        self._attr = kwargs
        self.predecessor: Task = pred
        self.successor: Task = succ

    def __eq__(self, other) -> bool:
        return (
            self.predecessor == other.predecessor
            and self.successor == other.successor
            and self.link == other.link
        )

    def __hash__(self) -> int:
        return hash(
            (self.predecessor.activity_id, self.successor.activity_id, self.link)
        )

    def __str__(self) -> str:
        return f"{self.predecessor.activity_id} --> {self.successor.activity_id} [{self.link}:{self.lag}]"

    @property
    def lag(self) -> int:
        return int(self._attr["lag_hr_cnt"] / 8)

    @property
    def link(self) -> str:
        return self._attr["pred_type"][-2:]
