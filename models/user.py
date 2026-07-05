from dataclasses import dataclass
from typing import Optional


@dataclass
class Student:
    id: int
    name: str
    email: str
    phone: Optional[str]
    is_active: bool
