from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from copy import deepcopy
from typing import Dict, List

import requests

from .blockchain import Blockchain, is_chain_valid


def wait_for_server(port: int, timeout: float = 10.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            response = requests.get(f"http://localhost:{port}/blockchain", timeout=1)
            if response.status_code == 200:
                return True
        except requests.RequestException:
            pass
        time.sleep(0.2)
    return False


def start_nodes() -> Dict[int, subprocess.Popen[str]]:
    processes: Dict[int, subprocess.Popen[str]] = {}
    for port in (5001, 5002, 5003):
        env = os.environ.copy()
        processes[port] = subprocess.Popen(
            [sys.executable, "-m", "blockchain_system.node", "--port", str(port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
        )
        if not wait_for_server(port):
            raise RuntimeError(f"Node on port {port} failed to start.")
    return processes


def register_peers() -> None:
    peer_map = {
        5001: ["http://localhost:5002", "http://localhost:5003"],
        5002: ["http://localhost:5001", "http://localhost:5003"],
        5003: ["http://localhost:5001", "http://localhost:5002"],
    }

    for node_port, peers in peer_map.items():
        for peer in peers:
            response = requests.post(
                f"http://localhost:{node_port}/nodes/register",
                json={"node_address": peer},
                timeout=5,
            )
            if response.status_code != 200:
                raise RuntimeError(f"Failed to register peer {peer} on node {node_port}: {response.text}")


def show_blockchains() -> List[Dict[str, object]]:
    blockchains = []
    for port in (5001, 5002, 5003):
        response = requests.get(f"http://localhost:{port}/blockchain", timeout=5)
        response.raise_for_status()
        blockchains.append({"port": port, "data": response.json()})
    return blockchains


def run_demo() -> None:
    processes = start_nodes()
    try:
        register_peers()

        transaction_response = requests.post(
            "http://localhost:5001/transaction",
            json={"sender": "Alice", "receiver": "Bob", "amount": 100},
            timeout=5,
        )
        print("Transaction response:", transaction_response.json())

        second_transaction_response = requests.post(
            "http://localhost:5002/transaction",
            json={"sender": "Bob", "receiver": "Charlie", "amount": 50},
            timeout=5,
        )
        print("Transaction response from node 5002:", second_transaction_response.json())

        for port in (5001, 5002, 5003):
            response = requests.get(f"http://localhost:{port}/transactions", timeout=5)
            response.raise_for_status()
            print(f"Node {port} pending transactions: {response.json()['transactions']}")

        mining_response = requests.post(
            "http://localhost:5001/mine",
            json={"miner": "Alice"},
            timeout=10,
        )
        print("Mining response:", mining_response.json())

        for entry in show_blockchains():
            print(f"Node {entry['port']} blockchain length: {len(entry['data']['chain'])}")
            print("Genesis block:")
            print(json.dumps(entry["data"]["chain"][0], indent=2))
            print(json.dumps(entry['data']['chain'][-1], indent=2))

        node_1_data = requests.get("http://localhost:5001/blockchain", timeout=5).json()
        tampered_blockchain = deepcopy(node_1_data)
        tampered_blockchain["chain"][1]["transactions"][0]["amount"] = 999
        tampered_blockchain["chain"][1]["current_hash"] = "tampered"
        mutated = Blockchain.from_dict(tampered_blockchain)
        print("Blockchain validity after tampering:", is_chain_valid(mutated))

        for port in (5001, 5002, 5003):
            sync_response = requests.get(f"http://localhost:{port}/nodes/resolve", timeout=10)
            sync_response.raise_for_status()
            print(f"Node {port} sync result: {sync_response.json()['message']}")

        print("Demo completed successfully.")
    finally:
        for process in processes.values():
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)


if __name__ == "__main__":
    run_demo()
