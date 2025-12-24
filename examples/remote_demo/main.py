import asyncio
import sys
from actor_system.api import create_system, spawn, tell, get_remote_ref, shutdown
from actor_system.core.actor import Actor


class Greeting:
    """Greeting message."""
    def __init__(self, name: str):
        self.name = name


class GreetingResponse:
    """Response to greeting."""
    def __init__(self, message: str):
        self.message = message


class GreeterActor(Actor):
    """Actor that responds to greetings."""
    
    def _reconstruct_message(self, msg):
        """Reconstruct Greeting object from dict if needed."""
        if isinstance(msg, dict):
            if "__class__" in msg and msg["__class__"] == "Greeting":
                return Greeting(msg.get("name", "Unknown"))
            elif "name" in msg:
                return Greeting(msg["name"])
        return msg
    
    def receive(self, message):
        """Handle messages."""
        from actor_system.core.system import AskMessage
        
        print(f"[DEBUG] GreeterActor received: {type(message).__name__}")
        if isinstance(message, AskMessage):
            original_msg = message.original_message
            print(f"[DEBUG] GreeterActor: It's an AskMessage, original: {type(original_msg).__name__}, value: {original_msg}")
            
            original_msg = self._reconstruct_message(original_msg)
            
            if isinstance(original_msg, Greeting):
                response = GreetingResponse(f"Hello, {original_msg.name}! Greetings from {self.self_ref.path.node_id}")
                print(f"[DEBUG] GreeterActor: Replying with: {response.message}")
                self.context.reply(message, response)
            else:
                print(f"[DEBUG] GreeterActor: Could not handle message type: {type(original_msg)}")
            return
        
        # Reconstruct message if it's a dict (for tell messages)
        message = self._reconstruct_message(message)
        
        if isinstance(message, Greeting):
            response = GreetingResponse(f"Hello, {message.name}! Greetings from {self.self_ref.path.node_id}")
            # Just print for tell
            print(f"Received greeting from {message.name}")
        
        elif isinstance(message, str):
            print(f"Received: {message}")


async def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("Server mode: python -m examples.remote_demo.main server [host] [port]")
        print("Client mode: python -m examples.remote_demo.main client <remote_host> <remote_port> [local_host] [local_port]")
        return
    
    mode = sys.argv[1]
    
    if mode == "server":
        host = sys.argv[2] if len(sys.argv) > 2 else "0.0.0.0"  # Listen on all interfaces
        port = int(sys.argv[3]) if len(sys.argv) > 3 else 8888
        
        print(f"Starting server on {host}:{port}")
        system = await create_system(node_id=f"{host}:{port}", host=host, port=port)
        
        try:
            greeter = await spawn(GreeterActor, actor_id="greeter")
            print(f"Greeter actor spawned at: {greeter.path}")
            print("Server running. Waiting for remote messages...")
            print("Press Ctrl+C to stop")
            try:
                await asyncio.sleep(3600)
            except KeyboardInterrupt:
                print("\nShutting down server...")
        
        finally:
            await shutdown()
    
    elif mode == "client":
        if len(sys.argv) < 4:
            print("Client mode requires: remote_host remote_port")
            return
        
        remote_host = sys.argv[2]
        remote_port = int(sys.argv[3])
        local_host = sys.argv[4] if len(sys.argv) > 4 else "localhost"
        local_port = int(sys.argv[5]) if len(sys.argv) > 5 else 8889
        
        print(f"Starting client on {local_host}:{local_port}")
        print(f"Connecting to remote server at {remote_host}:{remote_port}")
        
        system = await create_system(node_id=f"{local_host}:{local_port}", host=local_host, port=local_port)
        
        try:
            remote_address = f"{remote_host}:{remote_port}"
            remote_greeter = get_remote_ref(remote_address, "greeter")
            
            print(f"Connected to remote greeter: {remote_greeter.path}")
            print("\nSending messages to remote actor...")
            
            await tell(remote_greeter, Greeting("Alice"))
            await asyncio.sleep(1)
            
            await tell(remote_greeter, Greeting("Bob"))
            await asyncio.sleep(1)
            
            print("\nSending ask message...")
            try:
                response = await remote_greeter.ask(Greeting("Charlie"), timeout=5.0)
                if isinstance(response, dict):
                    response = GreetingResponse(response.get("message", str(response.get("value", response))))
                print(f"Response: {response.message}")
            except Exception as e:
                print(f"Error: {e}")
                import traceback
                traceback.print_exc()
            
            print("\nClient demo complete")
        
        finally:
            await shutdown()
    

if __name__ == "__main__":
    asyncio.run(main())

