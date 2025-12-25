#!/bin/bash

# 1. Clean up potential stale locks
rm -f /tmp/.X99-lock

# 2. Fix for "Machine UUID" crash in some Chrome versions
# Generate a machine-id if it's missing
if [ ! -f /var/lib/dbus/machine-id ]; then
    mkdir -p /var/lib/dbus
    dbus-uuidgen > /var/lib/dbus/machine-id
fi

echo "🚀 Starting Xvfb on :99..."
Xvfb :99 -ac -screen 0 1920x1080x24 -nolisten tcp &
xvfb_pid=$!

export DISPLAY=:99

# 3. Wait for Xvfb to be actually ready
echo "⏳ Waiting for Xvfb to be ready..."
for i in {1..10}; do
    if xdpyinfo -display :99 >/dev/null 2>&1; then
        echo "✅ Xvfb is ready."
        break
    fi
    echo "   ...waiting for display :99 ($i/10)"
    sleep 1
done

echo "🚀 Starting Uvicorn..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
