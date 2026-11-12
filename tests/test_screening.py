from decimal import Decimal

from fotoolkit.config import DATA_DIR
from fotoolkit.screening import WEIGHTS, build_flags, recommend, weighted_score, load_screening


def test_weights_sum_to_one():
    assert sum(WEIGHTS.values()) == Decimal("1.00")


def test_sample_bands_follow_the_published_rule():
    model = load_screening(DATA_DIR, 22_000_000)
    bands = dict(zip(model.opportunities["opp_id"], model.opportunities["recommendation"]))
    scores = dict(zip(model.opportunities["opp_id"], model.opportunities["weighted_score"]))
    assert bands == {
        "ATC-01": "Advance",
        "HID-01": "Advance",
        "SAB-01": "Watch",
        "NUE-01": "Watch",
        "CAD-01": "Pass",
    }
    assert round(scores["HID-01"], 2) == 4.35
    assert round(scores["ATC-01"], 2) == 4.45
    assert round(scores["SAB-01"], 2) == 3.70
    assert round(scores["NUE-01"], 2) == 3.50
    assert round(scores["CAD-01"], 2) == 3.10
    flags = dict(zip(model.opportunities["opp_id"], model.opportunities["red_flags"]))
    assert "Limited sponsor track record (under 3 years)." in flags["CAD-01"]
    assert "Leverage above 65% LTV." in flags["CAD-01"]
    assert "Sleeve exposure plus this ask exceeds 35% of total commitments." in flags["NUE-01"]
    assert flags["HID-01"] == []
    assert flags["ATC-01"] == []
    assert model.counts == {
        "opportunities": 5,
        "advance": 2,
        "watch": 2,
        "pass": 1,
        "ask_amount": 9_500_000,
    }


def test_hard_flag_blocks_a_high_score():
    score = weighted_score(
        {
            "sponsor_score": 5,
            "market_score": 5,
            "economics_score": 5,
            "structure_score": 5,
            "downside_score": 5,
            "fit_score": 5,
        }
    )
    flags = build_flags(
        {
            "track_record_years": 1,
            "leverage_ltv": Decimal("0.20"),
            "target_irr": Decimal("0.12"),
            "downside_score": 5,
            "sleeve_exposure": Decimal("0"),
            "ask_amount": Decimal("1000"),
            "explicit_flags": [],
        },
        Decimal("22000000"),
    )
    assert recommend(score, flags) == "Pass"


def test_score_out_of_range_is_rejected():
    try:
        weighted_score(
            {
                "sponsor_score": 6,
                "market_score": 5,
                "economics_score": 5,
                "structure_score": 5,
                "downside_score": 5,
                "fit_score": 5,
            }
        )
    except ValueError as exc:
        assert "1 to 5" in str(exc)
    else:
        raise AssertionError("expected ValueError")
