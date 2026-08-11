"""
System Monitor for Phase 8.
Handles monitoring of pipeline execution, metrics collection, and health checks.
"""
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
from utils.logger import get_logger

logger = get_logger(__name__)


class SystemMonitor:
    """
    Monitors system health and pipeline execution metrics.
    Can be extended to collect real-time metrics, health checks, etc.
    """

    def __init__(self):
        """Initialize the system monitor."""
        self._running = False
        self._start_time: Optional[datetime] = None
        self.metrics: Dict[str, Any] = {}
        logger.debug("SystemMonitor initialized")

    async def start(self):
        """Start the monitoring system."""
        if self._running:
            logger.warning("SystemMonitor is already running")
            return

        self._running = True
        self._start_time = datetime.utcnow()
        logger.info("SystemMonitor started")

    async def stop(self):
        """Stop the monitoring system."""
        if not self._running:
            logger.warning("SystemMonitor is not running")
            return

        self._running = False
        # Log final metrics
        if self._start_time:
            uptime = (datetime.utcnow() - self._start_time).total_seconds()
            logger.info(f"SystemMonitor stopped after {uptime:.1f}s")
            self.metrics["uptime_seconds"] = uptime

        # Reset state
        self._start_time = None
        logger.debug("SystemMonitor stopped")

    def record_metric(self, name: str, value: Any):
        """Record a custom metric."""
        self.metrics[name] = value
        logger.debug(f"Recorded metric: {name} = {value}")

    def get_metrics(self) -> Dict[str, Any]:
        """Get a copy of all recorded metrics."""
        return self.metrics.copy()

    def is_running(self) -> bool:
        """Check if the monitor is currently running."""
        return self._running