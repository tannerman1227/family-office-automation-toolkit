"""Standard investment screen.

Scores are inputs prepared by an analyst. This module applies a published
rubric, concentration and leverage flags, and a recommendation band.
It does not pull data from a manager and it is not an investment recommendation
to transact.
"""

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import pandas as pd

from fotoolkit.config import (
    ADVANCE_MIN,
    CONCENTRATION_LIMIT,
    HIGH_IRR,
    MAX_LTV,
    MIN_TRACK_YEARS,
    SCORE_WEIGHTS,
    WATCH_MIN,
    WEAK_DOWNSIDE,
)
from fotoolkit.readers import money_float, parse_decimal, parse_int, read_table, require_columns


WEIGHTS = {name: Decimal(value) for name, value in SCORE_WEIGHTS.items()}
ADVANCE = Decimal(ADVANCE_MIN)
WATCH = Decimal(WATCH_MIN)
CONCENTRATION = Decimal(CONCENTRATION_LIMIT)
MAX_LEVERAGE = Decimal(MAX_LTV)
HIGH_RETURN = Decimal(HIGH_IRR)


def weighted_score(scores: dict[str, int]) -> Decimal:
    for name, score in scores.items():
        if score < 1 or score > 5:
            raise ValueError(f"{name} must be an integer from 1 to 5, got {score}")
    total = Decimal("0")
    for name, weight in WEIGHTS.items():
        total += Decimal(scores[name]) * weight
    return total


def build_flags(row: dict, total_commitment: Decimal) -> list[dict]:
    flags = []
    if row["track_record_years"] < MIN_TRACK_YEARS:
        flags.append(
            {
                "severity": "hard",
                "text": "Limited sponsor track record (under 3 years).",
            }
        )
    if row["leverage_ltv"] > MAX_LEVERAGE:
        flags.append({"severity": "hard", "text": "Leverage above 65% LTV."})
    if row["target_irr"] > HIGH_RETURN and row["downside_score"] <= WEAK_DOWNSIDE:
        flags.append(
            {
                "severity": "hard",
                "text": "Target IRR above 25% with a downside score of 2 or lower.",
            }
        )
    if total_commitment > 0:
        exposure = row["sleeve_exposure"] + row["ask_amount"]
        if exposure / total_commitment > CONCENTRATION:
            flags.append(
                {
                    "severity": "soft",
                    "text": "Sleeve exposure plus this ask exceeds 35% of total commitments.",
                }
            )
    for part in row["explicit_flags"]:
        flags.append({"severity": "hard", "text": part})
    return flags


def recommend(score: Decimal, flags: list[dict]) -> str:
    hard = any(flag["severity"] == "hard" for flag in flags)
    soft = any(flag["severity"] == "soft" for flag in flags)
    if hard or score < WATCH:
        return "Pass"
    if score >= ADVANCE and not soft:
        return "Advance"
    if score >= WATCH:
        return "Watch"
    return "Pass"


def diligence_questions(flags: list[dict]) -> list[str]:
    questions = [
        "Confirm the fee load, the key-person clause, and the reporting package.",
        "Ask what would make the sponsor return capital early.",
    ]
    texts = " ".join(flag["text"] for flag in flags)
    if "track record" in texts:
        questions.append("Request the audited track record and two reference calls.")
    if "Leverage" in texts:
        questions.append("Ask for the covenant summary and a downside case.")
    if "35%" in texts:
        questions.append("Map the overlap with the current sleeve before discussing size.")
    if "25%" in texts:
        questions.append("Reconcile the target return with the downside case in writing.")
    if "Key-person" in texts:
        questions.append("Identify who runs the investment if that partner leaves.")
    return questions


@dataclass
class ScreeningModel:
    opportunities: pd.DataFrame
    weights: dict
    total_commitment: float
    counts: dict


def load_screening(data_dir: Path, total_commitment: float) -> ScreeningModel:
    rows = read_table(data_dir / "opportunities.csv")
    require_columns(
        rows,
        [
            "opp_id",
            "name",
            "sponsor",
            "asset_class",
            "geography",
            "stage",
            "ask_amount",
            "target_irr",
            "target_moic",
            "hold_years",
            "sponsor_score",
            "market_score",
            "economics_score",
            "structure_score",
            "downside_score",
            "fit_score",
            "sleeve_exposure",
            "track_record_years",
            "leverage_ltv",
            "explicit_flags",
            "thesis",
        ],
        "opportunities.csv",
    )
    commitment = Decimal(str(total_commitment))
    built = []
    for row in rows:
        scores = {name: parse_int(row[name]) for name in WEIGHTS}
        if any(score is None for score in scores.values()):
            raise ValueError(f"{row['opp_id']} has a score that is not a whole number")
        prepared = {
            "track_record_years": parse_int(row["track_record_years"]),
            "leverage_ltv": parse_decimal(row["leverage_ltv"]),
            "target_irr": parse_decimal(row["target_irr"]),
            "downside_score": scores["downside_score"],
            "sleeve_exposure": parse_decimal(row["sleeve_exposure"]),
            "ask_amount": parse_decimal(row["ask_amount"]),
            "explicit_flags": [part.strip() for part in row["explicit_flags"].split("|") if part.strip()],
        }
        score = weighted_score(scores)
        flags = build_flags(prepared, commitment)
        band = recommend(score, flags)
        exposure = prepared["sleeve_exposure"] + prepared["ask_amount"]
        built.append(
            {
                "opp_id": row["opp_id"],
                "name": row["name"],
                "sponsor": row["sponsor"],
                "asset_class": row["asset_class"],
                "geography": row["geography"],
                "stage": row["stage"],
                "ask_amount": money_float(prepared["ask_amount"]),
                "target_irr": float(prepared["target_irr"]),
                "target_moic": float(parse_decimal(row["target_moic"])),
                "hold_years": parse_int(row["hold_years"]),
                "sponsor_score": scores["sponsor_score"],
                "market_score": scores["market_score"],
                "economics_score": scores["economics_score"],
                "structure_score": scores["structure_score"],
                "downside_score": scores["downside_score"],
                "fit_score": scores["fit_score"],
                "sleeve_exposure": money_float(prepared["sleeve_exposure"]),
                "pro_forma_exposure": money_float(exposure),
                "exposure_share": float(exposure / commitment) if commitment else None,
                "track_record_years": prepared["track_record_years"],
                "leverage_ltv": float(prepared["leverage_ltv"]),
                "weighted_score": float(score),
                "recommendation": band,
                "hard_flag_count": sum(flag["severity"] == "hard" for flag in flags),
                "red_flags": [flag["text"] for flag in flags],
                "questions": diligence_questions(flags),
                "thesis": row["thesis"],
            }
        )
    frame = pd.DataFrame(built).sort_values(["weighted_score", "opp_id"], ascending=[False, True])
    frame = frame.reset_index(drop=True)
    counts = {
        "opportunities": int(len(frame)),
        "advance": int((frame["recommendation"] == "Advance").sum()),
        "watch": int((frame["recommendation"] == "Watch").sum()),
        "pass": int((frame["recommendation"] == "Pass").sum()),
        "ask_amount": money_float(sum((Decimal(str(value)) for value in frame["ask_amount"]), Decimal("0"))),
    }
    return ScreeningModel(
        opportunities=frame,
        weights={name: float(weight) for name, weight in WEIGHTS.items()},
        total_commitment=float(commitment),
        counts=counts,
    )
