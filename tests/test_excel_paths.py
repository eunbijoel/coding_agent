from __future__ import annotations

from pathlib import Path

import pytest

from coding_agent.integrations.excel_errors import (
    TRANSPORT_INVALID_TOOL_INPUT,
    TRANSPORT_WORKSPACE_VIOLATION,
)
from coding_agent.integrations.excel_paths import (
    PathValidationError,
    ValidatedInput,
    ensure_unique_inputs,
    validate_tool_inputs,
)
from tests.conftest import write_bytes


def _ok(workspace: Path, files: list[str], **kwargs):
    return validate_tool_inputs(
        workspace=workspace,
        files=files,
        prompt=kwargs.get("prompt", "이 파일의 주요 내용을 요약해줘"),
        analysis_mode=kwargs.get("analysis_mode", "single"),
        profile_name=kwargs.get("profile_name", "generic"),
        sheets=kwargs.get("sheets"),
    )


def test_valid_relative_xlsx(workspace: Path) -> None:
    write_bytes(workspace / "data.xlsx")
    inputs, mode, profile = _ok(workspace, ["data.xlsx"])
    assert mode == "single"
    assert profile == "generic"
    assert inputs[0].workspace_relative == "data.xlsx"
    assert inputs[0].path == (workspace / "data.xlsx").resolve()


def test_valid_workspace_absolute_path(workspace: Path) -> None:
    path = write_bytes(workspace / "abs.xlsx")
    inputs, _, _ = _ok(workspace, [str(path.resolve())])
    assert inputs[0].path == path.resolve()


def test_valid_csv(workspace: Path) -> None:
    write_bytes(workspace / "table.csv", b"a,b\n1,2\n")
    inputs, _, _ = _ok(workspace, ["table.csv"])
    assert inputs[0].path.suffix == ".csv"


def test_missing_file(workspace: Path) -> None:
    with pytest.raises(PathValidationError) as exc:
        _ok(workspace, ["missing.xlsx"])
    assert exc.value.error_code == TRANSPORT_INVALID_TOOL_INPUT
    assert "does not exist" in exc.value.message


def test_unsupported_extension(workspace: Path) -> None:
    write_bytes(workspace / "notes.txt", b"nope")
    with pytest.raises(PathValidationError) as exc:
        _ok(workspace, ["notes.txt"])
    assert exc.value.error_code == TRANSPORT_INVALID_TOOL_INPUT
    assert "Unsupported file extension" in exc.value.message


def test_blank_path(workspace: Path) -> None:
    with pytest.raises(PathValidationError) as exc:
        _ok(workspace, ["  "])
    assert exc.value.error_code == TRANSPORT_INVALID_TOOL_INPUT
    assert "blank" in exc.value.message


def test_workspace_escape(workspace: Path, tmp_path: Path) -> None:
    outsider = write_bytes(tmp_path / "outside.xlsx")
    with pytest.raises(PathValidationError) as exc:
        _ok(workspace, [str(outsider)])
    assert exc.value.error_code == TRANSPORT_WORKSPACE_VIOLATION


def test_dotdot_traversal(workspace: Path, tmp_path: Path) -> None:
    write_bytes(tmp_path / "secret.xlsx")
    with pytest.raises(PathValidationError) as exc:
        _ok(workspace, ["../secret.xlsx"])
    assert exc.value.error_code == TRANSPORT_WORKSPACE_VIOLATION


def test_input_symlink_escape(workspace: Path, tmp_path: Path) -> None:
    target = write_bytes(tmp_path / "secret.xlsx")
    link = workspace / "alias.xlsx"
    link.symlink_to(target)
    with pytest.raises(PathValidationError) as exc:
        _ok(workspace, ["alias.xlsx"])
    assert exc.value.error_code == TRANSPORT_WORKSPACE_VIOLATION


def test_duplicate_path(workspace: Path) -> None:
    write_bytes(workspace / "dup.xlsx")
    with pytest.raises(PathValidationError) as exc:
        _ok(
            workspace,
            ["dup.xlsx", str((workspace / "dup.xlsx").resolve())],
            analysis_mode="multi",
        )
    assert "Duplicate input path" in exc.value.message


def test_duplicate_source_id(workspace: Path) -> None:
    a = ValidatedInput(
        source_id="file-1",
        path=workspace / "a.xlsx",
        display_name="a.xlsx",
        sheet=0,
        workspace_relative="a.xlsx",
    )
    b = ValidatedInput(
        source_id="file-1",
        path=workspace / "b.xlsx",
        display_name="b.xlsx",
        sheet=0,
        workspace_relative="b.xlsx",
    )
    with pytest.raises(PathValidationError) as exc:
        ensure_unique_inputs([a, b])
    assert "Duplicate source id" in exc.value.message


def test_single_mode_multiple_files(workspace: Path) -> None:
    write_bytes(workspace / "a.xlsx")
    write_bytes(workspace / "b.xlsx")
    with pytest.raises(PathValidationError) as exc:
        _ok(workspace, ["a.xlsx", "b.xlsx"], analysis_mode="single")
    assert "exactly one file" in exc.value.message


def test_multi_mode_fewer_than_two_files(workspace: Path) -> None:
    write_bytes(workspace / "a.xlsx")
    with pytest.raises(PathValidationError) as exc:
        _ok(workspace, ["a.xlsx"], analysis_mode="multi")
    assert "at least two files" in exc.value.message


def test_invalid_analysis_mode(workspace: Path) -> None:
    write_bytes(workspace / "a.xlsx")
    with pytest.raises(PathValidationError) as exc:
        _ok(workspace, ["a.xlsx"], analysis_mode="merge")
    assert "analysis_mode" in exc.value.message


def test_sheets_length_mismatch(workspace: Path) -> None:
    write_bytes(workspace / "a.xlsx")
    write_bytes(workspace / "b.xlsx")
    with pytest.raises(PathValidationError) as exc:
        _ok(
            workspace,
            ["a.xlsx", "b.xlsx"],
            analysis_mode="multi",
            sheets=["Sheet1"],
        )
    assert "sheets length" in exc.value.message


def test_invalid_sheet_type(workspace: Path) -> None:
    write_bytes(workspace / "a.xlsx")
    with pytest.raises(PathValidationError) as exc:
        _ok(workspace, ["a.xlsx"], sheets=[True])
    assert "sheets[0]" in exc.value.message
