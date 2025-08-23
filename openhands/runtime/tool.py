from typing import Any, Callable
from pydantic import BaseModel
from .schema import ActionBase, ObservationBase, Schema


class ToolAnnotations(BaseModel):
    title: str | None = None
    readOnlyHint: bool | None = None
    destructiveHint: bool | None = None
    idempotentHint: bool | None = None
    openWorldHint: bool | None = None


class Tool:
    """Tool that wraps an executor function with input/output validation and schema.

    - Normalize input/output schemas (class or dict) into both model+schema.
    - Validate inputs before execute.
    - Coerce outputs only if an output model is defined; else return vanilla JSON.
    - Export MCP tool description.
    """

    def __init__(
        self,
        *,
        name: str,
        input_schema: type[ActionBase] | dict[str, Any],
        output_schema: type[ObservationBase] | dict[str, Any] | None = None,
        description: str | None = None,
        annotations: ToolAnnotations | None = None,
        _meta: dict[str, Any] | None = None,
        execute_fn: Callable[[ActionBase], ObservationBase] | None = None,
    ):
        self.name = name
        self.description = description
        self.annotations = annotations
        self._meta = _meta
        self._set_input_schema(input_schema)
        self._set_output_schema(output_schema)

        self.execute_fn = execute_fn

    def _set_input_schema(
        self, input_schema: dict[str, Any] | type[ActionBase]
    ) -> None:
        # ---- INPUT: class or dict -> model + schema
        self.action_type: type[ActionBase]
        self.input_schema: dict[str, Any]
        if isinstance(input_schema, type) and issubclass(input_schema, Schema):
            self.action_type = input_schema
            self.input_schema = input_schema.to_mcp_schema()
        elif isinstance(input_schema, dict):
            self.input_schema = input_schema
            self.action_type = ActionBase.from_mcp_schema(
                f"{self.name}Action", input_schema
            )
        else:
            raise TypeError(
                "input_schema must be ActionBase subclass or dict JSON schema"
            )

    def _set_output_schema(
        self, output_schema: dict[str, Any] | type[ObservationBase] | None
    ) -> None:
        # ---- OUTPUT: optional class or dict -> model + schema
        self.observation_type: type[ObservationBase] | None
        self.output_schema: dict[str, Any] | None
        if output_schema is None:
            self.observation_type = None
            self.output_schema = None
        elif isinstance(output_schema, type) and issubclass(output_schema, Schema):
            self.observation_type = output_schema
            self.output_schema = output_schema.to_mcp_schema()
        elif isinstance(output_schema, dict):
            self.output_schema = output_schema
            self.observation_type = ObservationBase.from_mcp_schema(
                f"{self.name}Observation", output_schema
            )
        else:
            raise TypeError(
                "output_schema must be ObservationBase subclass, dict, or None"
            )

    def call(self, action: ActionBase) -> ObservationBase:
        if self.execute_fn is None:
            raise NotImplementedError(f"Tool '{self.name}' has no executor")

        # Execute
        result = self.execute_fn(action)

        # Coerce output only if we declared a model; else wrap in base ObservationBase
        if self.observation_type:
            if isinstance(result, self.observation_type):
                return result
            return self.observation_type.model_validate(result)
        else:
            # When no output schema is defined, wrap the result in ObservationBase
            if isinstance(result, ObservationBase):
                return result
            elif isinstance(result, BaseModel):
                return ObservationBase.model_validate(result.model_dump())
            elif isinstance(result, dict):
                return ObservationBase.model_validate(result)
            raise TypeError(
                "Output must be dict or BaseModel when no output schema is defined"
            )

    def to_mcp_tool(self) -> dict[str, Any]:
        out = {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }
        if self.annotations:
            out["annotations"] = self.annotations
        if self._meta is not None:
            out["_meta"] = self._meta
        if self.output_schema:
            out["outputSchema"] = self.output_schema
        return out
