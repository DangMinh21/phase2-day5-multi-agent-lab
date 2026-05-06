import json

from typer.testing import CliRunner

from multi_agent_research_lab.cli import app


def test_multi_agent_cli_json_output(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "multi-agent",
            "--query",
            "Explain LangGraph tracing for multi-agent systems",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["final_answer"]
    assert payload["next_route"] == "done"
    assert payload["metrics"]["trace_path"].startswith("reports/traces/")
    assert (tmp_path / payload["metrics"]["trace_path"]).exists()


def test_multi_agent_cli_rejects_unknown_format() -> None:
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "multi-agent",
            "--query",
            "Explain LangGraph tracing",
            "--format",
            "xml",
        ],
    )

    assert result.exit_code != 0
    assert "format must be one of" in result.output
