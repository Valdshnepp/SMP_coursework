"""Actor references for transparent local and remote addressing."""

from abc import ABC, abstractmethod
from typing import Any, Optional, TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    from .system import ActorSystem
    from ..messaging.transport import Transport


@dataclass
class ActorPath:
    """Represents the path to an actor."""
    node_id: str
    actor_id: str
    
    def __str__(self) -> str:
        return f"akka://{self.node_id}/{self.actor_id}"
    
    def __hash__(self) -> int:
        return hash((self.node_id, self.actor_id))
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, ActorPath):
            return False
        return self.node_id == other.node_id and self.actor_id == other.actor_id


class ActorRef(ABC):
    """Abstract base class for actor references."""
    
    def __init__(self, path: ActorPath):
        """
        Initialize actor reference.
        
        Args:
            path: Path to the actor
        """
        self.path = path
    
    @abstractmethod
    async def tell(self, message: Any) -> None:
        """
        Send a message asynchronously.
        
        Args:
            message: Message to send
        """
        pass
    
    @abstractmethod
    async def ask(self, message: Any, timeout: float = 5.0) -> Any:
        """
        Send a message and wait for response.
        
        Args:
            message: Message to send
            timeout: Timeout in seconds
            
        Returns:
            Response message
            
        Raises:
            TimeoutError: If timeout is exceeded
        """
        pass
    
    def __str__(self) -> str:
        return str(self.path)
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.path})"
    
    def __hash__(self) -> int:
        return hash(self.path)
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, ActorRef):
            return False
        return self.path == other.path


class LocalActorRef(ActorRef):
    """Reference to a local actor."""
    
    def __init__(self, path: ActorPath, system: 'ActorSystem'):
        """
        Initialize local actor reference.
        
        Args:
            path: Path to the actor
            system: Actor system managing the actor
        """
        super().__init__(path)
        self._system = system
    
    async def tell(self, message: Any) -> None:
        """Send message to local actor."""
        await self._system.send_message(self.path, message)
    
    async def ask(self, message: Any, timeout: float = 5.0) -> Any:
        """Send message and wait for response."""
        return await self._system.ask_message(self.path, message, timeout)


class RemoteActorRef(ActorRef):
    """Reference to a remote actor."""
    
    def __init__(self, path: ActorPath, transport: 'Transport'):
        """
        Initialize remote actor reference.
        
        Args:
            path: Path to the actor
            transport: Transport for sending messages
        """
        super().__init__(path)
        self._transport = transport
    
    async def tell(self, message: Any) -> None:
        """Send message to remote actor."""
        await self._transport.send(self.path, message)
    
    async def ask(self, message: Any, timeout: float = 5.0) -> Any:
        """Send message and wait for response."""
        return await self._transport.send_and_receive(self.path, message, timeout)
