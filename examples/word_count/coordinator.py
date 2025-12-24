"""Coordinator actor for word count task."""

import asyncio
from actor_system.core.actor import Actor
from actor_system.core.actor_ref import ActorRef
from typing import List
from .worker import CountWords, WorkerActor
from .aggregator import StartAggregation, AggregatorActor


class ProcessFile:
    """Message to process a file."""
    def __init__(self, file_path: str, num_workers: int = 4):
        self.file_path = file_path
        self.num_workers = num_workers


class CoordinatorActor(Actor):
    """Coordinator actor that manages the word count task."""
    
    def __init__(self, mailbox_size: int = 1000):
        super().__init__(mailbox_size)
        self._workers: List[ActorRef] = []
        self._aggregator: ActorRef = None
        self._chunk_size = 1000 
    
    def receive(self, message):
        """Handle messages."""
        if isinstance(message, ProcessFile):
            asyncio.create_task(self._process_file(message))
    
    async def _process_file(self, message: ProcessFile):
        """Process a file by splitting it and distributing to workers."""
        try:
            with open(message.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            print(f"Processing file: {message.file_path}")
            print(f"File size: {len(content)} characters")
            
            self._workers = []
            for i in range(message.num_workers):
                worker_ref = await self.context.spawn(
                    WorkerActor,
                    actor_id=f"worker-{i}",
                    mailbox_size=100
                )
                self._workers.append(worker_ref)
            
            print(f"Spawned {len(self._workers)} workers")
            
            self._aggregator = await self.context.spawn(
                AggregatorActor,
                actor_id="aggregator",
                mailbox_size=1000
            )
            
            chunks = []
            for i in range(0, len(content), self._chunk_size):
                chunk = content[i:i + self._chunk_size]
                chunks.append((f"chunk-{i // self._chunk_size}", chunk))
            
            print(f"Split file into {len(chunks)} chunks")
            
            await self.context.tell(self._aggregator, StartAggregation(len(chunks)))
            
            worker_index = 0
            for chunk_id, chunk_text in chunks:
                worker = self._workers[worker_index]
                count_msg = CountWords(chunk_id, chunk_text, self._aggregator)
                await self.context.tell(worker, count_msg)
                worker_index = (worker_index + 1) % len(self._workers)
            
            print(f"Distributed {len(chunks)} chunks to workers")
            
        except FileNotFoundError:
            print(f"Error: File {message.file_path} not found")
        except Exception as e:
            print(f"Error processing file: {e}")


