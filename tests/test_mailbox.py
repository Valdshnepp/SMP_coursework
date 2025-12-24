"""Tests for the Mailbox component."""

import pytest
import asyncio
from actor_system.core.mailbox import Mailbox


@pytest.mark.asyncio
async def test_mailbox_put_get():
    """Test basic put and get operations."""
    mailbox = Mailbox(maxsize=10)
    
    await mailbox.put("message1")
    await mailbox.put("message2")
    
    msg1 = await mailbox.get()
    msg2 = await mailbox.get()
    
    assert msg1 == "message1"
    assert msg2 == "message2"


@pytest.mark.asyncio
async def test_mailbox_empty():
    """Test empty check."""
    mailbox = Mailbox(maxsize=10)
    
    assert mailbox.empty() is True
    
    await mailbox.put("message")
    assert mailbox.empty() is False
    
    await mailbox.get()
    assert mailbox.empty() is True


@pytest.mark.asyncio
async def test_mailbox_full():
    """Test full check with bounded queue."""
    mailbox = Mailbox(maxsize=2)
    
    assert mailbox.full() is False
    
    await mailbox.put("msg1")
    assert mailbox.full() is False
    
    await mailbox.put("msg2")
    assert mailbox.full() is True


@pytest.mark.asyncio
async def test_mailbox_backpressure():
    """Test that full mailbox blocks on put."""
    mailbox = Mailbox(maxsize=1)
    
    await mailbox.put("msg1")
    assert mailbox.full() is True
    
    # This should block until space is available
    put_task = asyncio.create_task(mailbox.put("msg2"))
    
    # Give it a moment to start
    await asyncio.sleep(0.01)
    
    # Should still be waiting
    assert not put_task.done()
    
    # Remove message to make space
    await mailbox.get()
    
    # Now put should complete
    await asyncio.sleep(0.01)
    assert put_task.done()


@pytest.mark.asyncio
async def test_mailbox_get_nowait():
    """Test non-blocking get."""
    mailbox = Mailbox(maxsize=10)
    
    # Should raise QueueEmpty
    with pytest.raises(asyncio.QueueEmpty):
        mailbox.get_nowait()
    
    await mailbox.put("message")
    msg = mailbox.get_nowait()
    assert msg == "message"


@pytest.mark.asyncio
async def test_mailbox_qsize():
    """Test queue size tracking."""
    mailbox = Mailbox(maxsize=10)
    
    assert mailbox.qsize() == 0
    
    await mailbox.put("msg1")
    assert mailbox.qsize() == 1
    
    await mailbox.put("msg2")
    assert mailbox.qsize() == 2
    
    await mailbox.get()
    assert mailbox.qsize() == 1


@pytest.mark.asyncio
async def test_mailbox_metrics():
    """Test mailbox metrics."""
    mailbox = Mailbox(maxsize=10)
    
    metrics = mailbox.metrics
    assert metrics.queue_depth == 0
    assert metrics.total_messages == 0
    
    await mailbox.put("msg1")
    await mailbox.put("msg2")
    
    metrics = mailbox.metrics
    assert metrics.total_messages == 2
    assert metrics.queue_depth == 2
    assert metrics.last_message_time is not None


@pytest.mark.asyncio
async def test_mailbox_unbounded():
    """Test unbounded mailbox."""
    mailbox = Mailbox(maxsize=0)  # 0 means unbounded
    
    # Should never be full
    for i in range(100):
        await mailbox.put(f"msg{i}")
    
    assert mailbox.qsize() == 100
    assert mailbox.full() is False

