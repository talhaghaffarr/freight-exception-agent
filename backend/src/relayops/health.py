"""Component health with four distinct meanings.

- ``healthy``   the component meets its freshness and error thresholds
- ``degraded``  work continues, but a dependency or data source is impaired
- ``unhealthy`` safe operation cannot continue
- ``unknown``   the component has not reported enough evidence

Readiness is deliberately narrower than status: an optional provider outage
degrades the platform but must not take the API out of the load balancer, while
a required component that cannot prove itself is not ready.
"""

from __future__ import annotations

import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal, Protocol, runtime_checkable

Status = Literal["healthy", "degraded", "unhealthy", "unknown"]

# Ordered by how much attention the state deserves, not by severity of failure:
# "unknown" outranks "healthy" because missing evidence is itself a finding.
_SEVERITY: dict[Status, int] = {"healthy": 0, "unknown": 1, "degraded": 2, "unhealthy": 3}
_BY_SEVERITY: dict[int, Status] = {value: key for key, value in _SEVERITY.items()}


@dataclass(frozen=True, slots=True)
class ComponentHealth:
    name: str
    status: Status
    required: bool = False
    detail: str | None = None
    latency_ms: float = 0.0
    checked_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, object] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "status": self.status,
            "required": self.required,
            "detail": self.detail,
            "latency_ms": round(self.latency_ms, 2),
            "checked_at": self.checked_at.isoformat(),
            "metadata": self.metadata,
        }


@runtime_checkable
class HealthProbe(Protocol):
    name: str
    required: bool

    def check(self) -> ComponentHealth: ...


@dataclass(frozen=True, slots=True)
class HealthReport:
    status: Status
    ready: bool
    components: tuple[ComponentHealth, ...]
    checked_at: datetime

    def component(self, name: str) -> ComponentHealth:
        for component in self.components:
            if component.name == name:
                return component
        raise KeyError(name)

    def as_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "ready": self.ready,
            "checked_at": self.checked_at.isoformat(),
            "components": [component.as_dict() for component in self.components],
        }


class StaticProbe:
    """A probe with a fixed answer. Used by tests and by not-yet-wired services."""

    def __init__(
        self,
        name: str,
        status: Status,
        *,
        required: bool = False,
        detail: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> None:
        self.name = name
        self.required = required
        self._status = status
        self._detail = detail
        self._metadata = metadata or {}

    def check(self) -> ComponentHealth:
        return ComponentHealth(
            name=self.name,
            status=self._status,
            required=self.required,
            detail=self._detail,
            metadata=self._metadata,
        )


def _run_probe(probe: HealthProbe) -> ComponentHealth:
    started = time.perf_counter()
    try:
        result = probe.check()
    except Exception as exc:
        # The exception text can carry a DSN with a password in it. Report the
        # type only; the full traceback goes to the structured log.
        return ComponentHealth(
            name=probe.name,
            status="unhealthy",
            required=getattr(probe, "required", False),
            detail=f"probe raised {type(exc).__name__}",
            latency_ms=(time.perf_counter() - started) * 1000,
        )
    latency_ms = (time.perf_counter() - started) * 1000
    if result.latency_ms:
        return result
    return ComponentHealth(
        name=result.name,
        status=result.status,
        required=result.required,
        detail=result.detail,
        latency_ms=latency_ms,
        checked_at=result.checked_at,
        metadata=result.metadata,
    )


def collect_health(probes: Sequence[HealthProbe]) -> HealthReport:
    components = tuple(_run_probe(probe) for probe in probes)

    severity = 0
    ready = True
    for component in components:
        contribution = _SEVERITY[component.status]
        if not component.required and component.status == "unhealthy":
            # An optional provider being down degrades the platform; it does not
            # make the platform unsafe to run.
            contribution = _SEVERITY["degraded"]
        severity = max(severity, contribution)
        if component.required and component.status in {"unhealthy", "unknown"}:
            ready = False

    return HealthReport(
        status=_BY_SEVERITY[severity] if components else "unknown",
        ready=ready,
        components=components,
        checked_at=datetime.now(UTC),
    )
