"""Message serialization for network transport."""

import json
import pickle
from abc import ABC, abstractmethod
from typing import Any


class Serializer(ABC):
    """Base class for message serializers."""
    
    @abstractmethod
    def serialize(self, obj: Any) -> bytes:
        """Serialize object to bytes."""
        pass
    
    @abstractmethod
    def deserialize(self, data: bytes) -> Any:
        """Deserialize bytes to object."""
        pass


class JSONSerializer(Serializer):
    """JSON-based serializer."""
    
    def _serialize_value(self, obj: Any) -> Any:
        """Recursively serialize a value, converting objects to dicts."""
        if hasattr(obj, '__dict__') and not isinstance(obj, (str, int, float, bool, type(None))):
            # Create a dict with class info and attributes
            result = {
                '__class__': obj.__class__.__name__,
                '__module__': obj.__class__.__module__,
            }
            # Serialize each attribute value
            for k, v in obj.__dict__.items():
                if not k.startswith('_'):
                    result[k] = self._serialize_value(v)
            return result
        elif isinstance(obj, dict):
            # Recursively serialize dict values
            return {k: self._serialize_value(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            # Recursively serialize list/tuple items
            return [self._serialize_value(item) for item in obj]
        else:
            # Primitive type or already serializable
            return obj
    
    def serialize(self, obj: Any) -> bytes:
        """Serialize to JSON bytes."""
        serialized = self._serialize_value(obj)
        return json.dumps(serialized, default=str).encode('utf-8')
    
    def deserialize(self, data: bytes) -> Any:
        """Deserialize from JSON bytes."""
        obj = json.loads(data.decode('utf-8'))
        # If it's a dict with class info, try to reconstruct
        if isinstance(obj, dict) and '__class__' in obj:
            return obj
        return obj


class PickleSerializer(Serializer):
    """Pickle-based serializer."""
    
    def serialize(self, obj: Any) -> bytes:
        """Serialize using pickle."""
        return pickle.dumps(obj)
    
    def deserialize(self, data: bytes) -> Any:
        """Deserialize using pickle."""
        return pickle.loads(data)





