from __future__ import annotations

import inspect

from deepagents_code.agent import _add_interrupt_on, create_cli_agent

from coding_agent.tools.excel_tool import ANALYZE_EXCEL_NAME, TRANSFORM_EXCEL_NAME


def test_create_cli_agent_public_signature_has_tools_not_interrupt_on() -> None:
    params = inspect.signature(create_cli_agent).parameters
    assert "tools" in params
    assert "mcp_tools" in params
    assert "interrupt_on" not in params


def test_custom_analyze_excel_is_not_default_hitl_target() -> None:
    mapping = _add_interrupt_on()
    assert "execute" in mapping
    assert "write_file" in mapping
    assert ANALYZE_EXCEL_NAME not in mapping
    assert TRANSFORM_EXCEL_NAME not in mapping
    assert "analyze_excel" not in mapping
    assert "transform_excel" not in mapping
