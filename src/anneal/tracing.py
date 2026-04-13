"""Trace logger for Anneal MCP calls. Same JSONL pattern as SpinChain."""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("anneal.tracing")

DEFAULT_TRACE_DIR = Path.home() / ".anneal" / "traces"


@dataclass
class StageTrace:
    name: str
    start_time: float = 0.0
    end_time: float = 0.0
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TraceRecord:
    trace_id: str
    timestamp: str
    input_params: dict[str, Any]
    stages: list[dict[str, Any]] = field(default_factory=list)
    output_summary: dict[str, Any] = field(default_factory=dict)
    total_duration_ms: float = 0.0
    error: str | None = None


class TraceLogger:
    def __init__(self, trace_dir: str | Path | None = None):
        self.trace_dir = Path(trace_dir) if trace_dir else DEFAULT_TRACE_DIR
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        self._trace_file = self.trace_dir / "anneal_traces.jsonl"
        self._active: dict[str, TraceRecord] = {}

    def start_trace(self, input_params: dict[str, Any]) -> str:
        trace_id = uuid.uuid4().hex[:12]
        record = TraceRecord(
            trace_id=trace_id,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            input_params=input_params,
        )
        record._start = time.perf_counter()
        self._active[trace_id] = record
        return trace_id

    def start_stage(self, trace_id: str, stage_name: str) -> StageTrace:
        return StageTrace(name=stage_name, start_time=time.perf_counter())

    def end_stage(self, trace_id: str, stage: StageTrace) -> None:
        stage.end_time = time.perf_counter()
        stage.duration_ms = (stage.end_time - stage.start_time) * 1000
        record = self._active.get(trace_id)
        if record:
            record.stages.append({
                "name": stage.name,
                "duration_ms": round(stage.duration_ms, 2),
                **stage.metadata,
            })

    def finish_trace(
        self, trace_id: str, output_summary: dict[str, Any], error: str | None = None
    ) -> TraceRecord | None:
        record = self._active.pop(trace_id, None)
        if not record:
            return None
        record.total_duration_ms = round((time.perf_counter() - record._start) * 1000, 2)
        record.output_summary = output_summary
        record.error = error
        self._write(record)
        return record

    def _write(self, record: TraceRecord) -> None:
        entry = {
            "trace_id": record.trace_id,
            "timestamp": record.timestamp,
            "input_params": record.input_params,
            "stages": record.stages,
            "output_summary": record.output_summary,
            "total_duration_ms": record.total_duration_ms,
            "error": record.error,
        }
        try:
            with open(self._trace_file, "a") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except OSError as e:
            logger.error("Failed to write trace: %s", e)

    @property
    def trace_file(self) -> Path:
        return self._trace_file


_tracer: TraceLogger | None = None


def get_tracer() -> TraceLogger:
    global _tracer
    if _tracer is None:
        trace_dir = os.environ.get("ANNEAL_TRACE_DIR")
        _tracer = TraceLogger(trace_dir=trace_dir)
    return _tracer
