"""
Tests for the embedding service.

These test the parts that DON'T require live API calls — the deterministic
ID conversion. Testing pure functions like this is fast, free, and catches
real bugs (e.g. if someone changes the namespace UUID and breaks all existing
vector lookups).
"""
from services.embeddings import to_point_id


def test_point_id_is_deterministic():
    """The same entry_id must always map to the same Qdrant point ID."""
    a = to_point_id("507f1f77bcf86cd799439011")
    b = to_point_id("507f1f77bcf86cd799439011")
    assert a == b


def test_point_id_differs_per_entry():
    """Different entries must map to different point IDs."""
    a = to_point_id("507f1f77bcf86cd799439011")
    b = to_point_id("507f1f77bcf86cd799439012")
    assert a != b


def test_point_id_is_valid_uuid():
    """Qdrant requires UUID-format point IDs."""
    import uuid
    result = to_point_id("507f1f77bcf86cd799439011")
    uuid.UUID(result)  # raises if not a valid UUID