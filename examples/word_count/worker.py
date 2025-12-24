"""Worker actor for counting words in text chunks."""

import asyncio
from actor_system.core.actor import Actor
from typing import Dict


class CountWords:
    """Message to request word counting."""
    def __init__(self, chunk_id: str, text: str, reply_to):
        self.chunk_id = chunk_id
        self.text = text
        self.reply_to = reply_to


class WordCountResult:
    """Result of word counting."""
    def __init__(self, chunk_id: str, word_count: Dict[str, int]):
        self.chunk_id = chunk_id
        self.word_count = word_count


class WorkerActor(Actor):
    """Worker actor that counts words in text chunks."""
    
    def receive(self, message):
        """Handle messages."""
        if isinstance(message, CountWords):
            # Count words in the text chunk
            words = message.text.lower().split()
            word_count = {}
            for word in words:
                word = word.strip('.,!?;:"()[]{}')
                if word:
                    word_count[word] = word_count.get(word, 0) + 1
            
            # Send result back
            result = WordCountResult(message.chunk_id, word_count)
            asyncio.create_task(self.context.tell(message.reply_to, result))

