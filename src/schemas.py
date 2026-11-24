"""Output contract for the triage slice (mirrors the Task schema in the root AGENTS.md)."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

DEPARTMENTS = ("housekeeping", "maintenance", "front_desk")
PRIORITIES = ("low", "normal", "urgent")
INTENTS = ("question", "service", "composite", "unclear")
MAX_TASK_CHARS = 120
MAX_REPLY_CHARS = 800


class SchemaError(ValueError):
    """Model output does not match the contract."""


@dataclass
class Task:
    room: str
    department: str
    priority: str
    task: str

    def __post_init__(self) -> None:
        if not isinstance(self.room, str) or not self.room:
            raise SchemaError("task.room must be a non-empty string")
        if self.department not in DEPARTMENTS:
            raise SchemaError(f"task.department {self.department!r} not in {DEPARTMENTS}")
        if self.priority not in PRIORITIES:
            raise SchemaError(f"task.priority {self.priority!r} not in {PRIORITIES}")
        if not isinstance(self.task, str) or not self.task.strip():
            raise SchemaError("task.task must be a non-empty string")
        if len(self.task) > MAX_TASK_CHARS:
            raise SchemaError(f"task.task longer than {MAX_TASK_CHARS} chars")


@dataclass
class ProposedTask:
    """A task as the model proposes it: no room, the code attaches that."""
    department: str
    priority: str
    task: str


@dataclass
class ModelOutput:
    intent: str
    reply: str
    tasks: list[ProposedTask]
    cited_sections: list[str]
    needs_clarification: bool


def parse_model_output(data: object) -> ModelOutput:
    """Validate the model's JSON object. Raises SchemaError on any deviation."""
    if not isinstance(data, dict):
        raise SchemaError("top-level JSON must be an object")
    missing = {"intent", "reply", "tasks", "cited_sections", "needs_clarification"} - data.keys()
    if missing:
        raise SchemaError(f"missing keys: {sorted(missing)}")
    if data["intent"] not in INTENTS:
        raise SchemaError(f"intent {data['intent']!r} not in {INTENTS}")
    reply = data["reply"]
    if not isinstance(reply, str) or not reply.strip():
        raise SchemaError("reply must be a non-empty string")
    if len(reply) > MAX_REPLY_CHARS:
        raise SchemaError(f"reply longer than {MAX_REPLY_CHARS} chars")
    if not isinstance(data["tasks"], list):
        raise SchemaError("tasks must be a list")
    tasks = []
    for item in data["tasks"]:
        if not isinstance(item, dict):
            raise SchemaError("each task must be an object")
        # Validate with a placeholder room; the real room is attached by code later.
        t = Task(room="?", department=item.get("department"), priority=item.get("priority"),
                 task=item.get("task"))
        tasks.append(ProposedTask(t.department, t.priority, t.task))
    cited = data["cited_sections"]
    if not isinstance(cited, list) or not all(isinstance(c, str) for c in cited):
        raise SchemaError("cited_sections must be a list of strings")
    if not isinstance(data["needs_clarification"], bool):
        raise SchemaError("needs_clarification must be a boolean")
    return ModelOutput(data["intent"], reply.strip(), tasks, cited, data["needs_clarification"])


@dataclass
class Usage:
    attempts: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: int = 0
    tokens_estimated: bool = False


@dataclass
class TriageResult:
    request_id: str
    mode: str
    model: str
    reply: str
    tasks: list[Task]
    room: str | None
    room_validated: bool
    room_status: str
    needs_clarification: bool
    sections_sent: list[str]
    guardrail_events: list[str] = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)
    cited_sections: list[str] = field(default_factory=list)  # as the model reported them (golden must_cite)

    def to_dict(self) -> dict:
        return asdict(self)
