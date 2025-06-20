#!/bin/bash
# Check if Redis is running, and start it if not. Install if missing.

REDIS_CLI=$(command -v redis-cli)
REDIS_SERVER=$(command -v redis-server)

if [ -z "$REDIS_CLI" ] || [ -z "$REDIS_SERVER" ]; then
  echo "redis-cli or redis-server not found in PATH. Attempting to install Redis..."
  if [ -x "$(command -v apt-get)" ]; then
    sudo apt-get update && sudo apt-get install -y redis-server
  elif [ -x "$(command -v yum)" ]; then
    sudo yum install -y redis
  elif [ -x "$(command -v dnf)" ]; then
    sudo dnf install -y redis
  elif [ -x "$(command -v pacman)" ]; then
    sudo pacman -Sy --noconfirm redis
  else
    echo "No supported package manager found. Please install Redis manually."
    exit 1
  fi
  REDIS_CLI=$(command -v redis-cli)
  REDIS_SERVER=$(command -v redis-server)
  if [ -z "$REDIS_CLI" ] || [ -z "$REDIS_SERVER" ]; then
    echo "Redis installation failed. Please install Redis manually."
    exit 1
  fi
fi

# Check if Redis is running
$REDIS_CLI ping > /dev/null 2>&1
if [ $? -eq 0 ]; then
  echo "Redis is already running."
  exit 0
else
  echo "Redis is not running. Starting redis-server..."
  nohup $REDIS_SERVER > redis.log 2>&1 &
  sleep 2
  $REDIS_CLI ping > /dev/null 2>&1
  if [ $? -eq 0 ]; then
    echo "Redis started successfully."
    exit 0
  else
    echo "Failed to start Redis. Check redis.log for details."
    exit 1
  fi
fi
