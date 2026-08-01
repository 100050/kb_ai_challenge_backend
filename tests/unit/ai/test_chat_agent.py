from pydantic_ai.models.test import TestModel

from app.ai.agent import AGENT_INSTRUCTIONS, create_chat_agent


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


def test_agent_maps_candidate_equivalent_rent_words_to_saved_metric() -> None:
    assert "내 집의 환산 월세" in AGENT_INSTRUCTIONS
    assert "equivalent_monthly_cost" in AGENT_INSTRUCTIONS
    assert "candidate_equivalent_monthly_cost" in AGENT_INSTRUCTIONS
