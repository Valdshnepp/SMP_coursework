"""Tests for the ActorSystem."""

import pytest
import asyncio
from actor_system.core.system import ActorSystem, AskMessage
from actor_system.core.actor import Actor


class EchoActor(Actor):
    """Actor that echoes messages."""
    
    def receive(self, message):
        """Echo message back."""
        if isinstance(message, str):
            self.context.reply(message, f"Echo: {message}")


class CounterActor(Actor):
    """Actor that maintains a counter."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.count = 0
    
    def receive(self, message):
        """Handle counter messages."""
        if isinstance(message, AskMessage):
            original_msg = message.original_message
            if original_msg == "get":
                self.context.reply(message, self.count)
        elif message == "increment":
            self.count += 1



@pytest.mark.asyncio
async def test_system_spawn():
    """Test spawning actors."""
    system = ActorSystem(node_id="test-node")
    await system.start()
    
    actor_ref = await system.spawn(EchoActor, actor_id="echo")
    
    assert actor_ref.path.actor_id == "echo"
    assert actor_ref.path.node_id == "test-node"
    assert actor_ref.path in system._actors
    
    await system.shutdown()


@pytest.mark.asyncio
async def test_system_spawn_duplicate_id():
    """Test that spawning with duplicate ID raises error."""
    system = ActorSystem(node_id="test-node")
    await system.start()
    
    await system.spawn(EchoActor, actor_id="echo")
    
    with pytest.raises(ValueError, match="already exists"):
        await system.spawn(EchoActor, actor_id="echo")
    
    await system.shutdown()


@pytest.mark.asyncio
async def test_system_send_message():
    """Test sending messages between actors."""
    system = ActorSystem(node_id="test-node")
    await system.start()
    
    actor_ref = await system.spawn(CounterActor, actor_id="counter")
    
    await system.send_message(actor_ref.path, "increment")
    await system.send_message(actor_ref.path, "increment")
    
    await asyncio.sleep(0.1)
    
    actor = system._actors[actor_ref.path]
    assert actor.count == 2
    
    await system.shutdown()


@pytest.mark.asyncio
async def test_system_ask_message():
    """Test ask pattern."""
    system = ActorSystem(node_id="test-node")
    await system.start()
    
    actor_ref = await system.spawn(CounterActor, actor_id="counter")
    
    await system.send_message(actor_ref.path, "increment")
    await system.send_message(actor_ref.path, "increment")
    await asyncio.sleep(0.1)
    
    response = await system.ask_message(actor_ref.path, "get", timeout=2.0)
    assert response == 2
    
    await system.shutdown()


@pytest.mark.asyncio
async def test_system_multiple_actors():
    """Test multiple actors in system."""
    system = ActorSystem(node_id="test-node")
    await system.start()
    
    actor1 = await system.spawn(CounterActor, actor_id="counter1")
    actor2 = await system.spawn(CounterActor, actor_id="counter2")
    
    await system.send_message(actor1.path, "increment")
    await system.send_message(actor2.path, "increment")
    await system.send_message(actor2.path, "increment")
    
    await asyncio.sleep(0.1)
    
    assert system._actors[actor1.path].count == 1
    assert system._actors[actor2.path].count == 2
    
    await system.shutdown()



@pytest.mark.asyncio
async def test_system_address():
    """Test address property."""
    system = ActorSystem(node_id="test-node", host="127.0.0.1", port=9999)
    await system.start()
    
    assert system.address == "127.0.0.1:9999"
    
    await system.shutdown()

