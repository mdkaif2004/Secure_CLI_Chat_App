# System Architecture & Technical Specification

**Project:** Secure CLI Peer-to-Peer Chat Application  
**Version:** 1.0.0  
**Status:** Active Prototype  
**Audience:** System Architects, Security Engineers, Developers

---

## 1. Executive Summary

This document provides a comprehensive technical breakdown of the Secure CLI Chat Application. The system is designed to provide **Zero Trust**, **Ephemeral**, and **End-to-End Encrypted (E2EE)** communication between two parties over an untrusted network.

**Core Philosophy:**
*   **Trust No One:** The relay server is treated as a hostile entity.
*   **Leave No Trace:** All state is held in volatile memory (RAM) and aggressively wiped.
*   **Fail Secure:** Any protocol deviation results in immediate session destruction.

---

## 2. High-Level Architecture

The system implements a **Client-Server-Client** topology where the server (Relay) functions strictly as a blind packet forwarder. The intelligence, security, and state management are pushed entirely to the "Edge" (the Clients).

### 2.1 Context Diagram

```mermaid
graph TD
    UserA["User A (Terminal)"] -->|Stdin/Stdout| ClientA[Secure Chat Client A]
    UserB["User B (Terminal)"] -->|Stdin/Stdout| ClientB[Secure Chat Client B]
    
    subgraph "Untrusted Network Zone"
        ClientA <-->|Encrypted WebSocket (TLS)| Relay[Relay Server]
        Relay <-->|Encrypted WebSocket (TLS)| ClientB
    end

    subgraph "Client A Internal Boundary"
        ClientA --> CryptoA[Crypto Module (RAM Only)]
        ClientA --> StateA[State Machine]
    end

    style ClientA fill:#cfc,stroke:#333,stroke-width:2px
    style ClientB fill:#cfc,stroke:#333,stroke-width:2px
    style Relay fill:#f9f,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5
```

---

## 3. Directory Structure & Module Responsibilities

The codebase is organized by domain responsibility. Each module isolates its dependencies to prevent leakage (e.g., UI code never touches raw private keys).

```text
.
├── main.py                  # Entry Point: Initializes CLI and Event Loop.
├── run.sh                   # Bootstrap: Checks Python ver, creates Venv, launches Relay/App.
├── relay_server.py          # Infrastructure: Dumb WebSocket forwarder.
├── core/
│   ├── session_manager.py   # Controller: Orchestrates UI, Net, and Crypto.
│   └── state_machine.py     # Logic: Defines strict app lifecycle.
├── crypto/
│   ├── key_manager.py       # Secrets: Generates/Stores keys in RAM.
│   ├── encryption.py        # Algo: Implements PyNaCl Box (X25519/XSalsa20).
│   └── memory_wiper.py      # Hygiene: overwrite_object() logic.
├── network/
│   └── transport.py         # IO: Async WebSocket handling & JSON framing.
├── security/
│   └── rate_limiter.py      # Protection: Token Bucket anti-spam.
├── ui/
│   └── cli.py               # View: Rich Console & PromptToolkit input loop.
└── utils/
    ├── validators.py        # Safety: Regex checks for inputs.
    └── error_codes.py       # Standards: Int-based error mapping.
```

---

## 4. Component Specifications

### 4.1 Core: Session Manager (`core/session_manager.py`)
*   **Role:** The central nervous system. It connects the `UI` events to `Network` actions and applies `Crypto` transformations.
*   **Key Methods:**
    *   `start_session(room_code)`: Initiates connection to relay.
    *   `perform_handshake()`: Triggers key generation and sends public key.
    *   `on_network_message(payload)`: Routes incoming signals (Handshake vs. Message).
    *   `destroy_session()`: The "Kill Switch". Disconnects socket, wipes keys, kills UI loop.

### 4.2 Crypto: Encryption Handler (`crypto/encryption.py`)
*   **Library:** `PyNaCl` (libsodium binding).
*   **Primitive:** `nacl.public.Box`.
*   **Algorithms:**
    *   **Key Exchange:** X25519 (Elliptic Curve Diffie-Hellman).
    *   **Encryption:** XSalsa20 stream cipher.
    *   **Authentication:** Poly1305 MAC (Message Authentication Code).
*   **Nonce Handling:** `PyNaCl` automatically generates random 24-byte nonces for XSalsa20, prepended to the ciphertext.
*   **Data Flow:** `String` -> `Bytes` -> `Box.encrypt()` -> `Bytes` -> `Base64` -> `Network`.

### 4.3 Network: Transport Layer (`network/transport.py`)
*   **Protocol:** WebSockets (`ws://` or `wss://`).
*   **Framing:** All messages are JSON strings.
*   **Behavior:**
    *   Maintains a persistent connection.
    *   Implements an async listen loop `async for message in websocket`.
    *   Decoupled from logic: It just calls `on_message_callback(dict)` when data arrives.

---

## 5. Protocol Specification (Wire Format)

All network traffic flows through the Relay. The protocol uses strictly typed JSON messages.

### 5.1 Joining a Room
**Direction:** Client -> Relay
```json
{
  "type": "JOIN",
  "room": "ALPHA1"  // Regex: ^[A-Z0-9]{8,16}$
}
```

### 5.2 Peer Discovery (Relay Response)
**Direction:** Relay -> Client
```json
{
  "type": "PEER_FOUND" // Sent when 2nd client joins
}
```

### 5.3 Signaling (General Purpose)
Used for both Key Exchange and Encrypted Data. The Relay blindly forwards these to the *other* peer in the room.

**A. Key Exchange Packet**
```json
{
  "type": "SIGNAL",
  "kind": "KEY_EXCHANGE",
  "key": "<Base64 Encoded 32-byte Curve25519 Public Key>"
}
```

**B. Encrypted Message Packet**
```json
{
  "type": "SIGNAL",
  "kind": "MSG",
  "payload": "<Base64 Encoded Encrypted Blob (Nonce + Ciphertext)>"
}
```

---

## 6. State Machine Lifecycle

The application enforces a strict state flow to prevent logic bugs (e.g., receiving a message before keys are exchanged).

| State | Trigger | Next State | Action |
| :--- | :--- | :--- | :--- |
| `INIT` | App Start | `INPUT_VALIDATION` | Prompt for Room Code |
| `INPUT_VALIDATION`| User Input | `SEARCHING` | Connect to Relay |
| `SEARCHING` | Server Msg (`PEER_FOUND`) | `USER_FOUND` | Trigger Handshake |
| `USER_FOUND` | Internal | `KEY_SETUP` | Generate Keys, Send PubKey |
| `KEY_SETUP` | Net Msg (`KEY_EXCHANGE`) | `CONNECTED` | Compute Shared Secret |
| `CONNECTED` | User Input | `CONNECTED` | Encrypt & Send |
| `ANY` | Network Error / `/quit` | `DISCONNECTED` | - |
| `DISCONNECTED` | Internal | `SESSION_DESTROYED` | Wipe Keys, Exit |

---

## 7. Cryptographic Standard & Security Model

### 7.1 Key Generation
*   **Type:** Ephemeral.
*   **Storage:** Instance variables in `KeyManager` class.
*   **Lifetime:** Bound to the process lifecycle or session duration.
*   **Wiping:** On `destroy_session()`, the `MemoryWiper` class attempts to overwrite the memory locations (though Python's immutable types makes this "best effort" via reference dropping and forced GC).

### 7.2 Message Pipeline
1.  **Input:** User types "Hello".
2.  **Validation:** Length check (max 1000 chars).
3.  **Encoding:** UTF-8 bytes.
4.  **Encryption:** `Box(priv_A, pub_B).encrypt(bytes)`.
    *   Generates 24-byte random Nonce.
    *   Encrypts with XSalsa20.
    *   Computes Poly1305 MAC.
    *   Output: `Nonce || Ciphertext || MAC`.
5.  **Transport Encoding:** Base64 encode the binary blob.
6.  **Transmission:** Send JSON to Relay.

### 7.3 Threat Mitigation
| Attack Vector | Countermeasure |
| :--- | :--- |
| **Relay Snooping** | Relay sees only Base64 blobs. Cannot decrypt without private keys (which never leave clients). |
| **Replay Attacks** | Relay Logic enforces real-time forwarding. Clients could implement a rolling counter inside the encrypted payload (Future Work). |
| **Message Tampering** | Poly1305 MAC check fails on decryption. Client drops packet and alerts user. |
| **Traffic Analysis** | All packets look identical (JSON wrappers). TLS (in Prod) hides metadata. |

---

## 8. Deployment & Scalability

### 8.1 Local / Prototype
*   **Relay:** Runs on `localhost:8765`.
*   **Clients:** Run in separate terminals.
*   **Dependencies:** Minimal (`websockets`, `cryptography`, `rich`, `prompt_toolkit`).

### 8.2 Production Deployment Strategy
1.  **Relay Hosting:**
    *   Containerize `relay_server.py` (Docker).
    *   Orchestrate with Kubernetes for auto-scaling.
    *   Load Balancer (Nginx) terminates SSL (`wss://`) and forwards to containers.
2.  **Client Distribution:**
    *   Package as a single binary using `PyInstaller`.
    *   Sign the binary to prevent tampering.

---

## 9. Developer Guide (How to Reproduce)

### 9.1 Prerequisites
*   Python 3.10+
*   Git

### 9.2 Setup Steps
1.  **Clone:** `git clone <repo_url>`
2.  **Inspect:** Read `run.sh` to understand the boot process.
3.  **Run:** Execute `./run.sh`.
    *   This script creates a `venv`.
    *   Installs `requirements.txt`.
    *   Backgrounds `relay_server.py` (checks port 8765).
    *   Launches `main.py`.

### 9.3 Extension Points
*   **Add Authentication:** Modify `handshake` in `session_manager.py` to include a password hash.
*   **Add File Transfer:** Create a new `kind: FILE_CHUNK` in `transport.py`.
*   **Change Crypto:** Swap `KeyManager` implementation to use `Kyber` (Post-Quantum) if library support exists.

---

## 10. Future Roadmap

1.  **Identity Verification:** Implement "Socialist Millionaire Protocol" (SMP) to verify that both parties know a shared secret without revealing it.
2.  **Obfuscation:** Padding messages to constant length to foil traffic analysis.
3.  **Onion Routing:** Native integration with Tor for IP anonymity.
4.  **Rust Core:** Rewrite `crypto/` and `core/` in Rust (using `PyO3`) for guaranteed memory safety and true zeroization.

---
*End of Specification*