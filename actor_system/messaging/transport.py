"""Network transport for remote messaging."""

import asyncio
import struct
import uuid
from typing import Dict, Optional, Any
from ..core.actor_ref import ActorPath
from .serializer import Serializer, JSONSerializer


class Transport:
    """TCP-based transport for remote messaging."""
    
    def __init__(self, serializer: Optional[Serializer] = None):
        """
        Initialize transport.
        
        Args:
            serializer: Serializer to use (default: JSONSerializer)
        """
        self._serializer = serializer or JSONSerializer()
        self._connections: Dict[str, asyncio.StreamWriter] = {}
        self._readers: Dict[str, asyncio.StreamReader] = {}
        self._pending_responses: Dict[str, asyncio.Future] = {}
        self._response_handlers: Dict[str, asyncio.Task] = {}
    
    async def connect(self, host: str, port: int) -> None:
        """
        Connect to a remote node.
        
        Args:
            host: Remote host
            port: Remote port
        """
        key = f"{host}:{port}"
        if key in self._connections:
            return
        
        try:
            reader, writer = await asyncio.open_connection(host, port)
            self._connections[key] = writer
            self._readers[key] = reader
            
            task = asyncio.create_task(self._handle_responses(reader, key))
            self._response_handlers[key] = task
        except Exception as e:
            print(f"Failed to connect to {host}:{port}: {e}")
            raise
    
    async def disconnect(self, host: str, port: int) -> None:
        """
        Disconnect from a remote node.
        
        Args:
            host: Remote host
            port: Remote port
        """
        key = f"{host}:{port}"
        if key in self._connections:
            writer = self._connections[key]
            writer.close()
            await writer.wait_closed()
            del self._connections[key]
        
        if key in self._readers:
            del self._readers[key]
        
        if key in self._response_handlers:
            task = self._response_handlers[key]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            del self._response_handlers[key]
    
    async def send(self, path: ActorPath, message: Any) -> None:
        """
        Send a message to a remote actor.
        
        Args:
            path: Path to remote actor
            message: Message to send
        """
        # Extract host and port from node_id (format: "host:port")
        try:
            host, port_str = path.node_id.split(":")
            port = int(port_str)
        except ValueError:
            raise ValueError(f"Invalid node_id format: {path.node_id}. Expected 'host:port'")
        
        await self.connect(host, port)
        
        key = f"{host}:{port}"
        writer = self._connections[key]
        
        data = self._serializer.serialize({
            "path": {"node_id": path.node_id, "actor_id": path.actor_id},
            "message": message
        })
        
        # Send length prefix
        length = len(data)
        writer.write(struct.pack("!I", length))
        writer.write(data)
        await writer.drain()
    
    async def send_and_receive(self, path: ActorPath, message: Any, timeout: float = 5.0) -> Any:
        """
        Send a message and wait for response.
        
        Args:
            path: Path to remote actor
            message: Message to send
            timeout: Timeout in seconds
            
        Returns:
            Response message
        """
        request_id = str(uuid.uuid4())  # Generate unique request ID
        future = asyncio.Future()
        self._pending_responses[request_id] = future
        
        # Send message with request ID
        try:
            host, port_str = path.node_id.split(":")
            port = int(port_str)
        except ValueError:
            raise ValueError(f"Invalid node_id format: {path.node_id}. Expected 'host:port'")
        
        await self.connect(host, port)
        
        key = f"{host}:{port}"
        writer = self._connections[key]
        
        data = self._serializer.serialize({
            "request_id": request_id,
            "path": {"node_id": path.node_id, "actor_id": path.actor_id},
            "message": message
        })
        
        length = len(data)
        writer.write(struct.pack("!I", length))
        writer.write(data)
        await writer.drain()
        
        # Wait for response
        try:
            response = await asyncio.wait_for(future, timeout=timeout)
            return response
        except asyncio.TimeoutError:
            if request_id in self._pending_responses:
                del self._pending_responses[request_id]
            raise TimeoutError(f"Remote ask timeout after {timeout}s")
    
    async def _handle_responses(self, reader: asyncio.StreamReader, key: str) -> None:
        """Handle incoming responses."""
        try:
            while True:
                # Read length
                length_data = await reader.readexactly(4)
                length = struct.unpack("!I", length_data)[0]
                
                # Read data
                data = await reader.readexactly(length)
                
                # Deserialize
                msg = self._serializer.deserialize(data)
                
                if "request_id" in msg:
                    request_id = msg["request_id"]
                    if request_id in self._pending_responses:
                        if "response" in msg:
                            # Response is already a dict from JSON deserialization
                            response = msg["response"]
                            self._pending_responses[request_id].set_result(response)
                            del self._pending_responses[request_id]
                        elif "error" in msg:
                            # Error response
                            error_msg = msg["error"]
                            self._pending_responses[request_id].set_exception(Exception(error_msg))
                            del self._pending_responses[request_id]
        except asyncio.IncompleteReadError:
            pass
        except Exception as e:
            print(f"Error handling responses from {key}: {e}")





