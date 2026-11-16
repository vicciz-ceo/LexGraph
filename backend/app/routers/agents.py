"""One validated suggestion contract shared by REST, MCP and local CLI."""
from typing import Literal
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator
from pydantic_core import PydanticCustomError
from sqlalchemy.orm import Session
from app.routers.assertions import AssertionCreate, _create_assertion, get_session, get_current_user_id
from app.services.validation import sanitize_for_storage

router = APIRouter(prefix="/api/v1/agent", tags=["agents"])


class AgentProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    platform: str = Field(min_length=1, max_length=120)
    model: str | None = Field(default=None, min_length=1, max_length=120)
    run_id: str | None = Field(default=None, min_length=1, max_length=120)

    @field_validator("platform", "model", "run_id")
    @classmethod
    def _without_markup(cls, value: str | None, info: ValidationInfo) -> str | None:
        # review:19: provenance is stored in the audit trail and returned as
        # agent_provenance, so markup is removed as from any submitted text
        # (after the length cap above). A value that is nothing but markup
        # is refused rather than stored empty.
        if value is None:
            return None
        text = sanitize_for_storage(value).strip()
        if not text:
            raise PydanticCustomError(
                "provenance_without_text", f"agent.{info.field_name} has no text once markup is removed")
        return text


class AgentAssertionCreate(AssertionCreate):
    model_config = ConfigDict(extra="forbid")
    agent: AgentProvenance
    confidence: float | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)
    save_as: Literal["draft", "proposed"] = "proposed"


@router.post("/assertions", status_code=201)
def suggest_assertion(body: AgentAssertionCreate, session: Session = Depends(get_session),
                      user_id: str = Depends(get_current_user_id)) -> dict:
    return _create_assertion(body, session, user_id,
                             agent=body.agent.model_dump(), confidence=body.confidence)
