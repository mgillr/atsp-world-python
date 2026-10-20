"""LangChain tool wrapper — HTTP client only."""
from __future__ import annotations
from typing import Any
from .. import Session

def get_tools(url: str | None = None) -> list[Any]:
    try:
        from langchain_core.tools import tool
    except ImportError as e:
        raise ImportError("pip install langchain-core") from e
    s = Session(url) if url else Session()
    s.enter()

    @tool
    def atsp_discover(q: str) -> str:
        """Search the ATSP World tool directory."""
        return str(s.discover(q))

    @tool
    def atsp_tasks() -> str:
        """List ATSP World catalyst tasks."""
        return str(s.tasks())

    return [atsp_discover, atsp_tasks]
