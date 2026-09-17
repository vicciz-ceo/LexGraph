"""One validated suggestion contract shared by REST, MCP and local CLI."""
from typing import Literal
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
from app.routers.assertions import AssertionCreate, _create_assertion, get_session, get_current_user_id

router = APIRouter(prefix="/api/v1/agent", tags=["agents"])


class AgentProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    platform: str = Field(min_length=1, max_length=120)
    model: str | None = Field(default=None, min_length=1, max_length=120)
    run_id: str | None = Field(default=None, min_length=1, max_length=120)


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
