from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set

import requests
from flask import Flask, jsonify, request

from .block import Block
from .blockchain import Blockchain, is_chain_valid


class BlockchainNode:
    def __init__(self, node_address: str):
        self.node_address = node_address.rstrip("/")
        self.blockchain = Blockchain()
        self.peers: Set[str] = set()

    def register_node(self, node_address: str) -> bool:
        normalized = node_address.rstrip("/")
        if normalized in {self.node_address, ""}:
            return False
        self.peers.add(normalized)
        return True

    def _post_json(self, url: str, payload: Dict[str, Any], relay: bool = False) -> Optional[requests.Response]:
        headers = {"X-Blockchain-Relay": "true"} if relay else {}
        try:
            return requests.post(url, json=payload, headers=headers, timeout=5)
        except requests.RequestException:
            return None

    def _get_json(self, url: str) -> Optional[Dict[str, Any]]:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return response.json()
        except requests.RequestException:
            return None
        return None

    def broadcast_transaction(self, transaction: Dict[str, Any]) -> None:
        for peer in sorted(self.peers):
            self._post_json(f"{peer}/transaction", transaction, relay=True)

    def broadcast_block(self, block: Block) -> None:
        for peer in sorted(self.peers):
            self._post_json(f"{peer}/block/receive", block.to_dict(), relay=True)

    def add_pending_transaction(self, transaction: Dict[str, Any], broadcast: bool = False) -> bool:
        if not transaction or not isinstance(transaction, dict):
            return False
        if not transaction.get("sender") or not transaction.get("receiver"):
            return False
        try:
            amount = float(transaction.get("amount", 0))
        except (TypeError, ValueError):
            return False
        if amount <= 0:
            return False

        already_exists = any(
            existing.get("sender") == transaction.get("sender")
            and existing.get("receiver") == transaction.get("receiver")
            and float(existing.get("amount", 0)) == amount
            and existing.get("timestamp") == transaction.get("timestamp")
            for existing in self.blockchain.pending_transactions
        )
        if not already_exists:
            self.blockchain.pending_transactions.append(transaction)
        if broadcast:
            self.broadcast_transaction(transaction)
        return True

    def create_transaction(self, sender: str, receiver: str, amount: float, broadcast: bool = True) -> Dict[str, Any]:
        transaction = self.blockchain.add_transaction(sender, receiver, amount)
        if broadcast:
            self.broadcast_transaction(transaction)
        return transaction

    def receive_block(self, block_data: Dict[str, Any], broadcast: bool = False) -> bool:
        if not block_data:
            return False
        block = Block.from_dict(block_data)

        if any(existing.current_hash == block.current_hash for existing in self.blockchain.chain):
            return True

        if block.index != len(self.blockchain.chain):
            return False
        if block.previous_hash != self.blockchain.latest_block.current_hash:
            return False
        candidate_chain = list(self.blockchain.chain)
        candidate_chain.append(block)
        if not is_chain_valid(candidate_chain):
            return False

        self.blockchain.chain.append(block)
        self.blockchain.remove_processed_transactions(block.transactions)
        if broadcast:
            self.broadcast_block(block)
        return True

    def mine_block(self, miner_address: str = "node", broadcast: bool = True) -> Optional[Block]:
        block = self.blockchain.mine_pending_transactions(miner_address)
        if block is None:
            return None
        if broadcast:
            self.broadcast_block(block)
        return block

    def resolve_conflicts(self) -> bool:
        best_chain = None
        best_length = len(self.blockchain.chain)

        for peer in sorted(self.peers):
            peer_data = self._get_json(f"{peer}/blockchain")
            if peer_data is None:
                continue
            candidate = Blockchain.from_dict(peer_data)
            if is_chain_valid(candidate) and len(candidate.chain) > best_length:
                best_chain = candidate
                best_length = len(candidate.chain)

        if best_chain is not None:
            self.blockchain = best_chain
            return True
        return False


def create_app(node: BlockchainNode) -> Flask:
    app = Flask(__name__)

    @app.route("/transaction", methods=["POST"])
    def submit_transaction():
        payload = request.get_json(silent=True) or {}
        sender = payload.get("sender")
        receiver = payload.get("receiver")
        amount = payload.get("amount")

        if not sender or not receiver or amount is None:
            return jsonify({"message": "Invalid transaction payload"}), 400

        is_relay = request.headers.get("X-Blockchain-Relay") == "true"
        try:
            transaction = {
                "sender": sender,
                "receiver": receiver,
                "amount": float(amount),
                "timestamp": payload.get("timestamp") or datetime.now(timezone.utc).isoformat(),
            }
            created = node.add_pending_transaction(transaction, broadcast=not is_relay)
            if not created:
                raise ValueError("The transaction is invalid.")
            return jsonify({"message": "Transaction added successfully", "transaction": transaction})
        except ValueError as exc:
            return jsonify({"message": str(exc)}), 400

    @app.route("/transactions", methods=["GET"])
    def list_transactions():
        return jsonify({"transactions": node.blockchain.pending_transactions})

    @app.route("/mine", methods=["POST"])
    def mine():
        payload = request.get_json(silent=True) or {}
        miner = payload.get("miner", "node")
        block = node.mine_block(miner_address=miner, broadcast=True)
        if block is None:
            return jsonify({"message": "No pending transactions to mine."}), 400
        return jsonify({"message": "Block mined successfully", "block": block.to_dict()})

    @app.route("/blockchain", methods=["GET"])
    def blockchain():
        return jsonify(node.blockchain.to_dict())

    @app.route("/nodes/register", methods=["POST"])
    def register_peer():
        payload = request.get_json(silent=True) or {}
        peer_address = payload.get("node_address") or payload.get("address")
        if not peer_address:
            return jsonify({"message": "Missing node address."}), 400
        node.register_node(peer_address)
        return jsonify({"message": "Node registered", "peers": sorted(node.peers)})

    @app.route("/nodes/resolve", methods=["GET"])
    def resolve():
        resolved = node.resolve_conflicts()
        status = "Blockchain synchronized" if resolved else "Blockchain already up to date"
        return jsonify({"message": status, "replaced": resolved, "blockchain": node.blockchain.to_dict()})

    @app.route("/block/receive", methods=["POST"])
    def receive_block_endpoint():
        payload = request.get_json(silent=True) or {}
        if not payload:
            return jsonify({"message": "No block data supplied."}), 400

        is_relay = request.headers.get("X-Blockchain-Relay") == "true"
        accepted = node.receive_block(payload, broadcast=not is_relay)
        if accepted:
            return jsonify({"message": "Block accepted"})
        return jsonify({"message": "Block rejected"}), 400

    return app


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run a blockchain node.")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind to.")
    parser.add_argument("--port", type=int, default=5001, help="Port to bind the node to.")
    args = parser.parse_args()

    node = BlockchainNode(f"http://{args.host}:{args.port}")
    app = create_app(node)
    app.run(host=args.host, port=args.port, debug=False)
