"""StepUpReason value object."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class StepUpReason:
    """Reason for a step-up decision."""

    week: Optional[int] = None
    weight: Optional[float] = None

    @classmethod
    def no_weight(cls, week: int) -> "StepUpReason":
        return cls(week=week)

    @classmethod
    def insufficient_weight_loss(cls, weight: float) -> "StepUpReason":
        return cls(weight=weight)

    @classmethod
    def already_receives(cls) -> "StepUpReason":
        return cls()

    def __str__(self) -> str:
        if self.week is not None:
            return f"No weight for week {self.week}"
        elif self.weight is not None:
            return f"Insufficient weight loss average ({self.weight})"
        return "Already receives meal replacements"
