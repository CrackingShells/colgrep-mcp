# MCP Python SDK v2 traps

## A tool's description has stray leading whitespace {#docstring-verbatim}

**Symptom**: a client shows a tool's description with odd indentation, or a
blank line followed by spaces, even though the handler's docstring reads
fine in the editor.

**Cause**: the SDK takes `handler.__doc__` verbatim as the `tools/list`
description — indentation included. A normally-indented multi-line
docstring ships its leading whitespace to every client on every call.
(`KT-C` §Pain Points.)

**What to do**: never register a tool directly with the SDK's own
decorator. Register through `server.register_tool(mcp, handler, *, title,
annotations)` only — it calls `inspect.getdoc(handler)`, which dedents
exactly the indentation and trailing newline-plus-spaces and nothing else,
so the words the model reads are unchanged. `test_smoke.py::
test_tool_descriptions_are_dedented` pins this; a failure there means a
tool was registered by hand instead of through `register_tool`.

## A cached resource handler raises at registration {#validate-call}

**Symptom**: wrapping a resource handler in `functools.cache` or
`functools.lru_cache` makes it fail (usually at registration or on first
call), even though the same wrapper works fine on a plain function.

**Cause**: the SDK wraps every resource handler in `pydantic.validate_call`,
which inspects the handler's signature; a `cache`/`lru_cache` wrapper
changes that signature in a way `validate_call` rejects. (`KT-C` §Pain
Points.)

**What to do**: put the cache one level down — cache the pure function that
does the work, and have the (uncached) registered handler call it — rather
than caching the handler itself.

## A static resource or the completion callback has no `ctx` {#no-context}

**Symptom**: you need the adapter or settings inside a static resource
handler or the completion callback, but the SDK gives these no request
`Context` to pull them from, unlike a tool handler.

**Cause**: only tool handlers receive a request `Context`. The process-wide
adapter/settings still need to be reachable from handlers the SDK doesn't
hand one to. (`KT-C`; `OBS-C` OV1 — a plain module global corrupts state
across overlapping sessions, e.g. two in-memory test clients whose
lifespans overlap in one process.)

**What to do**: call `server.get_app(ctx=None)` (or `get_adapter`/
`get_settings`, which are thin wrappers over it). It reads a `ContextVar`,
not a module global: every request task the SDK spawns descends from the
task that entered the lifespan and so inherits its value, while two
overlapping lifespans in one process each see only their own. Never
introduce a new module-level `AppContext`-shaped global to work around a
missing `ctx` — that is exactly the bug `get_app` fixed.

## `roots/list` or elicitation silently does nothing {#protocol-deprecation}

**Symptom**: a client doesn't answer `roots/list`, elicitation goes
nowhere, or you see deprecation warnings mentioning the MCP protocol at
startup.

**Cause**: MCP protocol revision 2026-07-28 deprecates roots, sampling,
logging and the original handshake. `roots/list` and elicitation only work
on sessions opened in legacy mode (`Client(..., mode="legacy")`, as the test
suite does); every `ctx.info` call triggers a deprecation warning, filtered
at startup so it doesn't spam a client. Because the logging capability is
itself deprecated, client notifications are not guaranteed to be honoured.
(`KT-B` §Root Causes; `R02` feature matrix.)

**What to do**: when a test or a real client needs roots or elicitation,
open the session in legacy mode. Never assume a deprecation warning at
startup indicates a bug to silence differently — it's filtered
deliberately. Send every client notification through
`logging_utils.safe_log`/`safe_progress`/`safe_notify_resource_updated`
(`maintainer-policy` §One idiom per concern)
so a client that has dropped the logging capability never fails a tool
call — never wrap a notification in a tool's own bare
`try/except Exception: pass`.

## A Windows client's root path won't resolve {#windows-roots}

**Symptom**: on Windows, a client-supplied root like
`file:///C:/Users/name/project` fails to resolve to a usable path, or
resolves to something with a leading slash before the drive letter.

**Cause**: client roots arrive as `file:///C:/Users/...` URIs. Building a
path with `Path(uri.path)` keeps the URI's leading `/` before the drive
letter, which is not a valid Windows path. (`KT-C` §Pain Points.)

**What to do**: convert a root URI with `urllib.request.url2pathname`,
never `Path(uri.path)` — this is exactly what `paths.py` does today; don't
reintroduce the `Path(uri.path)` pattern in a new caller.
