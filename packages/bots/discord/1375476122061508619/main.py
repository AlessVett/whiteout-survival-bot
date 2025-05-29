#!/usr/bin/env python3
"""
Main entry point for the WhiteOut Survival Discord Bot
"""

import sys
import os

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import and run the bot
from src.bot import main
import asyncio

if __name__ == '__main__':
    asyncio.run(main())