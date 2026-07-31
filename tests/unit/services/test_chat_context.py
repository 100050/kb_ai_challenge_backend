from app.services.chat import ChatService


def test_context_changes_contains_only_changed_input_values() -> None:
    previous = {
        "cash_flow": {"after_tax_monthly_income": 3_000_000},
        "housing_plans": [
            {
                "property_id": "property-1",
                "monthly_rent": 700_000,
            },
        ],
    }
    current = {
        "cash_flow": {"after_tax_monthly_income": 3_500_000},
        "housing_plans": [
            {
                "property_id": "property-1",
                "monthly_rent": 700_000,
            },
        ],
    }

    assert ChatService._context_changes(previous, current) == [
        {
            "path": "cash_flow.after_tax_monthly_income",
            "before": 3_000_000,
            "after": 3_500_000,
        },
    ]


def test_context_changes_reports_added_and_removed_housing_plans() -> None:
    previous = {
        "housing_plans": [
            {"property_id": "property-1", "name": "기존 매물"},
        ],
    }
    current = {
        "housing_plans": [
            {"property_id": "property-2", "name": "신규 매물"},
        ],
    }

    changes = ChatService._context_changes(previous, current)

    assert changes == [
        {
            "path": "housing_plans[property-1]",
            "before": {
                "property_id": "property-1",
                "name": "기존 매물",
            },
            "after": None,
        },
        {
            "path": "housing_plans[property-2]",
            "before": None,
            "after": {
                "property_id": "property-2",
                "name": "신규 매물",
            },
        },
    ]
