from dataclasses import dataclass


@dataclass
class ClassSchedule:
    day_of_week: int
    start_period: int
    end_period: int