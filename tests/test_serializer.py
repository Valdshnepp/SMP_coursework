"""Tests for message serialization."""

from actor_system.messaging.serializer import JSONSerializer


class SampleMessage:
    """Test message class."""
    
    def __init__(self, value: str, number: int):
        self.value = value
        self.number = number


def test_json_serialize_primitive():
    """Test serializing primitive types."""
    serializer = JSONSerializer()
    
    data = serializer.serialize("hello")
    result = serializer.deserialize(data)
    assert result == "hello"
    
    data = serializer.serialize(42)
    result = serializer.deserialize(data)
    assert result == 42
    


def test_json_serialize_dict():
    """Test serializing dictionaries."""
    serializer = JSONSerializer()
    
    obj = {"key1": "value1", "key2": 42}
    data = serializer.serialize(obj)
    result = serializer.deserialize(data)
    
    assert result == obj


def test_json_serialize_list():
    """Test serializing lists."""
    serializer = JSONSerializer()
    
    obj = [1, 2, 3, "hello"]
    data = serializer.serialize(obj)
    result = serializer.deserialize(data)
    
    assert result == obj


def test_json_serialize_object():
    """Test serializing custom objects."""
    serializer = JSONSerializer()
    
    obj = SampleMessage("hello", 42)
    data = serializer.serialize(obj)
    result = serializer.deserialize(data)
    
    assert isinstance(result, dict)
    assert result["__class__"] == "SampleMessage"
    assert result["value"] == "hello"
    assert result["number"] == 42


def test_json_serialize_nested():
    """Test serializing nested structures."""
    serializer = JSONSerializer()
    
    obj = {
        "outer": SampleMessage("inner", 10),
        "list": [SampleMessage("item1", 1), SampleMessage("item2", 2)]
    }
    
    data = serializer.serialize(obj)
    result = serializer.deserialize(data)
    
    assert isinstance(result, dict)
    assert isinstance(result["outer"], dict)
    assert result["outer"]["__class__"] == "SampleMessage"
    assert isinstance(result["list"], list)
    assert result["list"][0]["__class__"] == "SampleMessage"
