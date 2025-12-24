import asyncio
import sys
from actor_system.api import create_system, spawn, tell, shutdown
from .coordinator import CoordinatorActor, ProcessFile


async def main():
    """Main function."""
    system = await create_system(node_id="word-count-node")
    
    try:
        coordinator = await spawn(
            CoordinatorActor,
            actor_id="coordinator"
        )
        
        if len(sys.argv) > 1:
            file_path = sys.argv[1]
        else:
            return
        
        await tell(coordinator, ProcessFile(file_path, num_workers=4))
        
        await asyncio.sleep(5)
        
    finally:
        await shutdown()
        print("Actor system shut down")


if __name__ == "__main__":
    asyncio.run(main())

