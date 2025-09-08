#!/bin/bash

# Set UTF-8 locale
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
export PYTHONIOENCODING=utf-8

echo "🚀 Starting WhatsApp OpenAI Bot with UTF-8 support"
echo "=================================================="

# Run the Python script with explicit UTF-8 encoding
python3 -X utf8 start_openai_bot.py