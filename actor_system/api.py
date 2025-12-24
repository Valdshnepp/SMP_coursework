"""Public API for the actor system."""

from typing import Type, Optional, Any
from .core.actor import Actor
from .core.actor_ref import ActorRef
from .core.system import ActorSystem


# Global system instance (can be overridden)
_system: Optional[ActorSystem] = None


async def create_system(node_id: str = "default", host: str = "localhost", port: int = 8888) -> ActorSystem:
    """
    Create a new actor system.
    
    Args:
        node_id: Unique identifier for this node
        host: Host to listen on for remote messages
        port: Port to listen on for remote messages
        
    Returns:
        Actor system instance
    """
    global _system
    _system = ActorSystem(node_id=node_id, host=host, port=port)
    await _system.start()
    return _system


def get_system() -> ActorSystem:
    """
    Get the current actor system.
    
    Returns:
        Current actor system
        
    Raises:
        RuntimeError: If no system has been created
    """
    if _system is None:
        raise RuntimeError("No actor system created. Call create_system() first.")
    return _system


def set_system(system: ActorSystem) -> None:
    """
    Set the global actor system.
    
    Args:
        system: Actor system to use
    """
    global _system
    _system = system


async def spawn(
    actor_class: Type[Actor],
    actor_id: Optional[str] = None,
    **kwargs
) -> ActorRef:
    """
    Spawn a new actor.
    
    Args:
        actor_class: Actor class to spawn
        actor_id: Unique identifier (auto-generated if None)
        **kwargs: Arguments to pass to actor constructor
        
    Returns:
        Reference to spawned actor
    """
    system = get_system()
    return await system.spawn(actor_class, actor_id, **kwargs)


async def stop(actor_ref: ActorRef) -> None:
    """
    Stop an actor.
    
    Args:
        actor_ref: Reference to actor to stop
    """
    system = get_system()
    await system.stop(actor_ref)


async def tell(target: ActorRef, message: Any) -> None:
    """
    Send a message asynchronously (fire-and-forget).
    
    Args:
        target: Target actor reference
        message: Message to send
    """
    await target.tell(message)


async def ask(target: ActorRef, message: Any, timeout: float = 5.0) -> Any:
    """
    Send a message and wait for response.
    
    Args:
        target: Target actor reference
        message: Message to send
        timeout: Timeout in seconds
        
    Returns:
        Response message
        
    Raises:
        TimeoutError: If timeout is exceeded
    """
    return await target.ask(message, timeout)


async def shutdown() -> None:
    """Shutdown the actor system."""
    system = get_system()
    await system.shutdown()


def get_remote_ref(node_address: str, actor_id: str) -> ActorRef:
    """
    Get a reference to a remote actor.
    
    Args:
        node_address: Remote node address in format 'host:port'
        actor_id: ID of the remote actor
        
    Returns:
        Remote actor reference
    """
    system = get_system()
    return system.get_remote_ref(node_address, actor_id)

