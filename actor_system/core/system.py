"""ActorSystem - manages actor lifecycle and message routing."""

import asyncio
import uuid
import struct
from typing import Dict, Optional, Type, Any
from .actor import Actor, ActorContext
from .actor_ref import ActorRef, LocalActorRef, RemoteActorRef, ActorPath


class AskMessage:
    """Internal message for ask pattern."""
    def __init__(self, original_message: Any, reply_to: ActorRef):
        self.original_message = original_message
        self.reply_to = reply_to


class AskReply:
    """Internal message for ask pattern reply."""
    def __init__(self, response: Any):
        self.response = response


class ActorSystem:
    """Manages actor lifecycle and message routing."""
    
    def __init__(self, node_id: str = "default", host: str = "localhost", port: int = 8888):
        """
        Initialize actor system.
        
        Args:
            node_id: Unique identifier for this node
            host: Host to listen on for remote messages
            port: Port to listen on for remote messages
        """
        self._node_id = node_id
        self._host = host
        self._port = port
        self._actors: Dict[ActorPath, Actor] = {}
        self._actor_refs: Dict[ActorPath, ActorRef] = {}
        self._contexts: Dict[ActorPath, ActorContext] = {}
        self._pending_asks: Dict[str, asyncio.Future] = {}
        self._running = False
        self._server: Optional[asyncio.Server] = None
        self._transport = None
    
    @property
    def node_id(self) -> str:
        """Get node ID."""
        return self._node_id
    
    @property
    def address(self) -> str:
        """Get node address in format 'host:port'."""
        return f"{self._host}:{self._port}"
    
    async def spawn(
        self,
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
        if actor_id is None:
            actor_id = f"{actor_class.__name__}-{uuid.uuid4().hex[:8]}"
        
        path = ActorPath(node_id=self._node_id, actor_id=actor_id)
        
        if path in self._actors:
            raise ValueError(f"Actor with ID {actor_id} already exists")
        
        actor = actor_class(**kwargs)
        
        actor_ref = LocalActorRef(path, self)
        
        context = ActorContext(actor, actor_ref, self)
        actor.context = context
        
        self._actors[path] = actor
        self._actor_refs[path] = actor_ref
        self._contexts[path] = context
        
        actor.pre_start()
        actor.start()
        
        return actor_ref
    
    async def stop(self, actor_ref: ActorRef) -> None:
        """
        Stop an actor.
        
        Args:
            actor_ref: Reference to actor to stop
        """
        path = actor_ref.path
        
        if path not in self._actors:
            return
        
        actor = self._actors[path]
        
        await actor.stop()
        actor.post_stop()
        
        del self._actors[path]
        del self._actor_refs[path]
        del self._contexts[path]
    
    async def send_message(self, path: ActorPath, message: Any) -> None:
        """
        Send a message to an actor.
        
        Args:
            path: Path to actor
            message: Message to send
        """
        if path.node_id != self._node_id:
            from ..messaging.transport import Transport
            from ..messaging.serializer import JSONSerializer
            
            if self._transport is None:
                self._transport = Transport(serializer=JSONSerializer())
            
            await self._transport.send(path, message)
            return
        
        if path not in self._actors:
            raise ValueError(f"Actor {path} not found")
        
        actor = self._actors[path]
        await actor.mailbox.put(message)
    
    async def ask_message(self, path: ActorPath, message: Any, timeout: float = 5.0) -> Any:
        """
        Send a message and wait for response.
        
        Args:
            path: Path to actor
            message: Message to send
            timeout: Timeout in seconds
            
        Returns:
            Response message
            
        Raises:
            TimeoutError: If timeout is exceeded
        """
        if path.node_id != self._node_id:
            from ..messaging.transport import Transport
            from ..messaging.serializer import JSONSerializer
            
            if self._transport is None:
                self._transport = Transport(serializer=JSONSerializer())
            
            return await self._transport.send_and_receive(path, message, timeout)
        
        if path not in self._actors:
            raise ValueError(f"Actor {path} not found")
        
        ask_id = str(uuid.uuid4())
        future = asyncio.Future()
        self._pending_asks[ask_id] = future
        
        reply_path = ActorPath(node_id=self._node_id, actor_id=f"reply-{ask_id}")
        
        class ReplyActor(Actor):
            def receive(self, msg):
                if isinstance(msg, AskReply):
                    if ask_id in self._system._pending_asks:
                        self._system._pending_asks[ask_id].set_result(msg.response)
                        del self._system._pending_asks[ask_id]
        
        reply_actor = ReplyActor()
        reply_actor._system = self
        reply_context = ActorContext(reply_actor, LocalActorRef(reply_path, self), self)
        reply_actor.context = reply_context
        self._actors[reply_path] = reply_actor
        self._actor_refs[reply_path] = LocalActorRef(reply_path, self)
        self._contexts[reply_path] = reply_context
        reply_actor.start()
        
        ask_msg = AskMessage(original_message=message, reply_to=LocalActorRef(reply_path, self))
        
        await self.send_message(path, ask_msg)
        
        try:
            response = await asyncio.wait_for(future, timeout=timeout)
            return response
        except asyncio.TimeoutError:
            if ask_id in self._pending_asks:
                del self._pending_asks[ask_id]
            await self.stop(LocalActorRef(reply_path, self))
            raise TimeoutError(f"Ask timeout after {timeout}s")
        finally:
            if reply_path in self._actors:
                await self.stop(LocalActorRef(reply_path, self))
    
    def get_actor_ref(self, path: ActorPath) -> Optional[ActorRef]:
        """Get actor reference by path."""
        return self._actor_refs.get(path)
    
    def get_remote_ref(self, node_address: str, actor_id: str) -> RemoteActorRef:
        """
        Get a reference to a remote actor.
        
        Args:
            node_address: Remote node address in format 'host:port'
            actor_id: ID of the remote actor
            
        Returns:
            Remote actor reference
        """
        from ..messaging.transport import Transport
        from ..messaging.serializer import JSONSerializer
        
        if self._transport is None:
            self._transport = Transport(serializer=JSONSerializer())
        
        path = ActorPath(node_id=node_address, actor_id=actor_id)
        return RemoteActorRef(path, self._transport)
    
    async def shutdown(self) -> None:
        """Shutdown the actor system."""
        self._running = False
        
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        
        for path in list(self._actors.keys()):
            await self.stop(LocalActorRef(path, self))
    
    async def start(self) -> None:
        """Start the actor system and remote message server."""
        self._running = True
        self._server = await asyncio.start_server(
            self._handle_remote_connection,
            self._host,
            self._port
        )
        print(f"Actor system started on {self._host}:{self._port}")
    
    async def _handle_remote_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """Handle incoming remote connection."""
        try:
            while True:
                length_data = await reader.readexactly(4)
                length = struct.unpack("!I", length_data)[0]
                
                data = await reader.readexactly(length)
                
                from ..messaging.serializer import JSONSerializer
                serializer = JSONSerializer()
                msg = serializer.deserialize(data)
                
                path_data = msg.get("path", {})
                actor_path = ActorPath(
                    node_id=self._node_id, 
                    actor_id=path_data.get("actor_id", "")
                )
                
                message = msg.get("message")
                request_id = msg.get("request_id")
                if actor_path in self._actors:
                    if request_id:
                        # Create a future to wait for response
                        response_future = asyncio.Future()
                        
                        # Create a temporary reply actor to capture response
                        reply_ask_id = f"remote-{request_id}"
                        reply_path = ActorPath(node_id=self._node_id, actor_id=f"reply-{reply_ask_id}")
                        
                        class RemoteReplyActor(Actor):
                            def receive(self, msg):
                                from ..core.system import AskReply
                                print(f"[DEBUG] RemoteReplyActor received: {type(msg).__name__}")
                                if isinstance(msg, AskReply):
                                    print(f"[DEBUG] RemoteReplyActor got AskReply with response: {msg.response}")
                                    if not response_future.done():
                                        response_future.set_result(msg.response)
                                    else:
                                        print(f"[DEBUG] Future already done!")
                                else:
                                    print(f"[DEBUG] RemoteReplyActor got unexpected message type: {type(msg)}")
                        
                        reply_actor = RemoteReplyActor()
                        reply_context = ActorContext(reply_actor, LocalActorRef(reply_path, self), self)
                        reply_actor.context = reply_context
                        self._actors[reply_path] = reply_actor
                        self._actor_refs[reply_path] = LocalActorRef(reply_path, self)
                        self._contexts[reply_path] = reply_context
                        reply_actor.start()
                        
                        await asyncio.sleep(0.01)
                        
                        ask_msg = AskMessage(original_message=message, reply_to=LocalActorRef(reply_path, self))
                        
                        print(f"[DEBUG] Sending AskMessage to {actor_path}, reply_to: {reply_path}")
                        await self.send_message(actor_path, ask_msg)
                        
                        await asyncio.sleep(0.1)
                        
                        print(f"[DEBUG] Waiting for response from reply actor...")
                        try:
                            response = await asyncio.wait_for(response_future, timeout=5.0)
                            print(f"[DEBUG] Got response: {response}")
                            if hasattr(response, '__dict__'):
                                response_dict = {k: v for k, v in response.__dict__.items()}
                            else:
                                response_dict = {"value": str(response)}
                            
                            response_data = serializer.serialize({
                                "request_id": request_id,
                                "response": response_dict
                            })
                            writer.write(struct.pack("!I", len(response_data)))
                            writer.write(response_data)
                            await writer.drain()
                        except asyncio.TimeoutError:
                            error_data = serializer.serialize({
                                "request_id": request_id,
                                "error": "Timeout waiting for response"
                            })
                            writer.write(struct.pack("!I", len(error_data)))
                            writer.write(error_data)
                            await writer.drain()
                        except Exception as e:
                            import traceback
                            traceback.print_exc()
                            error_data = serializer.serialize({
                                "request_id": request_id,
                                "error": str(e)
                            })
                            writer.write(struct.pack("!I", len(error_data)))
                            writer.write(error_data)
                            await writer.drain()
                        finally:
                            if reply_path in self._actors:
                                await self.stop(LocalActorRef(reply_path, self))
                    else:
                        await self.send_message(actor_path, message)
                else:
                    print(f"Warning: Actor {actor_path} not found on this node")
        except asyncio.IncompleteReadError:
            pass
        except Exception as e:
            print(f"Error handling remote connection: {e}")
        finally:
            writer.close()
            await writer.wait_closed()

