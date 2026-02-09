#!/usr/bin/env python3
"""
Bianca AI Cloud - Main Entry Point
Multi-agent enterprise architecture
"""

import os
import sys
import asyncio
import logging
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class BiancaCloudEnterprise:
    def __init__(self):
        self.running = False
        
    async def startup(self):
        logger.info("BIANCA AI CLOUD ENTERPRISE - Starting...")
        self.running = True
        logger.info("All systems operational!")
            
    async def main_loop(self):
        while self.running:
            try:
                await asyncio.sleep(10)
            except KeyboardInterrupt:
                logger.info("Shutdown requested")
                break
    
    async def shutdown(self):
        logger.info("Initiating graceful shutdown...")
        self.running = False

async def main():
    app = BiancaCloudEnterprise()
    
    try:
        await app.startup()
        await app.main_loop()
    finally:
        await app.shutdown()

if __name__ == "__main__":
    # Check environment variables
    required_env = ["OPENAI_API_KEY", "TELEGRAM_TOKEN"]
    missing = [e for e in required_env if not os.getenv(e)]
    
    if missing:
        logger.error(f"Missing environment variables: {missing}")
        sys.exit(1)
    
    logger.info(f"Starting at {datetime.now()}")
    asyncio.run(main())
