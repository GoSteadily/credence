from dataclasses import dataclass
from typing import Any, Dict

from credence.role import Role


@dataclass
class Message:
    "@private"

    index: int
    role: Role
    body: str
    metadata: Dict[str, Any] | None = None
