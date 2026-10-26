# Blockchain System

A small Flask-based blockchain demonstration. Each node runs as a separate HTTP
server, keeps its own blockchain, and can share transactions and mined blocks
with registered peer nodes.

## Requirements and installation

- Python 3.13 (or another compatible Python 3 version)
- Dependencies listed in [`requirements.txt`](./requirements.txt): Flask and Requests

From the project root, create and activate a virtual environment, then install
the dependencies:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If PowerShell does not allow activation scripts, invoke the environment's
Python directly instead:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Start the nodes

Open three PowerShell terminals in the project root. Start one node in each
terminal:

```powershell
.\.venv\Scripts\python.exe -m blockchain_system.node --port 5001
```

```powershell
.\.venv\Scripts\python.exe -m blockchain_system.node --port 5002
```

```powershell
.\.venv\Scripts\python.exe -m blockchain_system.node --port 5003
```

Each node listens on `127.0.0.1` by default. Leave the terminals running while
using the nodes. To connect all three as peers, run the following from another
PowerShell terminal:

```powershell
$nodes = @(
    @{ port = 5001; peers = @(5002, 5003) },
    @{ port = 5002; peers = @(5001, 5003) },
    @{ port = 5003; peers = @(5001, 5002) }
)

foreach ($node in $nodes) {
    foreach ($peerPort in $node.peers) {
        $body = @{ node_address = "http://127.0.0.1:$peerPort" } | ConvertTo-Json
        Invoke-RestMethod -Method Post `
            -Uri "http://127.0.0.1:$($node.port)/nodes/register" `
            -ContentType "application/json" -Body $body
    }
}
```

Register peers before creating transactions or mining if you want the changes
to be broadcast automatically to the other nodes.

## Create a transaction

Send a JSON `POST` request to any node's `/transaction` endpoint. For example,
to add a transaction through node 5001:

```powershell
$transaction = @{
    sender   = "Alice"
    receiver = "Bob"
    amount   = 25
} | ConvertTo-Json

Invoke-RestMethod -Method Post `
    -Uri "http://127.0.0.1:5001/transaction" `
    -ContentType "application/json" -Body $transaction
```

The node adds a timestamp and broadcasts the transaction to its registered
peers. To inspect pending transactions on a node:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:5001/transactions"
```

## Mine pending transactions

Post a miner name to `/mine` on a node with pending transactions:

```powershell
$miner = @{ miner = "Alice" } | ConvertTo-Json

Invoke-RestMethod -Method Post `
    -Uri "http://127.0.0.1:5001/mine" `
    -ContentType "application/json" -Body $miner
```

The node mines its pending transactions into a block and broadcasts the block
to its registered peers. A node with no pending transactions returns an error
message instead of mining an empty block.

## Synchronize nodes

To ask a node to check its peers and adopt a longer valid blockchain, call
`/nodes/resolve`:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:5001/nodes/resolve"
```

Repeat for other nodes as needed, changing the port. Synchronization compares
valid chain lengths and replaces the node's chain only when a longer valid
chain is found.

## View a node's blockchain

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:5001/blockchain"
```

Change the port to inspect another node.
