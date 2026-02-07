#!/bin/bash

# Secure Chat Launcher

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$APP_DIR/venv"
PYTHON_BIN="python3"

# 1. Check Python Version
if ! command -v $PYTHON_BIN &> /dev/null; then
    echo "Error: python3 is not installed."
    exit 1
fi

# Simple version check (major.minor)
PY_VERSION=$($PYTHON_BIN -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
MAJOR=$(echo $PY_VERSION | cut -d. -f1)
MINOR=$(echo $PY_VERSION | cut -d. -f2)

if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 10 ]); then
    echo "Error: Python 3.10+ is required. Found $PY_VERSION"
    exit 1
fi

# 2. Create Virtual Environment
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    $PYTHON_BIN -m venv "$VENV_DIR"
fi

# 3. Activate Venv
source "$VENV_DIR/bin/activate"

# 4. Install Dependencies
REQUIREMENTS_FILE="$APP_DIR/requirements.txt"
MARKER_FILE="$VENV_DIR/.installed"

if [ -f "$REQUIREMENTS_FILE" ]; then
    # Check if we need to install dependencies
    if [ ! -f "$MARKER_FILE" ] || [ "$REQUIREMENTS_FILE" -nt "$MARKER_FILE" ]; then
        echo "Installing/Updating dependencies..."
        pip install -q -r "$REQUIREMENTS_FILE"
        touch "$MARKER_FILE"
    fi
fi

# 5. Apply OS-level socket restrictions (MacOS/Linux placeholder)
# In a real high-security scenario, we might use 'sandbox-exec' on macOS or 'unshare' on Linux.
# For this prototype, we rely on the application's strict networking code.

# --- RELAY SERVER CHECK (Auto-start for local prototype) ---
RELAY_PID=""
RELAY_HOST="localhost"
RELAY_PORT="8765"

# Function to check if port is open
check_relay_port() {
    $PYTHON_BIN -c "import socket; s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.settimeout(1); result = s.connect_ex(('$RELAY_HOST', $RELAY_PORT)); s.close(); exit(result)" &> /dev/null
}

if check_relay_port; then
    echo "Local relay detected on port $RELAY_PORT."
else
    echo "Starting local relay server..."
    $PYTHON_BIN "$APP_DIR/relay_server.py" > /dev/null 2>&1 &
    RELAY_PID=$!
    
    # Wait a moment for it to start
    sleep 1
    if ! check_relay_port; then
        echo "Warning: Failed to start local relay. Connection might fail."
    else
        echo "Local relay started (PID: $RELAY_PID)."
    fi
fi

# Cleanup function to kill relay only if we started it
cleanup() {
    if [ -n "$RELAY_PID" ]; then
        echo "Stopping local relay (PID: $RELAY_PID)..."
        kill "$RELAY_PID" 2>/dev/null
    fi
    deactivate
}
trap cleanup EXIT
# -----------------------------------------------------------

# 6. Launch Application
echo "Launching Secure Chat..."
python "$APP_DIR/main.py" "$@"

