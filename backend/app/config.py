"""Application settings.

Scaffolding only (sprint-harness Planner pass, sprint 2026-07-25-collaborative-
assertions). No business logic — just the settings shape a Developer track
will read from. Safe to extend; do not add computed/business behavior here
without going through a Developer-owned sprint item.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LEXGRAPH_")

    database_url: str = "sqlite:///:memory:"
    environment: str = "test"


def get_settings() -> Settings:
    return Settings()
