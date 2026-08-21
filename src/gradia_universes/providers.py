"""Capped, key-from-environment adapters for the public live-model panel.

The adapters deliberately expose one common text-in/text-out surface. Native
tool calling is a separate scaffold condition because changing the provider
tool protocol changes the agent, not merely the model.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

from .canonical import digest
from .live_runner import BudgetStop, Completion, ProviderFailure

ProviderName = Literal["openai", "anthropic", "xai", "gemini"]

ADAPTER_VERSIONS: dict[ProviderName, str] = {
    "openai": "openai-responses-rest.v2",
    "anthropic": "anthropic-messages-rest.v2",
    "xai": "xai-responses-rest.v2",
    "gemini": "gemini-generate-content-rest.v2",
}

KEY_ENVIRONMENTS: dict[ProviderName, str] = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "xai": "XAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
}


Transport = Callable[
    [str, dict[str, str], dict[str, Any], float],
    tuple[int, bytes],
]
ResponseSink = Callable[[bytes], None]
MAX_PROMPT_BYTES = 2 * 1024 * 1024


def urlopen_transport(
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout_seconds: float,
) -> tuple[int, bytes]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, separators=(",", ":")).encode(),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        # Never echo a provider body. It can contain user input, account
        # metadata or provider-generated details that do not belong in a log.
        error.read()
        return error.code, b""
    except (TimeoutError, urllib.error.URLError, OSError) as error:
        raise ProviderFailure("provider_transport_failure") from error


@dataclass(frozen=True)
class SpendPolicy:
    max_requests: int
    max_output_tokens_per_request: int
    max_total_output_tokens: int
    max_cost_usd: float
    input_usd_per_million_tokens: float
    output_usd_per_million_tokens: float

    def __post_init__(self) -> None:
        integer_fields = (
            self.max_requests,
            self.max_output_tokens_per_request,
            self.max_total_output_tokens,
        )
        if any(
            not isinstance(value, int) or isinstance(value, bool)
            for value in integer_fields
        ):
            raise ValueError("spend_policy_integer_limit_invalid")
        price_fields = (
            self.max_cost_usd,
            self.input_usd_per_million_tokens,
            self.output_usd_per_million_tokens,
        )
        if any(
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(value)
            for value in price_fields
        ):
            raise ValueError("spend_policy_price_invalid")
        if not 1 <= self.max_requests <= 10_000:
            raise ValueError("spend_policy_request_limit_invalid")
        if not 1 <= self.max_output_tokens_per_request <= 32_768:
            raise ValueError("spend_policy_output_limit_invalid")
        if not self.max_output_tokens_per_request <= self.max_total_output_tokens <= 10_000_000:
            raise ValueError("spend_policy_total_output_limit_invalid")
        if not 0 < self.max_cost_usd <= 10_000:
            raise ValueError("spend_policy_cost_limit_invalid")
        if not 0 <= self.input_usd_per_million_tokens <= 10_000:
            raise ValueError("spend_policy_input_price_invalid")
        if not 0 <= self.output_usd_per_million_tokens <= 10_000:
            raise ValueError("spend_policy_output_price_invalid")

    def as_dict(self) -> dict[str, int | float]:
        return {
            "max_requests": self.max_requests,
            "max_output_tokens_per_request": self.max_output_tokens_per_request,
            "max_total_output_tokens": self.max_total_output_tokens,
            "max_cost_usd": self.max_cost_usd,
            "input_usd_per_million_tokens": self.input_usd_per_million_tokens,
            "output_usd_per_million_tokens": self.output_usd_per_million_tokens,
        }


class CappedProviderBackend:
    """One provider/model cell with conservative pre-request reservations."""

    def __init__(
        self,
        provider: ProviderName,
        model: str,
        policy: SpendPolicy,
        *,
        transport: Transport = urlopen_transport,
        timeout_seconds: float = 60.0,
        api_key: str | None = None,
        response_sink: ResponseSink | None = None,
        temperature: float | None = None,
    ) -> None:
        validate_model_pin(model)
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not math.isfinite(timeout_seconds)
            or not 1 <= timeout_seconds <= 300
        ):
            raise ValueError("provider_timeout_invalid")
        temperature_max = 1 if provider == "anthropic" else 2
        if (
            temperature is not None
            and (
                isinstance(temperature, bool)
                or not isinstance(temperature, (int, float))
                or not math.isfinite(temperature)
                or not 0 <= temperature <= temperature_max
            )
        ):
            raise ValueError("provider_temperature_invalid")
        key = api_key if api_key is not None else os.environ.get(KEY_ENVIRONMENTS[provider])
        if not key:
            raise ValueError(f"provider_key_missing:{KEY_ENVIRONMENTS[provider]}")
        self.provider = provider
        self.model = model
        self.adapter_version = ADAPTER_VERSIONS[provider]
        self._key = key
        self._policy = policy
        self._transport = transport
        self._timeout_seconds = timeout_seconds
        self._response_sink = response_sink
        self._temperature = temperature
        self._requests = 0
        self._output_tokens = 0
        self._reserved_output_tokens = 0
        self._estimated_cost_usd = 0.0
        self._reserved_cost_usd = 0.0
        self._terminal_failure: ProviderFailure | None = None

    @property
    def policy_sha256(self) -> str:
        return digest(self._policy.as_dict())

    @property
    def estimated_cost_usd(self) -> float:
        return self._estimated_cost_usd

    @property
    def reserved_cost_usd(self) -> float:
        return self._reserved_cost_usd

    @property
    def reserved_output_tokens(self) -> int:
        return self._reserved_output_tokens

    @property
    def sampling_policy(self) -> dict[str, str | float | None]:
        return {
            "temperature": self._temperature,
            "temperature_posture": (
                "explicit" if self._temperature is not None else "provider_default"
            ),
            "provider_seed": None,
            "repeat_semantics": "independent_provider_request",
        }

    @property
    def sampling_policy_sha256(self) -> str:
        return digest(self.sampling_policy)

    def _reserve(self, prompt: str) -> float:
        prompt_bytes = len(prompt.encode())
        if prompt_bytes > MAX_PROMPT_BYTES:
            raise BudgetStop("provider_prompt_bytes_limit_exhausted")
        if self._requests >= self._policy.max_requests:
            raise BudgetStop("provider_request_budget_exhausted")
        if (
            self._reserved_output_tokens + self._policy.max_output_tokens_per_request
            > self._policy.max_total_output_tokens
        ):
            raise BudgetStop("provider_output_token_budget_exhausted")
        # A UTF-8 byte count plus framing allowance is deliberately conservative
        # for ordinary byte-level tokenization. It is still a local estimate,
        # not a provider invoice or account-side spending guarantee.
        reserved_input_tokens = prompt_bytes + 64
        reserved_cost = (
            reserved_input_tokens * self._policy.input_usd_per_million_tokens
            + self._policy.max_output_tokens_per_request
            * self._policy.output_usd_per_million_tokens
        ) / 1_000_000
        if self._reserved_cost_usd + reserved_cost > self._policy.max_cost_usd:
            raise BudgetStop("provider_cost_budget_exhausted")
        return reserved_cost

    def _request(self, prompt: str) -> tuple[dict[str, Any], bytes]:
        reserved_cost = self._reserve(prompt)
        url, headers, payload = self._request_contract(prompt)
        # Consume the conservative reservation before dispatch. A timeout or
        # provider error can be billable even when no usable response returns.
        self._requests += 1
        self._reserved_output_tokens += self._policy.max_output_tokens_per_request
        self._reserved_cost_usd += reserved_cost
        status, raw = self._transport(url, headers, payload, self._timeout_seconds)
        if status < 200 or status >= 300:
            raise ProviderFailure(f"provider_http_status:{status}")
        if len(raw) > 16 * 1024 * 1024:
            raise ProviderFailure("provider_response_too_large")
        if self._response_sink is not None:
            try:
                self._response_sink(raw)
            except OSError as error:
                raise ProviderFailure("provider_response_retention_failed") from error
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as error:
            raise ProviderFailure("provider_response_invalid_json") from error
        if not isinstance(value, dict):
            raise ProviderFailure("provider_response_not_object")
        return value, raw

    def complete(self, prompt: str) -> Completion:
        if self._terminal_failure is not None:
            raise ProviderFailure("provider_cell_latched_after_failure")
        try:
            value, raw = self._request(prompt)
            response_id, resolved_model, text, input_tokens, output_tokens = (
                self._parse_response(value)
            )
            if input_tokens is None or output_tokens is None:
                raise ProviderFailure("provider_usage_missing_after_spend")
            if (
                input_tokens < 0
                or output_tokens < 0
                or input_tokens > 10_000_000_000
                or output_tokens > 10_000_000_000
            ):
                raise ProviderFailure("provider_usage_invalid")
            incremental_cost = (
                input_tokens * self._policy.input_usd_per_million_tokens
                + output_tokens * self._policy.output_usd_per_million_tokens
            ) / 1_000_000
            # Once structurally valid provider usage is available, retain its
            # operator-price estimate even if a later integrity limit makes the
            # cell ineligible. The request may still have been billed.
            self._output_tokens += output_tokens
            self._estimated_cost_usd += incremental_cost
            if resolved_model != self.model:
                raise ProviderFailure("provider_resolved_model_mismatch")
            if output_tokens > self._policy.max_output_tokens_per_request:
                raise ProviderFailure("provider_output_limit_not_honored")
            if self._output_tokens > self._policy.max_total_output_tokens:
                raise ProviderFailure("provider_total_output_limit_exceeded")
            if self._estimated_cost_usd > self._policy.max_cost_usd:
                raise ProviderFailure("provider_reported_cost_limit_exceeded")
        except ProviderFailure as error:
            self._terminal_failure = error
            raise
        return Completion(
            provider=self.provider,
            model=self.model,
            adapter_version=self.adapter_version,
            response_id=response_id,
            output_text=text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            provider_response_sha256=hashlib.sha256(raw).hexdigest(),
            estimated_cost_usd=incremental_cost,
            cumulative_estimated_cost_usd=self._estimated_cost_usd,
            budget_policy_sha256=self.policy_sha256,
            resolved_model=resolved_model,
            cumulative_reserved_cost_usd=self._reserved_cost_usd,
        )

    def _request_contract(
        self, prompt: str
    ) -> tuple[str, dict[str, str], dict[str, Any]]:
        common_headers = {"Content-Type": "application/json"}
        max_output = self._policy.max_output_tokens_per_request
        if self.provider in {"openai", "xai"}:
            base = "https://api.openai.com" if self.provider == "openai" else "https://api.x.ai"
            payload: dict[str, Any] = {
                "model": self.model,
                "input": prompt,
                "max_output_tokens": max_output,
                "store": False,
            }
            if self._temperature is not None:
                payload["temperature"] = self._temperature
            return (
                f"{base}/v1/responses",
                {**common_headers, "Authorization": f"Bearer {self._key}"},
                payload,
            )
        if self.provider == "anthropic":
            payload = {
                "model": self.model,
                "max_tokens": max_output,
                "messages": [{"role": "user", "content": prompt}],
            }
            if self._temperature is not None:
                payload["temperature"] = self._temperature
            return (
                "https://api.anthropic.com/v1/messages",
                {
                    **common_headers,
                    "x-api-key": self._key,
                    "anthropic-version": "2023-06-01",
                },
                payload,
            )
        encoded_model = urllib.parse.quote(self.model, safe="-_.")
        generation_config: dict[str, Any] = {"maxOutputTokens": max_output}
        if self._temperature is not None:
            generation_config["temperature"] = self._temperature
        return (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{encoded_model}:generateContent",
            {**common_headers, "x-goog-api-key": self._key},
            {
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": generation_config,
            },
        )

    def _parse_response(
        self, value: dict[str, Any]
    ) -> tuple[str, str, str, int | None, int | None]:
        if self.provider in {"openai", "xai"}:
            output = value.get("output")
            text_parts: list[str] = []
            if isinstance(output, list):
                for item in output:
                    if not isinstance(item, dict) or not isinstance(item.get("content"), list):
                        continue
                    for content in item["content"]:
                        if (
                            isinstance(content, dict)
                            and content.get("type") == "output_text"
                            and isinstance(content.get("text"), str)
                        ):
                            text_parts.append(content["text"])
            usage = value.get("usage")
            usage = usage if isinstance(usage, dict) else {}
            return (
                _response_id(value),
                _resolved_model(value, "model"),
                _require_text(text_parts),
                _optional_int(usage.get("input_tokens")),
                _optional_int(usage.get("output_tokens")),
            )
        if self.provider == "anthropic":
            content = value.get("content")
            text_parts = []
            if isinstance(content, list):
                text_parts = [
                    item["text"]
                    for item in content
                    if isinstance(item, dict)
                    and item.get("type") == "text"
                    and isinstance(item.get("text"), str)
                ]
            usage = value.get("usage")
            usage = usage if isinstance(usage, dict) else {}
            return (
                _response_id(value),
                _resolved_model(value, "model"),
                _require_text(text_parts),
                _optional_int(usage.get("input_tokens")),
                _optional_int(usage.get("output_tokens")),
            )
        candidates = value.get("candidates")
        text_parts = []
        if isinstance(candidates, list) and candidates and isinstance(candidates[0], dict):
            content = candidates[0].get("content")
            if isinstance(content, dict) and isinstance(content.get("parts"), list):
                text_parts = [
                    item["text"]
                    for item in content["parts"]
                    if isinstance(item, dict) and isinstance(item.get("text"), str)
                ]
        usage = value.get("usageMetadata")
        usage = usage if isinstance(usage, dict) else {}
        response_id = value.get("responseId")
        if not isinstance(response_id, str) or not response_id:
            raise ProviderFailure("provider_response_id_missing")
        prompt_tokens = _optional_int(usage.get("promptTokenCount"))
        candidates_tokens = _optional_int(usage.get("candidatesTokenCount"))
        thoughts_tokens = _optional_int(usage.get("thoughtsTokenCount")) or 0
        total_tokens = _optional_int(usage.get("totalTokenCount"))
        output_tokens = None
        if prompt_tokens is not None and total_tokens is not None:
            output_tokens = total_tokens - prompt_tokens
            if output_tokens < 0:
                raise ProviderFailure("provider_usage_invalid")
        elif candidates_tokens is not None:
            output_tokens = candidates_tokens + thoughts_tokens
        return (
            response_id,
            _resolved_model(value, "modelVersion"),
            _require_text(text_parts),
            prompt_tokens,
            output_tokens,
        )


def _response_id(value: dict[str, Any]) -> str:
    response_id = value.get("id")
    if not isinstance(response_id, str) or not response_id:
        raise ProviderFailure("provider_response_id_missing")
    return response_id


def _resolved_model(value: dict[str, Any], field: str) -> str:
    resolved_model = value.get(field)
    if not isinstance(resolved_model, str) or not resolved_model:
        raise ProviderFailure("provider_resolved_model_missing")
    return resolved_model


def validate_model_pin(model: str) -> None:
    """Refuse empty, whitespace-bearing, control-bearing, or `latest` aliases."""

    if not isinstance(model, str) or not model or len(model) > 200:
        raise ValueError("provider_model_pin_invalid")
    if model != model.strip() or any(
        character.isspace() or ord(character) < 33 for character in model
    ):
        raise ValueError("provider_model_pin_invalid")
    if re.search(r"(?:^|[-_/:.])latest(?:$|[-_/:.])", model, re.IGNORECASE):
        raise ValueError("provider_model_alias_refused")


def _require_text(parts: list[str]) -> str:
    text = "".join(parts).strip()
    if not text:
        raise ProviderFailure("provider_output_text_missing")
    if len(text.encode()) > 1_000_000:
        raise ProviderFailure("provider_output_text_too_large")
    return text


def _optional_int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None
