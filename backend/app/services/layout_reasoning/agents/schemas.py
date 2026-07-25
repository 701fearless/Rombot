"""Multi-agent shared output schema for spatial advice."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AgentSuggestion(BaseModel):
    """Unified suggestion protocol used by Layout and Lifestyle agents."""

    id: str
    category: str  # Safety | Accessibility | Layout | Lifestyle | Decoration | ...
    priority: str  # High | Medium | Low
    title: str
    reason: str
    action: str
    confidence: float = Field(ge=0, le=1, default=0.8)


class AgentOutput(BaseModel):
    agent: str  # layout | lifestyle
    suggestions: list[AgentSuggestion] = Field(default_factory=list)


class CoordinatorTask(BaseModel):
    """Structured dispatch object produced by the Coordinator Agent."""

    room: dict
    furniture: list[dict] = Field(default_factory=list)
    openings: list[dict] = Field(default_factory=list)
    geometryChecks: list[dict] = Field(default_factory=list)
    candidate: dict
    userProfile: dict = Field(default_factory=dict)
    layoutFocus: list[str] = Field(default_factory=list)
    lifestyleFocus: list[str] = Field(default_factory=list)


class ScoreDimensions(BaseModel):
    layout: int = Field(ge=0, le=100, default=70)
    comfort: int = Field(ge=0, le=100, default=70)
    functionality: int = Field(ge=0, le=100, default=70)
    lifestyleCompatibility: int = Field(ge=0, le=100, default=70)


class AgentReport(BaseModel):
    score: int = Field(ge=0, le=100)
    scoreDimensions: ScoreDimensions
    summary: str
    highlights: list[str] = Field(default_factory=list)
    suggestions: list[AgentSuggestion] = Field(default_factory=list)
    agentOutputs: list[AgentOutput] = Field(default_factory=list)
    coordinator: CoordinatorTask | None = None
