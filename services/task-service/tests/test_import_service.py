from __future__ import annotations

import pytest

from py_common.core.errors import AppError

from app.services.import_service import parse_csv


def _csv_bytes(text: str) -> bytes:
    return text.encode("utf-8")


def test_missing_required_column_fails_whole_import():
    content = _csv_bytes("TaskName,Description\nDo thing,Some desc\n")
    with pytest.raises(AppError) as excinfo:
        parse_csv(content)
    assert excinfo.value.status_code == 400
    assert "TaskCode" in excinfo.value.message


def test_missing_task_name_column_fails_whole_import():
    content = _csv_bytes("TaskCode,Description\nABC123,Some desc\n")
    with pytest.raises(AppError):
        parse_csv(content)


def test_row_missing_task_code_value_is_skipped_others_import():
    content = _csv_bytes(
        "TaskCode,TaskName,Status\n"
        ",Missing code,Open\n"
        "GOOD1,Valid row,Open\n"
    )
    result = parse_csv(content)
    assert len(result.rows) == 1
    assert result.rows[0].task_code == "GOOD1"
    assert len(result.errors) == 1
    assert result.errors[0].row == 2
    assert "TaskCode" in result.errors[0].reason


def test_duplicate_task_code_in_file_is_skipped():
    content = _csv_bytes(
        "TaskCode,TaskName\n"
        "DUP1,First\n"
        "DUP1,Second\n"
    )
    result = parse_csv(content)
    assert len(result.rows) == 1
    assert result.rows[0].task_name == "First"
    assert len(result.errors) == 1
    assert "Duplicate" in result.errors[0].reason
    assert result.errors[0].row == 3


def test_invalid_status_is_skipped():
    content = _csv_bytes(
        "TaskCode,TaskName,Status\n"
        "BADS,Bad status,Weird\n"
        "OK1,Fine,Open\n"
    )
    result = parse_csv(content)
    assert len(result.rows) == 1
    assert result.rows[0].task_code == "OK1"
    assert len(result.errors) == 1
    assert "Status" in result.errors[0].reason


def test_defaults_applied_for_optional_and_missing_fields():
    content = _csv_bytes("TaskCode,TaskName\nDEF1,Defaults row\n")
    result = parse_csv(content)
    assert len(result.rows) == 1
    row = result.rows[0]
    assert row.status == "Open"
    assert row.description is None
    assert row.sponsor is None
    assert row.cost_centre is None
    assert row.coe_responsible is None


def test_unknown_extra_columns_are_ignored():
    content = _csv_bytes(
        "TaskCode,TaskName,SomeExtraColumn\n"
        "EX1,Has extra,ignored-value\n"
    )
    result = parse_csv(content)
    assert len(result.rows) == 1
    assert result.errors == []


def test_header_matching_is_case_insensitive():
    content = _csv_bytes("taskcode,taskname,sponsor\nCI1,Case insensitive,Jane Sponsor\n")
    result = parse_csv(content)
    assert len(result.rows) == 1
    assert result.rows[0].sponsor == "Jane Sponsor"


def test_new_columns_are_parsed():
    content = _csv_bytes(
        "TaskCode,TaskName,Description,Sponsor,CostCentre,CoEResponsible,Status\n"
        "NEW1,New task,Some description,Jane Sponsor,CC001,CoE Team,OnHold\n"
    )
    result = parse_csv(content)
    assert len(result.rows) == 1
    row = result.rows[0]
    assert row.description == "Some description"
    assert row.sponsor == "Jane Sponsor"
    assert row.cost_centre == "CC001"
    assert row.coe_responsible == "CoE Team"
    assert row.status == "OnHold"


def test_blank_lines_are_skipped_silently():
    content = _csv_bytes("TaskCode,TaskName\nOK1,Fine\n\n,\nOK2,Also fine\n")
    result = parse_csv(content)
    codes = {r.task_code for r in result.rows}
    assert codes == {"OK1", "OK2"}
