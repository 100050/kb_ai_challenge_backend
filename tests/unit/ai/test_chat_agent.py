from pydantic_ai.models.test import TestModel

from app.ai.agent import AGENT_INSTRUCTIONS, PROMPT_PATH, create_chat_agent


def test_all_input_update_tools_execute_without_user_approval() -> None:
    agent = create_chat_agent(TestModel())

    tools = agent._function_toolset.tools

    assert set(tools) == {
        "get_calculation_formula",
        "get_calculation_breakdown",
        "update_cash_flow",
        "update_financial_goals",
        "update_housing_plan",
    }
    assert all(not tool.requires_approval for tool in tools.values())


def test_agent_uses_external_prompt_file() -> None:
    assert AGENT_INSTRUCTIONS == PROMPT_PATH.read_text(
        encoding="utf-8",
    ).strip()
    assert "<role>" in AGENT_INSTRUCTIONS
    assert "<data_rules>" in AGENT_INSTRUCTIONS
    assert "Respond in Korean." in AGENT_INSTRUCTIONS
