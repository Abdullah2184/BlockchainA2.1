from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .block import Block


def validate_transaction(transaction: Dict[str, Any]) -> bool:
    if not isinstance(transaction, dict):
        return False
    sender = transaction.get("sender")
    receiver = transaction.get("receiver")
    amount = transaction.get("amount")
    if not sender or not receiver:
        return False
    try:
        amount_value = float(amount)
    except (TypeError, ValueError):
        return False
    return amount_value > 0


def is_chain_valid(chain: List[Block] | "Blockchain", difficulty: int = 4) -> bool:
    if isinstance(chain, Blockchain):
        chain_list = chain.chain
        difficulty = chain.difficulty
    else:
        chain_list = chain

    if not chain_list:
        return False

    for index, block in enumerate(chain_list):
        if index == 0:
            if block.previous_hash != "0" * 64:
                return False
            if block.calculate_hash() != block.current_hash:
                return False
            if not block.current_hash.startswith("0" * difficulty):
                return False
            continue

        previous_block = chain_list[index - 1]
        if block.previous_hash != previous_block.current_hash:
            return False
        if block.calculate_hash() != block.current_hash:
            return False
        if not block.current_hash.startswith("0" * difficulty):
            return False

        for transaction in block.transactions:
            if not validate_transaction(transaction):
                return False

    return True


class Blockchain:
    def __init__(self, difficulty: int = 4):
        self.difficulty = difficulty
        self.pending_transactions: List[Dict[str, Any]] = []
        self.chain: List[Block] = [self.create_genesis_block()] #creating first block

    @staticmethod
    def create_genesis_block() -> Block:
        genesis = Block(
            index=0,
            timestamp=0.0,
            transactions=[
                {
                    "sender": "Genesis",
                    "receiver": "System",
                    "amount": 0,
                    "note": "Genesis block",
                }
            ],
            previous_hash="0" * 64,
            nonce=0,
            current_hash="",
        )
        genesis.nonce = 0
        while not genesis.current_hash.startswith("0" * 4):
            genesis.nonce += 1
            genesis.current_hash = genesis.calculate_hash()
        return genesis

    @property
    def latest_block(self) -> Block:
        return self.chain[-1]

    def add_transaction(self, sender: str, receiver: str, amount: float) -> Dict[str, Any]:
        if not sender or not receiver:
            raise ValueError("Transaction sender and receiver are required.")
        if amount <= 0:
            raise ValueError("Transaction amount must be larger than zero.")

        transaction = {
            "sender": sender,
            "receiver": receiver,
            "amount": float(amount),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.pending_transactions.append(transaction)
        return transaction

    def proof_of_work(self, block: Block) -> Block:
        while not block.current_hash.startswith("0" * self.difficulty):
            block.nonce += 1
            block.current_hash = block.calculate_hash()
        return block

    def mine_pending_transactions(self, miner_address: str = "node") -> Optional[Block]:
        if not self.pending_transactions:
            return None

        block = Block(
            index=len(self.chain),
            timestamp=datetime.now(timezone.utc).timestamp(),
            transactions=[tx.copy() for tx in self.pending_transactions],
            previous_hash=self.latest_block.current_hash,
            nonce=0,
        )
        self.proof_of_work(block)
        self.chain.append(block)
        self.pending_transactions = []
        return block

    def remove_processed_transactions(self, transactions: List[Dict[str, Any]]) -> None:
        if not transactions:
            return

        match = []
        for pending in self.pending_transactions:
            for transaction in transactions:
                if (
                    pending.get("sender") == transaction.get("sender")
                    and pending.get("receiver") == transaction.get("receiver")
                    and float(pending.get("amount", 0)) == float(transaction.get("amount", 0))
                    and pending.get("timestamp") == transaction.get("timestamp")
                ):
                    match.append(pending)
                    break

        for item in match:
            if item in self.pending_transactions:
                self.pending_transactions.remove(item)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chain": [block.to_dict() for block in self.chain],
            "pending_transactions": self.pending_transactions,
            "difficulty": self.difficulty,
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "Blockchain":
        blockchain = cls(difficulty=int(payload.get("difficulty", 4)))
        blockchain.chain = [Block.from_dict(block) for block in payload.get("chain", [])]
        blockchain.pending_transactions = payload.get("pending_transactions", [])
        return blockchain

    def replace_chain(self, candidate: "Blockchain") -> bool:
        if not is_chain_valid(candidate, candidate.difficulty):
            return False
        if len(candidate.chain) <= len(self.chain):
            return False
        self.chain = candidate.chain
        self.pending_transactions = candidate.pending_transactions
        return True
