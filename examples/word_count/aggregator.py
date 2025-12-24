"""Aggregator actor for combining word count results."""

from actor_system.core.actor import Actor
from typing import Dict, Set
from .worker import WordCountResult


class StartAggregation:
    """Message to start aggregation."""
    def __init__(self, total_chunks: int):
        self.total_chunks = total_chunks


class AggregatorActor(Actor):
    """Aggregator actor that combines word count results."""
    
    def __init__(self, mailbox_size: int = 1000):
        super().__init__(mailbox_size)
        self._results: Dict[str, Dict[str, int]] = {}
        self._expected_chunks: int = 0
        self._received_chunks: int = 0
        self._final_result: Dict[str, int] = {}
    
    def receive(self, message):
        """Handle messages."""
        if isinstance(message, StartAggregation):
            self._expected_chunks = message.total_chunks
            self._received_chunks = 0
            self._results = {}
            self._final_result = {}
        
        elif isinstance(message, WordCountResult):
            self._results[message.chunk_id] = message.word_count
            self._received_chunks += 1
            
            if self._received_chunks >= self._expected_chunks:
                self._final_result = {}
                total_words = 0
                for chunk_result in self._results.values():
                    for word, count in chunk_result.items():
                        self._final_result[word] = self._final_result.get(word, 0) + count
                        total_words += count
                
                print(f"\n=== Word Count Complete ===")
                print(f"Total words: {total_words}")
                print(f"Total unique words: {len(self._final_result)}")
                print(f"Top 10 words:")
                sorted_words = sorted(self._final_result.items(), key=lambda x: x[1], reverse=True)
                for word, count in sorted_words[:10]:
                    print(f"  {word}: {count}")
                print("==========================\n")
        

