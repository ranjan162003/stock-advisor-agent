"""OpenCode as a model gateway — reuse every model the `opencode` CLI is set up with.

OpenCode (https://opencode.ai) already knows about all of your providers/models via
`opencode models` — including a local llama.cpp server — so this provider shells out to
`opencode run` instead of talking to each backend itself.
"""
from __future__ import annotations

import json

from app.agent.providers.base_llm_provider import BaseLlmProvider
from app.agent.providers.cli_process_runner import (
    find_cli_executable,
    open_visible_login_terminal,
    run_cli_quietly,
    run_cli_with_prompt_on_stdin,
)
from app.core.app_exceptions import ProviderCallError, ProviderNotConnectedError
from app.core.app_settings import get_settings
from app.schemas.provider_schemas import AuthMethod, LoginStartResponse, ProviderId, ProviderStatus

STATUS_TIMEOUT_SECONDS = 10


def _extract_text(events_stdout: str) -> str:
    """Concatenate the text parts of `opencode run --format json` NDJSON events."""
    chunks: list[str] = []
    for line in events_stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        part = event.get("part") or {}
        if event.get("type") == "text" and part.get("type") == "text":
            chunks.append(part.get("text", ""))
    return "".join(chunks).strip()


class OpencodeProvider(BaseLlmProvider):
    provider_id = ProviderId.OPENCODE
    display_name = "OpenCode"

    def __init__(self) -> None:
        self._settings = get_settings()

    def _list_models(self, cli_path: str) -> list[str]:
        """Every `provider/model` the CLI knows about, or [] if it couldn't answer."""
        completed = run_cli_quietly([cli_path, "models"], timeout_seconds=STATUS_TIMEOUT_SECONDS)
        if completed is None or completed.returncode != 0:
            return []
        return [line.strip() for line in completed.stdout.splitlines() if line.strip()]

    def get_status(self) -> ProviderStatus:
        cli_path = find_cli_executable("opencode")
        models = self._list_models(cli_path) if cli_path else []
        ready = bool(cli_path) and bool(models)

        if not cli_path:
            message = "OpenCode isn't installed."
        elif not models:
            message = "OpenCode is installed but has no models configured."
        else:
            message = f"OpenCode is ready with {len(models)} model(s)."

        default_model = self._settings.opencode_default_model
        if models and default_model not in models:
            default_model = models[0]

        return ProviderStatus(
            provider_id=self.provider_id,
            display_name=self.display_name,
            description="Runs any model OpenCode is set up with — a local llama.cpp server or free cloud models.",
            supports_cli_login=True,
            supports_api_key=False,
            cli_installed=bool(cli_path),
            # OpenCode is usable as soon as it can list models; auth is per-model, not one account.
            cli_logged_in=ready,
            is_ready=ready,
            active_auth_method=AuthMethod.CLI_LOGIN if ready else None,
            available_models=models,
            default_model=default_model,
            status_message=message,
            setup_hint=None
            if ready
            else "Install OpenCode (https://opencode.ai) and configure a model, then run `opencode models` to confirm.",
        )

    def start_browser_login(self) -> LoginStartResponse:
        cli_path = find_cli_executable("opencode")
        if not cli_path:
            return LoginStartResponse(
                started=False,
                message="OpenCode isn't installed. Install it from https://opencode.ai, then click 'Check status'.",
            )
        if open_visible_login_terminal([cli_path, "auth", "login"], "OpenCode login"):
            return LoginStartResponse(
                started=True,
                message="A terminal window opened — connect a provider there, then click 'Check status'.",
            )
        return LoginStartResponse(
            started=False, message="Run `opencode auth login` in a terminal, then click 'Check status'."
        )

    def generate_text(self, prompt: str, model_name: str | None = None, json_schema: dict | None = None) -> str:
        cli_path = find_cli_executable("opencode")
        if not cli_path:
            raise ProviderNotConnectedError("OpenCode isn't installed — install it from https://opencode.ai.")
        model = model_name or self.get_status().default_model
        command = [cli_path, "run", "--model", model, "--format", "json"]
        output = run_cli_with_prompt_on_stdin(
            command, prompt, self._settings.opencode_timeout_seconds, self.display_name
        )
        text = _extract_text(output)
        if not text:
            raise ProviderCallError(
                f"OpenCode returned no text for model '{model}' — check that it's configured and authenticated."
            )
        return text
