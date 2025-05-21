from dataclasses import dataclass
from typing import Any, Dict

from credence.role import Role


@dataclass
class Message:
    "@private"

    role: Role
    body: str
    index: int = 0
    metadata: Dict[str, Any] | None = None
