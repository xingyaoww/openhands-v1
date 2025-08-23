from typing import Any, TypeVar
from pydantic import BaseModel, Field, ConfigDict, create_model

S = TypeVar("S", bound="Schema")


def py_type(spec: dict[str, Any]) -> Any:
    """Map JSON schema types to Python types."""
    t = spec.get("type")
    if t == "array":
        items = spec.get("items", {})
        inner = py_type(items) if isinstance(items, dict) else Any
        return list[inner]  # type: ignore[index]
    if t == "object":
        return dict[str, Any]
    _map = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
    }
    if t in _map:
        return _map[t]
    return Any


class Schema(BaseModel):
    """Base schema for input action / output observation."""

    model_config = ConfigDict(extra="forbid")

    @classmethod
    def to_mcp_schema(cls) -> dict[str, Any]:
        """Convert to JSON schema format compatible with MCP."""
        js = cls.model_json_schema()
        req = [n for n, f in cls.model_fields.items() if f.is_required()]
        return {
            "type": "object",
            "properties": js.get("properties", {}) or {},
            "required": req or [],
        }

    @classmethod
    def from_mcp_schema(
        cls: type[S], model_name: str, schema: dict[str, Any]
    ) -> type["S"]:
        """Create a Schema subclass from an MCP/JSON Schema object."""
        assert isinstance(schema, dict), "Schema must be a dict"
        assert schema.get("type") == "object", "Only object schemas are supported"

        props: dict[str, Any] = schema.get("properties", {}) or {}
        required = set(schema.get("required", []) or [])

        fields: dict[str, tuple] = {}
        for fname, spec in props.items():
            tp = py_type(spec if isinstance(spec, dict) else {})
            default = ... if fname in required else None
            desc: str | None = (
                spec.get("description") if isinstance(spec, dict) else None
            )
            fields[fname] = (
                tp,
                Field(default=default, description=desc)
                if desc
                else Field(default=default),
            )
        return create_model(model_name, __base__=cls, **fields)  # type: ignore[return-value]


class ActionBase(Schema):
    """Base schema for input action."""

    pass


class ObservationBase(Schema):
    """Base schema for output observation."""

    model_config = ConfigDict(extra="allow")
