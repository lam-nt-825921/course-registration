from dataclasses import dataclass
from typing import Optional

@dataclass
class Course:
    id: Optional[int]
    code: str
    name: str
    credits: int
    max_slots: int
    registered_slots: int = 0

    def can_register(self) -> bool:
        return self.registered_slots < self.max_slots
