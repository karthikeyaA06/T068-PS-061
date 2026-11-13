import pytest

from run_commands import main


def test_command_runner_refuses_same_input_and_output_path(tmp_path, monkeypatch):
    command_file = tmp_path / "commands.jsonl"
    command_file.write_text('{"command":"noop"}\n', encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        ["run_commands.py", str(command_file), "--output", str(command_file)],
    )
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2
    assert command_file.read_text(encoding="utf-8") == '{"command":"noop"}\n'
