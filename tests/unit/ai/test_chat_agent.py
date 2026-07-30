from pydantic_ai.models.test import TestModel

from app.ai.agent import create_chat_agent


def test_all_input_update_tools_execute_without_user_approval() -> None:
    agent = create_chat_agent(TestModel())

    tools = agent._function_toolset.tools

    assert set(tools) == {
        "update_cash_flow",
        "update_financial_goals",
        "update_housing_plan",
    }
    assert all(not tool.requires_approval for tool in tools.values())
