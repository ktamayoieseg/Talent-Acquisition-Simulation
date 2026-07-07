from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import streamlit as st

from ai_adapter import generate_manager_response
from scoring import load_json, performance_band, score_round1, score_round2

BASE_DIR = Path(__file__).resolve().parent
SCENARIO = load_json("data/scenario.json")
RUBRICS = load_json("data/scoring_rubrics.json")

st.set_page_config(
    page_title="Talent Acquisition Lab",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .main .block-container {max-width: 1180px; padding-top: 1.3rem; padding-bottom: 4rem;}
    .hero {padding: 1.5rem 1.7rem; border-radius: 16px; background: linear-gradient(120deg,#192a56,#273c75); color: white; margin-bottom: 1rem;}
    .hero h1 {margin: 0 0 .35rem 0; font-size: 2rem;}
    .hero p {margin: 0; opacity: .92;}
    .case-card {border: 1px solid rgba(128,128,128,.25); border-radius: 12px; padding: 1rem 1.1rem; margin: .5rem 0 1rem 0;}
    .manager {border-left: 5px solid #e67e22; background: rgba(230,126,34,.08); padding: .9rem 1rem; border-radius: 8px; margin: .65rem 0;}
    .score-box {border: 1px solid rgba(128,128,128,.25); border-radius: 12px; padding: 1rem;}
    .small-note {font-size: .88rem; opacity: .78;}
    div[data-testid="stMetric"] {border: 1px solid rgba(128,128,128,.2); padding: .7rem; border-radius: 10px;}
    </style>
    """,
    unsafe_allow_html=True,
)


def initialise_state() -> None:
    defaults = {
        "team_name": "",
        "started": False,
        "page": "Welcome",
        "intake_done": False,
        "selected_questions": [],
        "round1_submitted": False,
        "round1_result": None,
        "round1_inputs": None,
        "round2_submitted": False,
        "round2_result": None,
        "round2_inputs": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_game() -> None:
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


def score_label(score: float, maximum: float) -> str:
    ratio = score / maximum if maximum else 0
    if ratio >= .85:
        return "Excellent"
    if ratio >= .70:
        return "Strong"
    if ratio >= .55:
        return "Developing"
    return "Needs revision"


def show_result_header(title: str, result: Dict[str, Any]) -> None:
    col1, col2 = st.columns([1, 2])
    with col1:
        st.metric(title, f"{result['score']:.1f} / {result['max']:.0f}")
    with col2:
        st.info(f"**{score_label(result['score'], result['max'])}.** The score is generated from the editable rubric in `data/scoring_rubrics.json`.")


def render_feedback_list(title: str, items: List[str], positive: bool = False, limit: int = 5) -> None:
    if not items:
        return
    icon = "✅" if positive else "→"
    st.markdown(f"**{title}**")
    for item in items[:limit]:
        st.markdown(f"{icon} {item}")


def make_report() -> str:
    team = st.session_state.team_name or "Anonymous team"
    lines = [
        "# Talent Acquisition Lab — Team Report",
        "",
        f"**Team:** {team}",
        f"**Scenario:** {SCENARIO['role_title']} at {SCENARIO['company']['name']}",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
    ]
    if st.session_state.round1_result:
        r1 = st.session_state.round1_result
        inputs = st.session_state.round1_inputs
        lines.extend([
            "## Round 1 — Intake meeting and job analysis",
            f"**Score:** {r1['score']:.1f}/100",
            "",
            "### Selected intake questions",
        ])
        question_lookup = {q["id"]: q["question"] for q in SCENARIO["intake_questions"]}
        lines.extend([f"- {question_lookup.get(qid, qid)}" for qid in inputs["selected_questions"]])
        lines.extend(["", "### Hiring brief"])
        field_labels = {
            "business_objective": "Business objective",
            "role_purpose": "Role purpose",
            "deliverables": "First-six-month deliverables",
            "essential_requirements": "Essential requirements",
            "desirable_requirements": "Desirable requirements",
            "constraints_conditions": "Constraints and employment conditions",
            "success_measures": "Success measures",
        }
        for key, label in field_labels.items():
            lines.extend([f"#### {label}", inputs["brief_fields"].get(key, ""), ""])
        lines.extend(["### Competency scorecard", ""])
        comp_lookup = {c["id"]: c["label"] for c in SCENARIO["competencies"]}
        for comp_id in inputs["selected_competencies"]:
            lines.append(f"- **{comp_lookup.get(comp_id, comp_id)} — {inputs['weights'].get(comp_id, 0)}%:** {inputs['indicators'].get(comp_id, '')}")
        lines.append("")

    if st.session_state.round2_result:
        r2 = st.session_state.round2_result
        inputs = st.session_state.round2_inputs
        channel_lookup = {c["id"]: c for c in SCENARIO["round2"]["channels"]}
        lines.extend([
            "## Round 2 — Attraction and sourcing",
            f"**Score:** {r2['score']:.1f}/100",
            "",
            "### Selected channels",
        ])
        for channel_id in inputs["selected_channels"]:
            channel = channel_lookup[channel_id]
            lines.append(f"- {channel['name']} — €{channel['cost']:,.0f}")
        lines.extend([
            "",
            "### Job advertisement",
            inputs["job_advert"],
            "",
            "### Boolean search string",
            f"`{inputs['boolean_string']}`",
            "",
            "### Candidate outreach message",
            inputs["outreach_message"],
            "",
        ])

    if st.session_state.round1_result and st.session_state.round2_result:
        overall = (st.session_state.round1_result["score"] + st.session_state.round2_result["score"]) / 2
        lines.extend([
            "## Overall prototype result",
            f"**Overall score:** {overall:.1f}/100",
            f"**Performance band:** {performance_band(overall)}",
            "",
            "> This is formative feedback from a deterministic prototype rubric. It should support debriefing, not replace instructor judgement.",
        ])
    return "\n".join(lines)


initialise_state()

st.markdown(
    f"""
    <div class="hero">
      <h1>🧭 {SCENARIO['game_title']}</h1>
      <p>Two-round minimum viable simulation: intake and job analysis → attraction and sourcing.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### Game navigation")
    if st.session_state.team_name:
        st.caption(f"Team: {st.session_state.team_name}")
    page_options = ["Welcome", "Round 1 — Intake & job analysis"]
    if st.session_state.round1_submitted:
        page_options.append("Round 2 — Attraction & sourcing")
    if st.session_state.round2_submitted:
        page_options.append("Results")
    current = st.session_state.page if st.session_state.page in page_options else page_options[0]
    selected_page = st.radio("Go to", page_options, index=page_options.index(current), label_visibility="collapsed")
    st.session_state.page = selected_page

    st.divider()
    st.markdown("### Progress")
    st.write("✅ Started" if st.session_state.started else "○ Start")
    st.write("✅ Round 1 submitted" if st.session_state.round1_submitted else "○ Round 1")
    st.write("✅ Round 2 submitted" if st.session_state.round2_submitted else "○ Round 2")
    st.divider()
    st.button("Reset simulation", on_click=reset_game, use_container_width=True)


if st.session_state.page == "Welcome":
    col1, col2 = st.columns([1.15, .85], gap="large")
    with col1:
        st.subheader("Your assignment")
        st.markdown(
            f"""
            You are the Talent Acquisition team for **{SCENARIO['company']['name']}**. Your task is to turn an ambiguous request into a defensible recruitment strategy for a **{SCENARIO['role_title']}**.

            In this prototype you will:

            1. conduct a constrained intake meeting;
            2. create a hiring brief and weighted competency scorecard;
            3. allocate a sourcing budget;
            4. write a job advertisement, Boolean search and outreach message.
            """
        )
        st.warning("The scenario and all candidate/company information are fictional. Scores are formative and deterministic.")

        with st.form("start_form"):
            team_name = st.text_input("Team name or anonymous code", value=st.session_state.team_name, placeholder="e.g., Team Atlas")
            submitted = st.form_submit_button("Start the simulation", type="primary")
            if submitted:
                st.session_state.team_name = team_name.strip() or "Anonymous team"
                st.session_state.started = True
                st.session_state.page = "Round 1 — Intake & job analysis"
                st.rerun()
    with col2:
        st.markdown("<div class='case-card'>", unsafe_allow_html=True)
        st.markdown(f"**Company:** {SCENARIO['company']['name']}")
        st.write(SCENARIO["company"]["description"])
        st.markdown(f"**Role:** {SCENARIO['role_title']}")
        st.markdown(f"**Base:** {SCENARIO['company']['location']}")
        st.markdown("**Project:** Unified loyalty programme across stores and e-commerce")
        st.markdown("</div>", unsafe_allow_html=True)


elif st.session_state.page == "Round 1 — Intake & job analysis":
    if not st.session_state.started:
        st.warning("Enter a team name on the Welcome page first.")
        st.stop()

    st.header("Round 1 — Intake meeting and job analysis")
    st.markdown("### Initial request")
    st.markdown(f"<div class='manager'><strong>Marketing Director:</strong><br>{SCENARIO['rough_hiring_need']}</div>", unsafe_allow_html=True)
    st.caption(SCENARIO["role_context"])

    st.markdown("### 1. Conduct the intake meeting")
    st.write(f"You have time for **{SCENARIO['intake_limit']} questions**. Choose carefully; the manager's answers will provide evidence for your hiring brief.")
    question_label_to_id = {q["question"]: q["id"] for q in SCENARIO["intake_questions"]}
    id_to_question = {q["id"]: q for q in SCENARIO["intake_questions"]}
    default_labels = [id_to_question[qid]["question"] for qid in st.session_state.selected_questions if qid in id_to_question]
    selected_labels = st.multiselect(
        "Questions to ask",
        options=list(question_label_to_id.keys()),
        default=default_labels,
        max_selections=SCENARIO["intake_limit"],
        disabled=st.session_state.round1_submitted,
        help="The question labels are not scored by length; they are scored by the decision-useful evidence they elicit.",
    )
    selected_ids = [question_label_to_id[label] for label in selected_labels]

    col_a, col_b = st.columns([1, 3])
    with col_a:
        if st.button("Conduct meeting", type="primary", disabled=not selected_ids or st.session_state.round1_submitted):
            st.session_state.selected_questions = selected_ids
            st.session_state.intake_done = True
            st.rerun()
    with col_b:
        if st.session_state.intake_done and not st.session_state.round1_submitted:
            if st.button("Change intake questions"):
                st.session_state.intake_done = False
                st.session_state.selected_questions = []
                st.rerun()

    if st.session_state.intake_done:
        st.markdown("#### Hiring manager responses")
        for question_id in st.session_state.selected_questions:
            item = id_to_question[question_id]
            with st.expander(item["question"], expanded=True):
                st.markdown(f"**Manager:** {generate_manager_response(question_id, SCENARIO)}")

    st.divider()
    st.markdown("### 2. Produce the hiring brief")
    st.caption("Write concise, evidence-based content. The scoring engine detects role-relevant concepts and flags potentially exclusionary requirements.")

    field_specs = [
        ("business_objective", "Business objective", "What organisational and customer outcome must the hire enable?"),
        ("role_purpose", "Role purpose", "Summarise why the role exists and its scope."),
        ("deliverables", "First-six-month deliverables", "List concrete outputs and milestones."),
        ("essential_requirements", "Essential requirements", "Describe only capabilities that are necessary on day one."),
        ("desirable_requirements", "Desirable requirements", "What experience would help but should not exclude transferable profiles?"),
        ("constraints_conditions", "Constraints and employment conditions", "Include timeline, location, salary/contract and practical constraints."),
        ("success_measures", "Success measures", "How will the hiring manager know that the person is succeeding?"),
    ]
    brief_fields: Dict[str, str] = {}
    for key, label, help_text in field_specs:
        brief_fields[key] = st.text_area(
            label,
            key=f"brief_{key}",
            height=100,
            help=help_text,
            disabled=st.session_state.round1_submitted,
        )

    st.markdown("### 3. Build a weighted competency scorecard")
    st.write("Choose exactly **six** competencies, allocate **100%**, and define one observable behavioural indicator for each.")
    comp_label_to_id = {c["label"]: c["id"] for c in SCENARIO["competencies"]}
    comp_lookup = {c["id"]: c for c in SCENARIO["competencies"]}
    selected_comp_labels = st.multiselect(
        "Competencies",
        options=list(comp_label_to_id.keys()),
        max_selections=6,
        key="competency_selector",
        disabled=st.session_state.round1_submitted,
    )
    selected_comp_ids = [comp_label_to_id[label] for label in selected_comp_labels]
    weights: Dict[str, float] = {}
    indicators: Dict[str, str] = {}

    for comp_id in selected_comp_ids:
        comp = comp_lookup[comp_id]
        with st.container(border=True):
            st.markdown(f"**{comp['label']}**")
            st.caption(comp["description"])
            c1, c2 = st.columns([1, 4])
            with c1:
                weights[comp_id] = st.number_input(
                    "Weight %",
                    min_value=0,
                    max_value=100,
                    value=int(st.session_state.get(f"weight_{comp_id}", 0)),
                    step=5,
                    key=f"weight_{comp_id}",
                    disabled=st.session_state.round1_submitted,
                )
            with c2:
                indicators[comp_id] = st.text_input(
                    "Observable behavioural indicator",
                    key=f"indicator_{comp_id}",
                    placeholder="e.g., Identifies dependencies, creates milestones and delivers agreed outputs by deadline.",
                    disabled=st.session_state.round1_submitted,
                )

    weight_total = sum(weights.values())
    st.metric("Current weighting", f"{weight_total:.0f}%", delta=f"{weight_total - 100:+.0f} from target")

    validation_errors = []
    if not st.session_state.intake_done:
        validation_errors.append("Conduct the intake meeting.")
    if len(selected_comp_ids) != 6:
        validation_errors.append("Select exactly six competencies.")
    if weight_total != 100:
        validation_errors.append("Make the competency weights total 100%.")
    if any(not value.strip() for value in brief_fields.values()):
        validation_errors.append("Complete every hiring-brief field.")
    if len(indicators) == 6 and any(not value.strip() for value in indicators.values()):
        validation_errors.append("Add an indicator for every selected competency.")

    if not st.session_state.round1_submitted:
        if validation_errors:
            st.caption("Before submission: " + " ".join(validation_errors))
        if st.button("Submit Round 1", type="primary", disabled=bool(validation_errors)):
            result = score_round1(
                st.session_state.selected_questions,
                brief_fields,
                selected_comp_ids,
                weights,
                indicators,
                RUBRICS["round1"],
            )
            st.session_state.round1_result = result
            st.session_state.round1_inputs = {
                "selected_questions": list(st.session_state.selected_questions),
                "brief_fields": dict(brief_fields),
                "selected_competencies": list(selected_comp_ids),
                "weights": dict(weights),
                "indicators": dict(indicators),
            }
            st.session_state.round1_submitted = True
            st.rerun()

    if st.session_state.round1_submitted:
        st.divider()
        show_result_header("Round 1 score", st.session_state.round1_result)
        r1 = st.session_state.round1_result
        cols = st.columns(3)
        cols[0].metric("Intake", f"{r1['intake']['score']:.1f}/20")
        cols[1].metric("Hiring brief", f"{r1['brief']['score']:.1f}/40")
        cols[2].metric("Competency scorecard", f"{r1['scorecard']['score']:.1f}/40")
        with st.expander("View formative feedback", expanded=True):
            render_feedback_list("Intake feedback", r1["intake"]["feedback"])
            missing = []
            for field_result in r1["brief"]["breakdown"].values():
                missing.extend(field_result["misses"])
            render_feedback_list("Concepts to strengthen in the brief", missing, limit=8)
            if r1["brief"]["penalties"]:
                render_feedback_list("Potentially exclusionary criteria detected", [p["label"] for p in r1["brief"]["penalties"]])
            render_feedback_list("Scorecard improvements", r1["scorecard"]["weight_feedback"] + r1["scorecard"]["indicator_feedback"], limit=8)
        if st.button("Continue to Round 2", type="primary"):
            st.session_state.page = "Round 2 — Attraction & sourcing"
            st.rerun()


elif st.session_state.page == "Round 2 — Attraction & sourcing":
    if not st.session_state.round1_submitted:
        st.warning("Complete Round 1 first.")
        st.stop()

    st.header("Round 2 — Attraction and sourcing")
    st.write("Translate the hiring brief into a balanced sourcing campaign and candidate-facing communications.")
    budget = SCENARIO["round2"]["budget"]
    st.info(f"Your campaign budget is **€{budget:,.0f}**. {SCENARIO['round2']['budget_note']}")

    st.markdown("### 1. Select sourcing channels")
    channel_lookup = {channel["id"]: channel for channel in SCENARIO["round2"]["channels"]}
    channel_label_to_id = {f"{c['name']} — €{c['cost']:,.0f}": c["id"] for c in SCENARIO["round2"]["channels"]}

    table_rows = [
        {
            "Channel": c["name"],
            "Cost": f"€{c['cost']:,.0f}",
            "Purpose": c["description"],
        }
        for c in SCENARIO["round2"]["channels"]
    ]
    st.dataframe(table_rows, use_container_width=True, hide_index=True)

    selected_channel_labels = st.multiselect(
        "Campaign channels",
        options=list(channel_label_to_id.keys()),
        key="channel_selector",
        disabled=st.session_state.round2_submitted,
    )
    selected_channel_ids = [channel_label_to_id[label] for label in selected_channel_labels]
    total_cost = sum(channel_lookup[channel_id]["cost"] for channel_id in selected_channel_ids)
    remaining = budget - total_cost
    c1, c2, c3 = st.columns(3)
    c1.metric("Selected channels", len(selected_channel_ids))
    c2.metric("Spend", f"€{total_cost:,.0f}")
    c3.metric("Budget remaining", f"€{remaining:,.0f}", delta=f"{remaining / budget:.0%}" if budget else None)
    if remaining < 0:
        st.error("The current campaign is over budget. Revise your channel selection.")

    st.markdown("### 2. Write the job advertisement")
    st.caption("Write the full advert in English or bilingual form. Include a credible value proposition, job-related requirements and transparent conditions.")
    job_advert = st.text_area(
        "Job advertisement",
        height=360,
        key="job_advert",
        disabled=st.session_state.round2_submitted,
        placeholder="Chef de projet marketing digital & omnicanal — Maison Nova\n\nAbout the transformation...",
    )

    st.markdown("### 3. Build a Boolean search string")
    boolean_string = st.text_input(
        "Boolean string",
        key="boolean_string",
        disabled=st.session_state.round2_submitted,
        placeholder='("chef de projet" OR "project manager") AND (digital OR omnicanal OR omnichannel) AND ...',
    )

    st.markdown("### 4. Write a direct-sourcing message")
    candidate = SCENARIO["round2"]["outreach_candidate"]
    st.markdown(f"<div class='case-card'><strong>{candidate['name']}</strong><br>{candidate['profile']}</div>", unsafe_allow_html=True)
    outreach_message = st.text_area(
        "Candidate outreach message",
        height=220,
        key="outreach_message",
        disabled=st.session_state.round2_submitted,
        placeholder="Bonjour Camille, ...",
    )

    validation_errors = []
    if len(selected_channel_ids) < 2:
        validation_errors.append("Select at least two sourcing channels.")
    if total_cost > budget:
        validation_errors.append("Bring the campaign within budget.")
    if len(job_advert.split()) < 80:
        validation_errors.append("Write a job advertisement of at least 80 words.")
    if len(boolean_string.strip()) < 20:
        validation_errors.append("Provide a usable Boolean string.")
    if len(outreach_message.split()) < 40:
        validation_errors.append("Write an outreach message of at least 40 words.")

    if not st.session_state.round2_submitted:
        if validation_errors:
            st.caption("Before submission: " + " ".join(validation_errors))
        if st.button("Submit Round 2", type="primary", disabled=bool(validation_errors)):
            result = score_round2(
                selected_channel_ids,
                SCENARIO["round2"]["channels"],
                budget,
                job_advert,
                boolean_string,
                outreach_message,
                RUBRICS["round2"],
            )
            st.session_state.round2_result = result
            st.session_state.round2_inputs = {
                "selected_channels": list(selected_channel_ids),
                "job_advert": job_advert,
                "boolean_string": boolean_string,
                "outreach_message": outreach_message,
            }
            st.session_state.round2_submitted = True
            st.rerun()

    if st.session_state.round2_submitted:
        st.divider()
        show_result_header("Round 2 score", st.session_state.round2_result)
        r2 = st.session_state.round2_result
        cols = st.columns(4)
        cols[0].metric("Channels", f"{r2['channels']['score']:.1f}/35")
        cols[1].metric("Job advert", f"{r2['advert']['score']:.1f}/30")
        cols[2].metric("Boolean", f"{r2['boolean']['score']:.1f}/15")
        cols[3].metric("Outreach", f"{r2['outreach']['score']:.1f}/20")
        with st.expander("View formative feedback", expanded=True):
            render_feedback_list("Channel portfolio strengths", r2["channels"]["coverage_hits"], positive=True)
            render_feedback_list("Channel portfolio gaps", r2["channels"]["coverage_misses"])
            render_feedback_list("Advert strengths", r2["advert"]["hits"], positive=True, limit=6)
            render_feedback_list("Advert concepts to add", r2["advert"]["misses"], limit=7)
            render_feedback_list("Boolean concepts to add", r2["boolean"]["misses"], limit=5)
            render_feedback_list("Outreach concepts to add", r2["outreach"]["misses"], limit=6)
            all_penalties = r2["channels"]["penalties"] + r2["advert"]["penalties"] + r2["boolean"]["penalties"] + r2["outreach"]["penalties"]
            if all_penalties:
                render_feedback_list("Penalties triggered", [f"{p['label']} ({p['points']})" for p in all_penalties])
        if st.button("View final results", type="primary"):
            st.session_state.page = "Results"
            st.rerun()


elif st.session_state.page == "Results":
    if not st.session_state.round2_submitted:
        st.warning("Complete both rounds first.")
        st.stop()

    r1 = st.session_state.round1_result
    r2 = st.session_state.round2_result
    overall = (r1["score"] + r2["score"]) / 2
    st.header("Prototype results")
    c1, c2, c3 = st.columns(3)
    c1.metric("Round 1", f"{r1['score']:.1f}/100")
    c2.metric("Round 2", f"{r2['score']:.1f}/100")
    c3.metric("Overall", f"{overall:.1f}/100")
    st.success(f"**{performance_band(overall)}**")

    st.markdown("### Debrief prompts")
    st.markdown(
        """
        1. Which initial hiring-manager preferences did you convert into evidence-based criteria—or reject?
        2. Which capable profiles might your sourcing strategy still fail to reach?
        3. Where could your advert or Boolean string produce unintended exclusion?
        4. What information would you need before moving to screening and assessment design?
        """
    )

    report = make_report()
    st.download_button(
        "Download team report (.md)",
        data=report,
        file_name=f"TA_Lab_{st.session_state.team_name.replace(' ', '_')}.md",
        mime="text/markdown",
        type="primary",
    )
    st.caption("Instructor note: exact scoring rules are stored in `data/scoring_rubrics.json` and can be edited without changing the interface code.")
