#!/bin/bash

echo "========================================"
echo "   ASTEROID MINER LAUNCHER"
echo "========================================"
echo ""

python3 launcher.py

if [ $? -ne 0 ]; then
    echo ""
    echo "Error running the game!"
    echo "Make sure Python 3.8+ is installed."
    read -p "Press Enter to exit..."
fi
