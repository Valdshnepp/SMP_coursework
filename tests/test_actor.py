"""Tests for the Actor base class."""

import pytest
import asyncio
from actor_system.core.actor import Actor
from actor_system.core.system import ActorSystem


class SimpleActor(Actor):
    """Simple test actor."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.received = []
    
    def receive(self, message):
        """Store received messages."""
        self.received.append(message)


class BehaviorChangeActor(Actor):
    """Actor that changes behavior."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.received = []
    
    def receive(self, message):
        """Default behavior."""
        self.received.append(("default", message))
    
    def new_behavior(self, message):
        """New behavior."""
        self.received.append(("new", message))



@pytest.mark.asyncio
async def test_actor_receive_messages():
    """Test that actor receives and processes messages."""
    system = ActorSystem(node_id="test-node")
    await system.start()
    
    actor_ref = await system.spawn(SimpleActor, actor_id="test-actor")
    actor = system._actors[actor_ref.path]
    
    await system.send_message(actor_ref.path, "message1")
    await system.send_message(actor_ref.path, "message2")
    
    await asyncio.sleep(0.1)
    
    assert len(actor.received) == 2
    assert "message1" in actor.received
    assert "message2" in actor.received
    
    await system.shutdown()


@pytest.mark.asyncio
async def test_actor_behavior_change():
    """Test changing actor behavior."""
    system = ActorSystem(node_id="test-node")
    await system.start()
    
    actor_ref = await system.spawn(BehaviorChangeActor, actor_id="test-actor")
    actor = system._actors[actor_ref.path]
    
    await system.send_message(actor_ref.path, "msg1")
    await asyncio.sleep(0.1)
    
    actor.become(actor.new_behavior)
    
    await system.send_message(actor_ref.path, "msg2")
    await asyncio.sleep(0.1)
    
    assert len(actor.received) == 2
    assert ("default", "msg1") in actor.received
    assert ("new", "msg2") in actor.received
    
    await system.shutdown()


@pytest.mark.asyncio
async def test_actor_lifecycle():
    """Test actor lifecycle (pre_start, post_stop)."""
    class LifecycleActor(Actor):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.pre_start_called = False
            self.post_stop_called = False
        
        def pre_start(self):
            self.pre_start_called = True
        
        def post_stop(self):
            self.post_stop_called = True
        
        def receive(self, message):
            pass
    
    system = ActorSystem(node_id="test-node")
    await system.start()
    
    actor_ref = await system.spawn(LifecycleActor, actor_id="test-actor")
    actor = system._actors[actor_ref.path]
    
    assert actor.pre_start_called is True
    
    await system.stop(actor_ref)
    await asyncio.sleep(0.1)
    
    assert actor.post_stop_called is True
    
    await system.shutdown()

