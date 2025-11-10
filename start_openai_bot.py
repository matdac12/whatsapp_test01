#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Startup script for WhatsApp OpenAI Bot
Loads environment variables and starts the webhook server
"""

import os
import sys
import logging
from pathlib import Path

# Set UTF-8 as default encoding
os.environ['PYTHONIOENCODING'] = 'utf-8'

# Get the directory of this script
script_dir = Path(__file__).parent.absolute()
os.chdir(script_dir)

# Initialize logging early (before loading env vars)
from logging_config import setup_logging
setup_logging(log_level=logging.INFO)
logger = logging.getLogger('startup')

# Load environment variables from .env file
env_file = script_dir / '.env'
if env_file.exists():
    logger.info("Loading environment variables from .env file")
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value
                # Only log debug info for sensitive keys
                if 'TOKEN' in key or 'KEY' in key:
                    logger.debug(f"{key}: {'*' * 10}...")
                else:
                    preview = value[:30] + '...' if len(value) > 30 else value
                    logger.debug(f"{key}: {preview}")
else:
    logger.warning("No .env file found, using system environment variables")

# Verify required environment variables
required_vars = {
    'WHATSAPP_ACCESS_TOKEN': 'WhatsApp access token',
    'WHATSAPP_PHONE_ID': 'WhatsApp phone number ID',
    'OPENAI_API_KEY': 'OpenAI API key',
    'OPENAI_PROMPT_ID': 'OpenAI prompt ID'
}

missing_vars = []
for var, description in required_vars.items():
    if not os.environ.get(var):
        missing_vars.append(f"{var} ({description})")

if missing_vars:
    logger.warning("Missing required environment variables:")
    for var in missing_vars:
        logger.warning(f"  - {var}")
    logger.warning("Please set these in your .env file or environment")
    response = input("\nDo you want to continue anyway? (y/n): ")
    if response.lower() != 'y':
        logger.error("Startup aborted by user")
        sys.exit(1)

# Set default values
os.environ.setdefault('PORT', '3000')
os.environ.setdefault('VERIFY_TOKEN', 'my-verify-token-123')
os.environ.setdefault('OPENAI_MODEL', 'gpt-4.1')

# Log startup information (minimal, professional)
port = os.environ.get('PORT')
model = os.environ.get('OPENAI_MODEL')
logger.info(f"Server starting on http://localhost:{port}")
logger.info(f"OpenAI model: {model}")
logger.debug(f"Verify token: {os.environ.get('VERIFY_TOKEN')}")
logger.debug("Setup instructions:")
logger.debug(f"  1. Run: ngrok http {port}")
logger.debug("  2. Configure WhatsApp webhook with ngrok URL")
logger.debug("  3. Send test message to WhatsApp Business number")

# Import and run the webhook server
try:
    from webhook_openai import app
    app.run(host='0.0.0.0', port=int(port), debug=False, use_reloader=False)
except ImportError as e:
    logger.error(f"Failed to import webhook_openai: {e}")
    logger.error("Install required packages: pip install -r requirements.txt")
    sys.exit(1)
except Exception as e:
    logger.error(f"Server startup failed: {e}")
    sys.exit(1)