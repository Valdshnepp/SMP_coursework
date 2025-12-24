"""Mailbox implementation for actors with backpressure support."""

import asyncio
from typing import Any, Optional
from collections import deque
from dataclasses import dataclass
from datetime import datetime


@dataclass
class MailboxMetrics:
    """Metrics for mailbox monitoring."""
    queue_depth: int = 0
    total_messages: int = 0
    messages_per_second: float = 0.0
    last_message_time: Optional[datetime] = None


class Mailbox:
    """Bounded mailbox queue for actors with backpressure support."""
    
    def __init__(self, maxsize: int = 1000):
        """
        Initialize mailbox.
        
        Args:
            maxsize: Maximum number of messages in queue (0 = unbounded)
        """
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=maxsize if maxsize > 0 else 0)
        self._maxsize = maxsize
        self._metrics = MailboxMetrics()
        self._message_times: deque = deque(maxlen=100)
        
    async def put(self, message: Any) -> None:
        """
        Put a message into the mailbox.
        
        Args:
            message: Message to enqueue
            
        Raises:
            asyncio.QueueFull: If queue is full and backpressure is enabled
        """
        await self._queue.put(message)
        self._metrics.total_messages += 1
        self._metrics.queue_depth = self._queue.qsize()
        now = datetime.now()
        self._metrics.last_message_time = now
        self._message_times.append(now)
        self._update_throughput()
    
    async def get(self) -> Any:
        """
        Get a message from the mailbox.
        
        Returns:
            Next message from queue
        """
        message = await self._queue.get()
        self._metrics.queue_depth = self._queue.qsize()
        return message
    
    def get_nowait(self) -> Any:
        """
        Get a message without waiting (non-blocking).
        
        Returns:
            Next message from queue
            
        Raises:
            asyncio.QueueEmpty: If queue is empty
        """
        message = self._queue.get_nowait()
        self._metrics.queue_depth = self._queue.qsize()
        return message
    
    def empty(self) -> bool:
        """Check if mailbox is empty."""
        return self._queue.empty()
    
    def full(self) -> bool:
        """Check if mailbox is full (backpressure indicator)."""
        return self._queue.full()
    
    def qsize(self) -> int:
        """Get current queue size."""
        return self._queue.qsize()
    
    @property
    def metrics(self) -> MailboxMetrics:
        """Get mailbox metrics."""
        self._metrics.queue_depth = self._queue.qsize()
        return self._metrics
    
    def _update_throughput(self) -> None:
        """Update messages per second metric."""
        if len(self._message_times) < 2:
            self._metrics.messages_per_second = 0.0
            return
        
        time_span = (self._message_times[-1] - self._message_times[0]).total_seconds()
        if time_span > 0:
            self._metrics.messages_per_second = len(self._message_times) / time_span
        else:
            self._metrics.messages_per_second = 0.0

