from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .planner import generate_personalized_plan

app = FastAPI(
    title="AI-Powered Personal Diet Planner API",
    version="0.1.0",
    description="Backend API starter for the personal diet planner project.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProfileInput(BaseModel):
    """Validated profile details submitted by the planner form."""

    age: int = Field(ge=13, le=120)
    sex: Literal["female", "male", "other"]
    heightCm: int = Field(ge=80, le=250)
    weightKg: float = Field(ge=25, le=350)
    activity: Literal["low", "light", "moderate", "high"]
    goal: Literal["balanced", "lose", "maintain", "gain", "energy"]
    diet: Literal["omnivore", "vegetarian", "vegan", "pescatarian", "other"]
    allergies: str = Field(default="", max_length=300)
    budget: str = Field(min_length=1, max_length=100)
    cuisine: str = Field(default="", max_length=200)
    timeline: Literal["week", "two-weeks", "month"]


@app.get("/", tags=["health"])
def read_root() -> dict[str, str]:
    """Basic endpoint confirming that the API is responding."""
    return {"message": "Personal Diet Planner API is ready"}


@app.post("/profiles", tags=["profiles"])
def create_profile(profile: ProfileInput) -> dict[str, object]:
    """Accept a profile and echo it back; persistence will be added later."""
    return {
        "message": "Profile received successfully",
        "profile": profile.model_dump(),
    }


@app.post("/plans/generate", tags=["plans"])
def create_sample_plan(profile: ProfileInput) -> dict[str, object]:
    """Generate AI-arranged educational meal ideas with a local fallback."""
    plan = generate_personalized_plan(profile.model_dump())
    if plan["blocked"]:
        raise HTTPException(status_code=422, detail=plan["message"])
    plan.pop("blocked")
    return plan
