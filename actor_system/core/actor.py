"""Base Actor class for the actor system."""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Callable, Optional, TYPE_CHECKING
from .mailbox import Mailbox
from .actor_ref import ActorRef

if TYPE_CHECKING:
    from .system import ActorSystem


class Actor(ABC):
    """Base class for all actors."""
    
    def __init__(self, mailbox_size: int = 1000):
        """
        Initialize actor.
        
        Args:
            mailbox_size: Maximum size of mailbox queue
        """
        self._mailbox = Mailbox(maxsize=mailbox_size)
        self._behavior: Callable[[Any], None] = self.receive
        self._context: Optional['ActorContext'] = None
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    @property
    def context(self) -> 'ActorContext':
        """Get actor context."""
        if self._context is None:
            raise RuntimeError("Actor context not set")
        return self._context
    
    @context.setter
    def context(self, value: 'ActorContext') -> None:
        """Set actor context."""
        self._context = value
    
    @property
    def mailbox(self) -> Mailbox:
        """Get actor mailbox."""
        return self._mailbox
    
    @property
    def self_ref(self) -> ActorRef:
        """Get reference to self."""
        return self.context.self_ref
    
    def become(self, behavior: Callable[[Any], None]) -> None:
        """
        Change actor behavior.
        
        Args:
            behavior: New behavior function
        """
        self._behavior = behavior
    
    def unbecome(self) -> None:
        """Revert to default behavior."""
        self._behavior = self.receive
    
    @abstractmethod
    def receive(self, message: Any) -> None:
        """
        Default message handler.
        
        Args:
            message: Received message
        """
        pass
    
    async def _process_message(self, message: Any) -> None:
        """
        Process a single message.
        
        Args:
            message: Message to process
        """
        # Handle AskMessage pattern
        from ..core.system import AskMessage, AskReply
        if isinstance(message, AskMessage):
            original_msg = message.original_message
            reply_to = message.reply_to
            
            self._behavior(message)
        else:
            self._behavior(message)
    
    async def _run(self) -> None:
        """Main actor loop."""
        self._running = True
        while self._running:
            try:
                message = await self._mailbox.get()
                await self._process_message(message)
            except asyncio.CancelledError:
                break
            except Exception as e:
                raise
    
    def start(self) -> None:
        """Start actor message processing."""
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run())
    
    async def stop(self) -> None:
        """Stop actor message processing."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
    
    def pre_start(self) -> None:
        """Called before actor starts processing messages."""
        pass
    
    def post_stop(self) -> None:
        """Called after actor stops processing messages."""
        pass


class ActorContext:
    """Context providing actor capabilities."""
    
    def __init__(self, actor: Actor, actor_ref: ActorRef, system: 'ActorSystem'):
        """
        Initialize actor context.
        
        Args:
            actor: The actor instance
            actor_ref: Reference to the actor
            system: Actor system
        """
        self._actor = actor
        self._self_ref = actor_ref
        self._system = system
    
    @property
    def self_ref(self) -> ActorRef:
        """Get reference to self."""
        return self._self_ref
    
    @property
    def system(self) -> 'ActorSystem':
        """Get actor system."""
        return self._system
    
    async def spawn(self, actor_class: type[Actor], actor_id: str, **kwargs) -> ActorRef:
        """
        Spawn a new actor.
        
        Args:
            actor_class: Actor class to spawn
            actor_id: Unique identifier for the actor
            **kwargs: Arguments to pass to actor constructor
            
        Returns:
            Reference to spawned actor
        """
        return await self._system.spawn(actor_class, actor_id, **kwargs)
    
    async def stop(self, actor_ref: ActorRef) -> None:
        """
        Stop an actor.
        
        Args:
            actor_ref: Reference to actor to stop
        """
        await self._system.stop(actor_ref)
    
    async def tell(self, target: ActorRef, message: Any) -> None:
        """
        Send a message asynchronously.
        
        Args:
            target: Target actor reference
            message: Message to send
        """
        await target.tell(message)
    
    async def ask(self, target: ActorRef, message: Any, timeout: float = 5.0) -> Any:
        """
        Send a message and wait for response.
        
        Args:
            target: Target actor reference
            message: Message to send
            timeout: Timeout in seconds
            
        Returns:
            Response message
        """
        return await target.ask(message, timeout)
    
    def reply(self, message: Any, response: Any) -> None:
        """
        Reply to an AskMessage.
        
        Args:
            message: The AskMessage received
            response: Response to send back
        """
        from ..core.system import AskMessage, AskReply
        from ..core.actor_ref import LocalActorRef
        
        if isinstance(message, AskMessage):
            reply_msg = AskReply(response)
            print(f"[DEBUG] ActorContext.reply: Sending AskReply to {message.reply_to.path}")
            
            if isinstance(message.reply_to, LocalActorRef):
                reply_actor = self._system._actors.get(message.reply_to.path)
                if reply_actor:
                    print(f"[DEBUG] ActorContext.reply: Putting message directly in reply actor mailbox")
                    asyncio.create_task(reply_actor.mailbox.put(reply_msg))
                else:
                    print(f"[DEBUG] ActorContext.reply: Reply actor not found!")
                    asyncio.create_task(message.reply_to.tell(reply_msg))
            else:
                asyncio.create_task(message.reply_to.tell(reply_msg))

