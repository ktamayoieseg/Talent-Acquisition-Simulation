"""Deterministic scoring engine for the Talent Acquisition Lab MVP."""

from __future__ import annotations

import json
import math
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

BASE_DIR = Path(__file__).resolve().parent


def load_json(relative_path: str) -> Dict[str, Any]:
    with (BASE_DIR / relative_path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def normalise(value: Any) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.lower().replace("’", "'").replace("–", "-")
    return re.sub(r"\s+", " ", text).strip()


def _contains(text: str, phrase: str) -> bool:
    return normalise(phrase) in text


def _concept_met(text: str, concept: Mapping[str, Any]) -> bool:
    if "absence_of" in concept:
        return not any(_contains(text, phrase) for phrase in concept["absence_of"])

    if "word_count_range" in concept:
        minimum, maximum = concept["word_count_range"]
        count = len(re.findall(r"\b\w+[\w'-]*\b", text))
        return minimum <= count <= maximum

    if "all_groups" in concept:
        for group in concept["all_groups"]:
            if not any(_contains(text, phrase) for phrase in group):
                return False
        return True

    if "all_of" in concept:
        return all(_contains(text, phrase) for phrase in concept["all_of"])

    return any(_contains(text, phrase) for phrase in concept.get("any_of", []))


def score_text(text: str, rubric: Mapping[str, Any]) -> Dict[str, Any]:
    clean = normalise(text)
    earned = 0.0
    hits: List[str] = []
    misses: List[str] = []
    penalties: List[Dict[str, Any]] = []

    for concept in rubric.get("concepts", []):
        if _concept_met(clean, concept):
            earned += float(concept["points"])
            hits.append(concept["label"])
        else:
            misses.append(concept["label"])

    for penalty in rubric.get("penalties", []):
        triggered = False
        if "patterns" in penalty:
            triggered = any(_contains(clean, pattern) for pattern in penalty["patterns"])
        if "max_and_count" in penalty:
            triggered = len(re.findall(r"\band\b", clean)) > int(penalty["max_and_count"])
        if triggered:
            earned += float(penalty["points"])
            penalties.append({"label": penalty["label"], "points": penalty["points"]})

    maximum = float(rubric["max_points"])
    earned = max(0.0, min(maximum, earned))
    return {
        "score": round(earned, 1),
        "max": maximum,
        "hits": hits,
        "misses": misses,
        "penalties": penalties,
    }


def score_intake(selected_question_ids: Sequence[str], rubric: Mapping[str, Any]) -> Dict[str, Any]:
    points_map = rubric["question_points"]
    raw = sum(float(points_map.get(question_id, 0)) for question_id in selected_question_ids)
    score = min(float(rubric["max_points"]), raw)
    high_value = sum(1 for question_id in selected_question_ids if points_map.get(question_id, 0) >= 3)
    low_value = sum(1 for question_id in selected_question_ids if points_map.get(question_id, 0) == 0)
    feedback = []
    if high_value >= 5:
        feedback.append("The intake focused strongly on outcomes, deliverables and evidence requirements.")
    else:
        feedback.append("Ask more questions about outcomes, deliverables, success measures, constraints and essential capabilities.")
    if low_value:
        feedback.append("Some question capacity was used on preference or pedigree topics that do not improve job analysis.")
    return {
        "score": round(score, 1),
        "max": float(rubric["max_points"]),
        "high_value_count": high_value,
        "low_value_count": low_value,
        "feedback": feedback,
    }


def score_hiring_brief(fields: Mapping[str, str], rubric: Mapping[str, Any]) -> Dict[str, Any]:
    breakdown: Dict[str, Any] = {}
    total = 0.0
    all_text = "\n".join(str(value) for value in fields.values())

    for field_name, field_rubric in rubric["fields"].items():
        result = score_text(fields.get(field_name, ""), field_rubric)
        breakdown[field_name] = result
        total += result["score"]

    global_penalties = []
    clean = normalise(all_text)
    for penalty in rubric.get("penalties", []):
        if any(_contains(clean, pattern) for pattern in penalty.get("patterns", [])):
            total += float(penalty["points"])
            global_penalties.append({"label": penalty["label"], "points": penalty["points"]})

    total = max(0.0, min(float(rubric["max_points"]), total))
    return {
        "score": round(total, 1),
        "max": float(rubric["max_points"]),
        "breakdown": breakdown,
        "penalties": global_penalties,
    }


def score_competency_scorecard(
    selected_ids: Sequence[str],
    weights: Mapping[str, float],
    indicators: Mapping[str, str],
    rubric: Mapping[str, Any],
) -> Dict[str, Any]:
    comp_rules = rubric["competencies"]

    selection_raw = sum(float(comp_rules.get(comp_id, {}).get("selection_points", 0)) for comp_id in selected_ids)
    selection_score = min(float(rubric["selection_max"]), selection_raw)

    weight_total = sum(float(weights.get(comp_id, 0)) for comp_id in selected_ids)
    weight_score = 0.0
    weight_feedback = []
    per_comp_weight = float(rubric["weight_max"]) / max(1, len(selected_ids))
    for comp_id in selected_ids:
        value = float(weights.get(comp_id, 0))
        low, high = comp_rules.get(comp_id, {}).get("target_weight", [0, 100])
        if low <= value <= high:
            weight_score += per_comp_weight
        elif (low - 5) <= value <= (high + 5):
            weight_score += per_comp_weight * 0.5
            weight_feedback.append(f"{comp_id}: weighting is close to, but outside, the suggested range.")
        else:
            weight_feedback.append(f"{comp_id}: weighting is not well aligned with the role evidence.")
    if not math.isclose(weight_total, 100.0, abs_tol=0.01):
        weight_score *= 0.5
        weight_feedback.append("Competency weights should total 100%.")
    weight_score = min(float(rubric["weight_max"]), weight_score)

    indicator_score = 0.0
    indicator_feedback = []
    per_comp_indicator = float(rubric["indicator_max"]) / max(1, len(selected_ids))
    observable_verbs = [normalise(word) for word in rubric.get("observable_verbs", [])]
    for comp_id in selected_ids:
        text = normalise(indicators.get(comp_id, ""))
        specific_terms = [normalise(term) for term in comp_rules.get(comp_id, {}).get("indicator_terms", [])]
        enough_detail = len(text.split()) >= 6
        has_specific = any(term in text for term in specific_terms)
        has_observable = any(verb in text for verb in observable_verbs)
        if enough_detail and has_specific and has_observable:
            indicator_score += per_comp_indicator
        elif enough_detail and (has_specific or has_observable):
            indicator_score += per_comp_indicator * 0.5
            indicator_feedback.append(f"{comp_id}: make the indicator more observable and role-specific.")
        else:
            indicator_feedback.append(f"{comp_id}: add a behavioural indicator describing visible action and outcome.")
    indicator_score = min(float(rubric["indicator_max"]), indicator_score)

    total = selection_score + weight_score + indicator_score
    return {
        "score": round(min(float(rubric["max_points"]), total), 1),
        "max": float(rubric["max_points"]),
        "selection_score": round(selection_score, 1),
        "selection_max": float(rubric["selection_max"]),
        "weight_score": round(weight_score, 1),
        "weight_max": float(rubric["weight_max"]),
        "indicator_score": round(indicator_score, 1),
        "indicator_max": float(rubric["indicator_max"]),
        "weight_total": round(weight_total, 1),
        "weight_feedback": weight_feedback,
        "indicator_feedback": indicator_feedback,
    }


def score_round1(
    selected_questions: Sequence[str],
    brief_fields: Mapping[str, str],
    selected_competencies: Sequence[str],
    weights: Mapping[str, float],
    indicators: Mapping[str, str],
    rubrics: Mapping[str, Any],
) -> Dict[str, Any]:
    intake = score_intake(selected_questions, rubrics["intake"])
    brief = score_hiring_brief(brief_fields, rubrics["hiring_brief"])
    scorecard = score_competency_scorecard(selected_competencies, weights, indicators, rubrics["competency_scorecard"])
    total = intake["score"] + brief["score"] + scorecard["score"]
    return {
        "score": round(total, 1),
        "max": 100.0,
        "intake": intake,
        "brief": brief,
        "scorecard": scorecard,
    }


def score_channels(
    selected_channel_ids: Sequence[str],
    channel_catalogue: Sequence[Mapping[str, Any]],
    budget: float,
    rubric: Mapping[str, Any],
) -> Dict[str, Any]:
    channel_lookup = {channel["id"]: channel for channel in channel_catalogue}
    selected = [channel_lookup[channel_id] for channel_id in selected_channel_ids if channel_id in channel_lookup]
    total_cost = sum(float(channel["cost"]) for channel in selected)

    base = sum(float(rubric["selection_points"].get(channel["id"], 0)) for channel in selected)
    base = min(float(rubric["base_max"]), base)

    tags = set(tag for channel in selected for tag in channel.get("tags", []))
    coverage = 0.0
    coverage_hits = []
    coverage_misses = []
    for bonus in rubric.get("coverage_bonuses", []):
        met = False
        if "requires_tags" in bonus:
            met = all(tag in tags for tag in bonus["requires_tags"])
        if "minimum_channels" in bonus:
            met = len(selected) >= int(bonus["minimum_channels"])
        if met:
            coverage += float(bonus["points"])
            coverage_hits.append(bonus["label"])
        else:
            coverage_misses.append(bonus["label"])

    efficiency_rules = rubric["efficiency"]
    if total_cost <= budget * float(efficiency_rules["full_score_budget_ratio"]):
        efficiency = float(efficiency_rules["max_points"])
    elif total_cost <= budget:
        efficiency = float(efficiency_rules["within_budget_points"])
    else:
        efficiency = 0.0

    penalties = []
    penalty_total = 0.0
    for penalty in rubric.get("penalties", []):
        if "above_channels" in penalty and len(selected) > int(penalty["above_channels"]):
            extra = len(selected) - int(penalty["above_channels"])
            points = extra * float(penalty["points_per_extra"])
            penalty_total += points
            penalties.append({"label": penalty["label"], "points": points})
        if "channel" in penalty and penalty["channel"] in selected_channel_ids and budget > 0:
            channel_cost = float(channel_lookup[penalty["channel"]]["cost"])
            if channel_cost / budget >= float(penalty["minimum_budget_share"]):
                points = float(penalty["points"])
                penalty_total += points
                penalties.append({"label": penalty["label"], "points": points})

    total = base + coverage + efficiency + penalty_total
    if total_cost > budget:
        total = min(total, 15.0)
    total = max(0.0, min(float(rubric["max_points"]), total))
    return {
        "score": round(total, 1),
        "max": float(rubric["max_points"]),
        "base_score": round(base, 1),
        "coverage_score": round(coverage, 1),
        "efficiency_score": round(efficiency, 1),
        "cost": total_cost,
        "budget": budget,
        "coverage_hits": coverage_hits,
        "coverage_misses": coverage_misses,
        "penalties": penalties,
    }


def score_round2(
    selected_channels: Sequence[str],
    channel_catalogue: Sequence[Mapping[str, Any]],
    budget: float,
    job_advert: str,
    boolean_string: str,
    outreach_message: str,
    rubrics: Mapping[str, Any],
) -> Dict[str, Any]:
    channels = score_channels(selected_channels, channel_catalogue, budget, rubrics["channels"])
    advert = score_text(job_advert, rubrics["job_advert"])
    boolean = score_text(boolean_string, rubrics["boolean_string"])
    outreach = score_text(outreach_message, rubrics["outreach_message"])
    total = channels["score"] + advert["score"] + boolean["score"] + outreach["score"]
    return {
        "score": round(total, 1),
        "max": 100.0,
        "channels": channels,
        "advert": advert,
        "boolean": boolean,
        "outreach": outreach,
    }


def performance_band(score: float) -> str:
    if score >= 85:
        return "Excellent evidence-based TA design"
    if score >= 70:
        return "Strong, with targeted improvements needed"
    if score >= 55:
        return "Developing: several sound choices, but important gaps"
    return "Needs revision before progressing to candidate selection"
