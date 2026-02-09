"""
Health Monitor Service
"""

import logging
import asyncio

logger = logging.getLogger(__name__)

class HealthMonitor:
    def __init__(self):
        self.running = False
        
    async def start(self):
        self.running = True
        
    async def stop(self):
        self.running = False
