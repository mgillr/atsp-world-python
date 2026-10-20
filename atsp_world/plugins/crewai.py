"""CrewAI tool wrapper."""
from __future__ import annotations
from .. import Session

class AtspWorldTool:
    name = "atsp_world"
    description = "Enter ATSP World and search its tool directory / catalyst tasks."

    def __init__(self, url: str | None = None):
        self.s = Session(url) if url else Session()
        self.s.enter()

    def run(self, q: str = "") -> str:
        return str(self.s.discover(q) if q else self.s.tasks())
