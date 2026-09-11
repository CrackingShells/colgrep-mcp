"""Pydantic models shared by tools, resources and the adapter (R01 §Pydantic models)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SearchHit(BaseModel):
    hit_id: str = Field(description="Self-describing id: '<absolute file>:<line>-<end_line>'. Pass to `expand`.")
    file: str
    line: int
    end_line: int
    name: str
    qualified_name: str
    unit_type: str
    language: str
    signature: str | None = None
    score: float
    snippet: str | None = Field(default=None, description="First `snippet_lines` lines of the unit.")
    code: str | None = Field(default=None, description="Full unit source; only when include_code=true.")


class SearchResult(BaseModel):
    query: str
    pattern: str | None = None
    paths: list[str]
    hits: list[SearchHit]
    total: int
    truncated: bool
    elapsed_ms: int
    index_updated: bool = False
    notes: list[str] = Field(default_factory=list)


class FileHit(BaseModel):
    file: str
    best_score: float
    hits: int
    top_units: list[str]


class FileResult(BaseModel):
    query: str
    pattern: str | None = None
    paths: list[str]
    files: list[FileHit]
    truncated: bool
    elapsed_ms: int


class ExpandedUnit(BaseModel):
    hit_id: str
    file: str
    line: int
    end_line: int
    code: str | None = None
    truncated: bool = False
    error: str | None = None


class ExpandResult(BaseModel):
    units: list[ExpandedUnit]


class IndexStatus(BaseModel):
    project: str
    indexed: bool
    model: str | None = None
    index_path: str | None = None
    units_indexed: int | None = None
    search_count: int | None = None
    raw: str


class IndexInfo(BaseModel):
    project: str
    model: str
    units_indexed: int
    search_count: int


class IndexList(BaseModel):
    indexes: list[IndexInfo]


class IndexBuildResult(BaseModel):
    project: str
    units_indexed: int | None = None
    elapsed_ms: int
    log_tail: list[str] = Field(default_factory=list)


class IndexClearResult(BaseModel):
    project: str
    cleared: bool


class Doctor(BaseModel):
    colgrep_path: str | None
    version: str | None
    settings: dict[str, str]
    default_root: str | None
    root_source: str
    ok: bool
    problems: list[str] = Field(default_factory=list)
