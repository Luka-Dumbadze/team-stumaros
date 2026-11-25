"""StumarOS HTTP service: tool use (Week 5). The Week 5+ POST /chat triage endpoint joins this app later.

Run:  uvicorn src.app:app --reload
      curl -s localhost:8000/act -H 'content-type: application/json' -H 'X-Room: 204' \\
           -d '{"question": "When is breakfast?"}'
"""
from __future__ import annotations

from fastapi import FastAPI, Header
from pydantic import BaseModel, Field

from .act import act
from .tools import verified_room

app = FastAPI(title="StumarOS")


class Ask(BaseModel):
    question: str = Field(min_length=1, max_length=1000)


@app.post("/act")
def act_endpoint(body: Ask, x_room: str | None = Header(default=None)) -> dict:
    # Stand-in for real sign-in (Week 12). The room this header names counts only if it is an active stay
    # today (AGENTS.md rule, checked in code); otherwise the caller is a visitor. The model never sees it.
    return act(body.question, room=verified_room(x_room)).to_dict()
