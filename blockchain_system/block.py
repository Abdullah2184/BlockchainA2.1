from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List


Transaction = Dict[str, Any]


@dataclass
class Block:
    index: int
    timestamp: float
    transactions: List[Transaction]
    previous_hash: str
    nonce: int = 0
    current_hash: str = field(default="")

    def __post_init__(self) -> None:
        if not self.current_hash:
            self.current_hash = self.calculate_hash()

    def calculate_hash(self) -> str:
        payload = {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": self.transactions,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
        }
        serialized = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": self.transactions,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "current_hash": self.current_hash,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Block":
        return cls(
            index=int(data["index"]),
            timestamp=float(data["timestamp"]),
            transactions=data.get("transactions", []),
            previous_hash=data["previous_hash"],
            nonce=int(data.get("nonce", 0)),
            current_hash=data.get("current_hash", ""),
        )
