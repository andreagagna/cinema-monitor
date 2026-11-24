import subprocess
import sys


def test_cli_exits_nonzero_for_invalid_date(tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "src.main"],
        env={
            "DATE": "not-a-date",
            "LOG_FILE": str(tmp_path / "monitor.log"),
            "PYTHON_DOTENV_DISABLED": "1",
        },
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )

    assert result.returncode == 1
    assert "not-a-date" in result.stderr
    assert "does not match format" in result.stderr
