from scoring import load_json, score_round1, score_round2

SCENARIO = load_json("data/scenario.json")
RUBRICS = load_json("data/scoring_rubrics.json")


def strong_round1_submission():
    selected_questions = [
        "business_outcome",
        "deliverables",
        "success_measures",
        "stakeholders",
        "constraints",
        "must_have_trainable",
        "risks",
    ]
    brief = {
        "business_objective": "Create one unified omnichannel loyalty experience across France and Belgium, improving customer experience, activation and repeat purchase.",
        "role_purpose": "Lead cross-functional delivery of the digital and omnichannel loyalty programme from requirements and planning through pilot and launch.",
        "deliverables": "Establish governance and a project plan, confirm requirements and scope, coordinate vendor workstreams, deliver a ten-store pilot, prepare store training and make a go/no-go launch recommendation.",
        "essential_requirements": "Demonstrated cross-functional project delivery, stakeholder influence, structured planning, risk mitigation, data and KPI literacy, and professional French and English.",
        "desirable_requirements": "Retail, e-commerce, CRM or loyalty exposure is desirable. Multi-site, vendor and international experience would be an advantage.",
        "constraints_conditions": "Permanent Lille-based hybrid role with travel, €52,000–€60,000 plus bonus. Pilot in 16 weeks, launch decision by week 22, working within a €650,000 budget and peak-trading constraints.",
        "success_measures": "On-time and on-budget milestones, store readiness and adoption, low defects, clear risk reporting, customer enrolment, activation and repeat purchase.",
    }
    selected_competencies = [
        "project_planning",
        "stakeholder_management",
        "change_management",
        "customer_orientation",
        "data_decision",
        "risk_management",
    ]
    weights = {
        "project_planning": 20,
        "stakeholder_management": 20,
        "change_management": 15,
        "customer_orientation": 15,
        "data_decision": 15,
        "risk_management": 15,
    }
    indicators = {
        "project_planning": "Creates a milestone plan, identifies dependencies and delivers agreed outputs by deadline.",
        "stakeholder_management": "Builds stakeholder alignment, influences decisions and resolves cross-functional conflict.",
        "change_management": "Coordinates training, measures readiness and builds adoption among store teams.",
        "customer_orientation": "Analyses customer feedback and adapts the journey to create measurable value.",
        "data_decision": "Analyses KPI data, prioritises evidence and communicates a clear recommendation.",
        "risk_management": "Identifies project risks, creates mitigation plans and escalates material issues early.",
    }
    return selected_questions, brief, selected_competencies, weights, indicators


def test_strong_round1_scores_high():
    result = score_round1(*strong_round1_submission(), RUBRICS["round1"])
    assert result["score"] >= 80


def test_weak_round1_scores_lower():
    selected_questions = ["culture_fit", "competitor_only", "school_pedigree"]
    brief = {key: "We want a young digital native from a top school with five years in retail required." for key in RUBRICS["round1"]["hiring_brief"]["fields"]}
    selected_competencies = ["retail_experience", "digital_fluency"]
    weights = {"retail_experience": 80, "digital_fluency": 20}
    indicators = {"retail_experience": "Has retail experience.", "digital_fluency": "Knows digital."}
    result = score_round1(selected_questions, brief, selected_competencies, weights, indicators, RUBRICS["round1"])
    assert result["score"] < 45


def test_strong_round2_scores_high_and_within_budget():
    channels = ["internal_mobility", "apec", "linkedin_sourcing", "specialist_board"]
    advert = """
    Chef de projet marketing digital & omnicanal — Maison Nova
    Maison Nova is a retailer with 62 stores across France and Belgium. Lead a unified loyalty programme that improves the customer journey and repeat purchase. You will coordinate cross-functional stakeholders in marketing, IT, store operations and our vendor; create the project plan, manage milestones, risks and issues, deliver a pilot and support the go/no-go launch decision. Essential criteria are a demonstrated track record in complex project delivery, stakeholder influence, risk management and data-informed decisions. Retail, CRM or loyalty exposure is desirable rather than mandatory. Permanent Lille hybrid role, salary €52,000–€60,000 plus bonus. We welcome all qualified candidates and provide reasonable adjustments. Apply through a transparent two-interview and work-sample process.
    """
    boolean = '("chef de projet" OR "project manager") AND (digital OR omnicanal OR omnichannel) AND (retail OR e-commerce) AND (CRM OR loyalty OR fidélité OR marketing)'
    outreach = """
    Bonjour Camille, your CRM and loyalty delivery for retail clients, especially the multi-country app rollout, looks highly relevant to a role I am supporting at Maison Nova. The company is unifying the loyalty journey across 62 stores and e-commerce in France and Belgium, and the project manager will own the cross-functional business outcome rather than remain in an agency delivery role. It is a permanent Lille-based hybrid position with a €52,000–€60,000 range. Would you be open to a brief 15-minute conversation next week, with no obligation? Kind regards, Alex.
    """
    result = score_round2(channels, SCENARIO["round2"]["channels"], SCENARIO["round2"]["budget"], advert, boolean, outreach, RUBRICS["round2"])
    assert result["channels"]["cost"] <= SCENARIO["round2"]["budget"]
    assert result["score"] >= 80


def test_agency_heavy_strategy_is_penalised():
    channels = ["agency", "social_organic"]
    result = score_round2(channels, SCENARIO["round2"]["channels"], SCENARIO["round2"]["budget"], "short advert", "project manager", "hello", RUBRICS["round2"])
    labels = [item["label"] for item in result["channels"]["penalties"]]
    assert "agency consumes most of budget" in labels
