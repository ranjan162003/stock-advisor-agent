import subprocess

from app.agent.providers import opencode_provider
from app.agent.providers.opencode_provider import OpencodeProvider, _extract_text


def test_extract_text_joins_text_events_and_ignores_the_rest():
    stdout = "\n".join(
        [
            '{"type":"step_start","part":{"type":"step-start"}}',
            '{"type":"text","part":{"type":"text","text":"Hello "}}',
            '{"type":"tool","part":{"type":"tool","tool":"read"}}',
            '{"type":"text","part":{"type":"text","text":"world"}}',
        ]
    )
    assert _extract_text(stdout) == "Hello world"


def test_extract_text_ignores_non_json_lines():
    assert _extract_text("opening server...\n{}\n") == ""


def _completed(stdout: str) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=["opencode"], returncode=0, stdout=stdout)


def test_status_is_ready_when_cli_lists_models(monkeypatch):
    monkeypatch.setattr(opencode_provider, "find_cli_executable", lambda _name: "/usr/bin/opencode")
    monkeypatch.setattr(
        opencode_provider, "run_cli_quietly", lambda command, timeout_seconds=10: _completed("llamacpp/q4\nopencode/free\n")
    )

    status = OpencodeProvider().get_status()

    assert status.is_ready
    assert status.available_models == ["llamacpp/q4", "opencode/free"]
    assert status.default_model == "llamacpp/q4"  # blank setting falls back to the first reported model


def test_status_not_ready_without_models(monkeypatch):
    monkeypatch.setattr(opencode_provider, "find_cli_executable", lambda _name: "/usr/bin/opencode")
    monkeypatch.setattr(opencode_provider, "run_cli_quietly", lambda command, timeout_seconds=10: _completed(""))

    assert not OpencodeProvider().get_status().is_ready
