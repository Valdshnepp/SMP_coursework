"""Tests for the public API."""

import pytest
import asyncio
from actor_system.api import (
    create_system, get_system, spawn, stop, tell, ask, shutdown, get_remote_ref
)
from actor_system.core.actor import Actor


class SimpleTestActor(Actor):
    """Test actor for API tests."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.received_messages = []
    
    def receive(self, message):
        """Store received messages."""
        from actor_system.core.system import AskMessage
        if isinstance(message, AskMessage):
            self.received_messages.append(message.original_message)
        else:
            self.received_messages.append(message)


class EchoActor(Actor):
    """Actor that echoes messages back."""
    
    def receive(self, message):
        """Echo the message back."""
        from actor_system.core.system import AskMessage
        if isinstance(message, AskMessage):
            original_msg = message.original_message
            if isinstance(original_msg, str):
                self.context.reply(message, f"Echo: {original_msg}")
        elif isinstance(message, str):
            pass


@pytest.mark.asyncio
async def test_create_system():
    """Test creating an actor system."""
    system = await create_system(node_id="test-node", host="localhost", port=8889)
    assert system is not None
    assert system.node_id == "test-node"
    assert system.address == "localhost:8889"
    await shutdown()


@pytest.mark.asyncio
async def test_get_system():
    """Test getting the current system."""
    system = await create_system(node_id="test-node")
    retrieved = get_system()
    assert retrieved is system
    await shutdown()


@pytest.mark.asyncio
async def test_get_system_without_creation():
    """Test that getting system without creation raises error."""
    # Clear any existing system
    from actor_system.api import set_system
    set_system(None)
    
    with pytest.raises(RuntimeError, match="No actor system created"):
        get_system()


@pytest.mark.asyncio
async def test_spawn_actor():
    """Test spawning an actor."""
    await create_system(node_id="test-node")
    
    actor_ref = await spawn(SimpleTestActor, actor_id="test-actor")
    assert actor_ref is not None
    assert actor_ref.path.actor_id == "test-actor"
    assert actor_ref.path.node_id == "test-node"
    
    await shutdown()


@pytest.mark.asyncio
async def test_spawn_actor_auto_id():
    """Test spawning an actor with auto-generated ID."""
    await create_system(node_id="test-node")
    
    actor_ref = await spawn(SimpleTestActor)
    assert actor_ref is not None
    assert actor_ref.path.actor_id.startswith("SimpleTestActor-")
    
    await shutdown()


@pytest.mark.asyncio
async def test_tell():
    """Test sending a message with tell."""
    await create_system(node_id="test-node")
    
    actor_ref = await spawn(SimpleTestActor, actor_id="test-actor")
    await tell(actor_ref, "Hello")
    
    # Give actor time to process
    await asyncio.sleep(0.1)
    
    actor = get_system()._actors[actor_ref.path]
    assert len(actor.received_messages) == 1
    assert actor.received_messages[0] == "Hello"
    
    await shutdown()


@pytest.mark.asyncio
async def test_ask():
    """Test sending a message with ask and getting response."""
    await create_system(node_id="test-node")
    
    actor_ref = await spawn(EchoActor, actor_id="echo-actor")
    response = await ask(actor_ref, "Hello", timeout=2.0)
    
    assert response == "Echo: Hello"
    
    await shutdown()


@pytest.mark.asyncio
async def test_ask_timeout():
    """Test that ask times out correctly."""
    await create_system(node_id="test-node")
    
    actor_ref = await spawn(SimpleTestActor, actor_id="test-actor")
    
    with pytest.raises(TimeoutError):
        await ask(actor_ref, "Hello", timeout=0.1)
    
    await shutdown()


@pytest.mark.asyncio
async def test_stop():
    """Test stopping an actor."""
    await create_system(node_id="test-node")
    
    actor_ref = await spawn(SimpleTestActor, actor_id="test-actor")
    await stop(actor_ref)
    
    # Actor should be removed from system
    system = get_system()
    assert actor_ref.path not in system._actors
    
    await shutdown()


@pytest.mark.asyncio
async def test_get_remote_ref():
    """Test getting a remote actor reference."""
    await create_system(node_id="test-node", host="localhost", port=8890)
    
    remote_ref = get_remote_ref("localhost:8888", "remote-actor")
    assert remote_ref is not None
    assert remote_ref.path.node_id == "localhost:8888"
    assert remote_ref.path.actor_id == "remote-actor"
    
    await shutdown()


@pytest.mark.asyncio
async def test_multiple_actors():
    """Test spawning and messaging multiple actors."""
    await create_system(node_id="test-node")
    
    actor1 = await spawn(SimpleTestActor, actor_id="actor1")
    actor2 = await spawn(SimpleTestActor, actor_id="actor2")
    
    await tell(actor1, "Message 1")
    await tell(actor2, "Message 2")
    
    await asyncio.sleep(0.1)
    
    system = get_system()
    assert len(system._actors[actor1.path].received_messages) == 1
    assert len(system._actors[actor2.path].received_messages) == 1
    
    await shutdown()

