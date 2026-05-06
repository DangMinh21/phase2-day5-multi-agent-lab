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


def test_benchmark_cli_writes_report(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.chdir(tmp_path)
    config_path = tmp_path / "benchmark.yaml"
    config_path.write_text(
        "benchmark:\n"
        "  queries:\n"
        "    - Explain LangGraph tracing\n",
        encoding="utf-8",
    )
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "benchmark",
            "--config",
            str(config_path),
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["report_path"] == "reports/benchmark_report.md"
    assert (tmp_path / payload["report_path"]).exists()
    assert len(payload["metrics"]) == 2
