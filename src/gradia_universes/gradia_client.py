"""Narrow external conformance client for Gradia's public API contract."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

REQUIRED_PATHS = {
    "/v1/health",
    "/v1/projects/{project_id}/scenarios",
    "/v1/scenario-versions/{scenario_version_id}/reviews",
    "/v1/runs",
    "/v1/runs/{run_id}/scenario-occurrences",
    "/v1/runs/{run_id}/scenario-control",
    "/v1/runs/{run_id}/scenario-operator-events/{event_id}/deliver",
    "/v1/projects/{project_id}/analytics/trajectory-evidence-editions",
    "/v1/analytics/trajectory-detectors/{detector_id}/materializations",
    "/v1/analytics/trajectory-materializations/{materialization_id}/recomputations",
    "/v1/research-release-decisions/{decision_id}/public-universe-release-receipt",
}


@dataclass(frozen=True)
class Response:
    status: int
    body: bytes

    def json(self) -> dict[str, Any]:
        value = json.loads(self.body)
        if not isinstance(value, dict):
            raise ValueError("response_object_required")
        return value


class GradiaClient:
    def __init__(self, base_url: str, token: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self._token = token

    def request(self, method: str, path: str, body: dict[str, Any] | None = None) -> Response:
        headers = {"Accept": "application/json", "User-Agent": "gradia-universe-sample/0.1"}
        payload = None
        if body is not None:
            payload = json.dumps(body, separators=(",", ":")).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        request = urllib.request.Request(
            f"{self.base_url}{path}", data=payload, headers=headers, method=method
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return Response(response.status, response.read())
        except urllib.error.HTTPError as error:
            return Response(error.code, error.read())

    def verify_contract(self) -> dict[str, Any]:
        health = self.request("GET", "/v1/health")
        if health.status != 200:
            raise ValueError(f"gradia_health_failed:{health.status}")
        openapi = self.request("GET", "/openapi.json")
        if openapi.status != 200:
            raise ValueError(f"gradia_openapi_failed:{openapi.status}")
        paths = openapi.json().get("paths")
        if not isinstance(paths, dict):
            raise ValueError("gradia_openapi_paths_missing")
        missing = sorted(REQUIRED_PATHS - set(paths))
        if missing:
            raise ValueError(f"gradia_contract_paths_missing:{','.join(missing)}")
        anonymous = GradiaClient(self.base_url).request(
            "GET", "/v1/projects/public-conformance-probe/scenarios"
        )
        if anonymous.status != 401:
            raise ValueError(f"gradia_anonymous_boundary_unexpected:{anonymous.status}")
        return {
            "base_url": self.base_url,
            "health_status": health.status,
            "openapi_path_count": len(paths),
            "required_paths": sorted(REQUIRED_PATHS),
            "anonymous_project_scenario_status": anonymous.status,
        }
