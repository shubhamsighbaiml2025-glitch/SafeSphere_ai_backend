from typing import Any


def serialize_document(doc: dict[str, Any]) -> dict[str, Any]:
    serialized = dict(doc)
    if "_id" in serialized:
        serialized["id"] = str(serialized.pop("_id"))
    return serialized

