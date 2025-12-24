"""Message base classes."""

from abc import ABC
from typing import Any, Optional
from dataclasses import dataclass


class Message(ABC):
    """Base class for all messages."""
    pass


@dataclass
class Envelope:
    """Message envelope with metadata."""
    message: Any
    sender: Optional[Any] = None
    reply_to: Optional[Any] = None

