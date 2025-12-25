#!/bin/bash
echo "🚀 Starting Xvfb..."
# Start Xvfb in the background on display :99
Xvfb :99 -ac -screen 0 1920x1080x24 -nolisten tcp &
xvfb_pid=$!

# Export the display so Chrome picks it up
export DISPLAY=:99

echo "⏳ Waiting for Xvfb..."
sleep 3

echo "🚀 Starting Uvicorn..."
# Run the application
exec uvicorn main:app --host 0.0.0.0 --port 8000
