# Blockchain Network Assignment Report

## 1. Introduction

This project implements a mini blockchain network in Python that models the core principles of a distributed ledger. The system contains a blockchain data structure, proof-of-work mining, transaction broadcasting, multiple independent nodes, and a synchronization mechanism for ledger recovery. The implementation focuses on the mandatory functional requirements from the assignment while keeping the design modular and understandable.

The solution is built as a small, self-contained package that exposes a blockchain core and a Flask-based API for node communication. It supports three nodes running on ports 5001, 5002, and 5003, and demonstrates transaction propagation, block mining, validation, and tamper detection.

## 2. Blockchain Architecture

A blockchain is a linked list of blocks where each block contains a cryptographic hash of the previous block. This design makes the chain resistant to tampering because even a small change to any accepted block invalidates all later blocks if their previous hash references are recomputed.

In this implementation:

- Each block stores an index, timestamp, list of transactions, previous hash, nonce, and current hash.
- Blocks are linked sequentially through the previous_hash field.
- The chain is stored independently on each node.
- Validation ensures every block and every transaction is legitimate before accepting it.

## 3. System Architecture

The system is structured into three layers:

1. Core blockchain layer - stores blocks and validates transactions.
2. Network layer - exposes REST endpoints and handles peer communication.
3. Demonstration layer - starts nodes and simulates a practical network workflow.

The implementation is organized into:

- [blockchain_system/block.py](./blockchain_system/block.py) — block model and hashing logic
- [blockchain_system/blockchain.py](./blockchain_system/blockchain.py) — blockchain logic, validation, mining, and transaction management
- [blockchain_system/node.py](./blockchain_system/node.py) — peer-to-peer API and node behavior
- [blockchain_system/demo.py](./blockchain_system/demo.py) — demonstration script for multi-node testing
- [requirements.txt](./requirements.txt) — dependencies

## 4. Python Implementation

The network is implemented using Python with Flask for HTTP endpoints and requests for inter-node communication. This aligns with the assignment’s recommendation to use Python’s socket, Flask, and requests libraries for a lightweight distributed network.

Key design decisions:

- Use data classes for clean block representation.
- Keep block validation and blockchain operations separate from API routes.
- Keep node logic modular so each node can register peers, broadcast transactions, and listen for incoming blocks.
- Use straightforward REST endpoints that map directly to the assignment requirements.

## 5. Block Structure

Each block contains:

- index: the position of the block in the blockchain
- timestamp: time of creation
- transactions: list of transactions included in the block
- previous_hash: hash of the previous block
- nonce: number used in proof-of-work mining
- current_hash: SHA-256 digest representing the current block payload

The block hash is generated using SHA-256 over a deterministic JSON representation of the block contents. The hash is recalculated at validation time to ensure the data has not been tampered with.

## 6. Transaction Processing

Transactions are represented as dictionaries with fields such as:

```python
{
    "sender": "Alice",
    "receiver": "Bob",
    "amount": 100,
    "timestamp": "2026-10-24T14:36:39.811716+00:00"
}
```

The node can:

- accept a new transaction through the POST /transaction endpoint,
- append it to the pending transaction pool,
- propagate it to all known peers, and
- include it in a mined block.

This follows the required transaction broadcasting flow where all nodes receive the transaction before mining.

## 7. Proof of Work

The implementation uses a simple proof-of-work mechanism in which the block hash must begin with a required number of zeros. The difficulty is set to 4 in the current implementation.

The mining loop is similar to:

```python
while not block.current_hash.startswith("0" * self.difficulty):
    block.nonce += 1
    block.current_hash = block.calculate_hash()
```

This adds computational cost to block creation and prevents trivial fabrication of blocks. While simple, it is suitable for a learning-oriented blockchain network.

## 8. P2P Communication

The network uses a lightweight peer-to-peer design based on HTTP requests:

- Each node keeps a set of known peers.
- Nodes register with one another using /nodes/register.
- Transactions are broadcast using /transaction.
- Newly mined blocks are broadcast using /block/receive.
- Nodes can synchronize by requesting /blockchain information from peers.

This allows independent nodes to operate with local copies of the blockchain while still allowing propagation of new state.

## 9. Consensus/Synchronization Mechanism

Consensus in this implementation is intentionally simple and based on validity and chain length. A node requests another node’s blockchain using /nodes/resolve and then:

1. Validates the chain.
2. Checks whether the candidate chain is longer than the local chain.
3. Replaces the local chain if the incoming chain is valid and longer.

This mirrors a basic longest-chain consensus model without full network-wide voting or complex finality.

## 10. Blockchain Validation

The blockchain validation function checks:

- block hash integrity,
- previous hash linkage,
- proof-of-work compliance,
- transaction validity,
- block ordering and continuity.

If one block is modified, all later blocks become invalid because their previous_hash values no longer match the actual previous block hash. This is the main weakness exploited during tamper testing.

The implementation uses a validation function that repeatedly recalculates hashes and compares them to stored values.

## 11. Security Analysis

The implementation is intentionally simple and therefore has several real security weaknesses. At least five are discussed below:

1. 51% attack: a miner controlling the majority of network hash power can rewrite or dominate the blockchain.
2. Sybil attack: an attacker can create many fake identities to manipulate peer networks and influence consensus.
3. Double-spending: transactions are not verified against account balances, so a user could spend the same funds multiple times.
4. Transaction manipulation: without signatures or digital authorization, any node can forge transactions.
5. Man-in-the-middle attack: traffic between nodes is not encrypted or authenticated, allowing interception or tampering.
6. Node impersonation: peers are registered by address without robust identity checks.
7. Denial-of-service attack: an attacker can spam the network with invalid transactions or requests.
8. Weak authentication: no token, user identity, or permission model is used.
9. Lack of digital signatures: the system cannot verify whether the sender actually authorized a transaction.
10. Private-key management: no cryptographic wallets or secure key storage exist.

These are typical limitations of educational blockchain prototypes and are well understood in real-world blockchain systems.

## 12. Experimental Results

The node network was tested using three independent Python processes on ports 5001, 5002, and 5003.

Observed behavior:

- All nodes successfully registered with each other.
- A transaction from Alice to Bob with amount 100 was broadcast to all nodes.
- All nodes showed the same pending transaction pool before mining.
- Node 5001 successfully mined a new block and broadcast it to peers.
- Each peer accepted the block and extended the chain to length 2.
- Validation confirmed the chain remained valid after legitimate broadcast.
- After manually tampering with a transaction amount and current_hash in a block, the blockchain validation result became invalid.
- Synchronization preserved the correct valid chain and did not replace it with the tampered version.

This matches the assignment’s expected demonstration outcome: the blockchain is valid before tampering and invalid after tampering.

## 13. Limitations

This implementation is intentionally minimal and is not production-ready. Some limitations include:

- Proof-of-work difficulty is fixed and low.
- No wallet system, transaction signatures, or account balances are implemented.
- No secure peer discovery or authentication exists.
- The network is not resilient to hostile or misconfigured peers.
- Synchronization relies on a basic longest-chain rule rather than full distributed consensus.

These constraints are acceptable for a university assignment focused on understanding blockchain fundamentals.

## 14. Conclusion

This project successfully implements a simple blockchain network with block creation, proof-of-work mining, transaction broadcasting, block propagation, chain validation, and basic peer synchronization. The modular architecture makes the core logic readable and easy to follow, which is important for understanding the relationship between distributed ledgers, network communication, and blockchain security.

Although the implementation is intentionally simple, it demonstrates the key concepts central to blockchain systems and satisfies the assignment’s core learning objectives.


## Project Notes

The implementation follows the recommended endpoints:

- /transaction — POST transaction creation
- /transactions — GET pending transactions
- /mine — POST block mining
- /blockchain — GET current blockchain
- /nodes/register — POST node registration
- /nodes/resolve — GET blockchain synchronization
- /block/receive — POST block reception from another node

This matches the assignment requirement and provides a clear API surface for a distributed blockchain network.
