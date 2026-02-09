#!/usr/bin/env python3
"""
Taxami Bot Premium - Main Entry Point
Cloud deployment ready
"""

import os
import sys
import logging
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    logger.info("🤖 TAXAMI BOT PREMIUM - Starting...")
    
    # Check required environment variables
    required_env = ["TELEGRAM_TOKEN", "OPENAI_API_KEY", "STRIPE_SECRET_KEY"]
    missing = [e for e in required_env if not os.getenv(e)]
    
    if missing:
        logger.error(f"❌ Missing environment variables: {missing}")
        sys.exit(1)
    
    logger.info("✅ Environment variables OK")
    logger.info(f"🚀 Starting Taxami Bot at {datetime.now()}")
    
    try:
        # Import and start the bot
        from taxami_bot_premium import main_loop
        main_loop()
    except Exception as e:
        logger.error(f"❌ Failed to start bot: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
