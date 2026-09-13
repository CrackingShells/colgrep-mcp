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
    location_verified: bool = Field(
        default=False,
        description="True when `line`/`end_line` were re-derived via locate_unit and matched exactly "
        "(R05 D1: colgrep's own line/end_line are frequently wrong). False means the reported "
        "values are an unverified fallback.",
    )


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
    requested_path: str = Field(
        default="",
        description="The path `status()` was called with, verbatim. May differ from `project` "
        "(R05 D3): colgrep folds a path into the nearest already-registered ancestor project.",
    )


class IndexInfo(BaseModel):
    project: str
    model: str
    units_indexed: int
    search_count: int
    # Store-derived fields (index_housekeeping R01 §C4); all `None` when the
    # store root could not be derived or the project is absent from the store.
    path_exists: bool | None = Field(default=None, description="Whether `project` still exists on disk.")
    size_bytes: int | None = Field(default=None, description="Bytes under the index directory.")
    last_modified: str | None = Field(default=None, description="ISO 8601 UTC time of the last search or update.")
    shadowed_by: str | None = Field(
        default=None, description="An indexed, existing ancestor project that double-indexes this one's units."
    )
    stale: str | None = Field(
        default=None,
        description="`orphaned` (path gone), `machine_state` (temp, cache or hidden tree) or `shadowed`; "
        "`None` for a live project. `cold` needs parameters and is reported by `index_prune` only.",
    )


class IndexList(BaseModel):
    indexes: list[IndexInfo]
    store_root: str | None = Field(default=None, description="The index store directory, when it could be derived.")
    total_bytes: int | None = Field(default=None, description="Bytes under the whole store.")
    total: int | None = Field(default=None, description="Indexed projects before any `stale_only` filter.")


class IndexBuildResult(BaseModel):
    project: str
    units_indexed: int | None = None
    elapsed_ms: int
    log_tail: list[str] = Field(default_factory=list)
    added: int | None = None
    changed: int | None = None
    deleted: int | None = None
    unchanged: int | None = None
    up_to_date: bool = False


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
