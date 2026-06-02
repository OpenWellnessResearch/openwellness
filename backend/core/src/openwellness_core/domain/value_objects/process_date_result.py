"""Result of determining a processing date."""

from dataclasses import dataclass

from arrow import Arrow


@dataclass
class ProcessDateResult:
    """Result of determining a processing date."""

    final_date: Arrow
    applied_adjustments: list[str]
