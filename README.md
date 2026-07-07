# Talent Acquisition Lab — Minimum Viable Prototype

A two-round Streamlit simulation for a Master-level Talent Acquisition course.

## What is included

- **Round 1: Intake meeting and job analysis**
  - Ambiguous hiring request
  - Constrained selection of intake questions
  - Curated hiring-manager responses
  - Hiring brief fields
  - Six-competency weighted scorecard
  - Deterministic formative scoring and feedback

- **Round 2: Attraction and sourcing**
  - Fictional €12,000 campaign budget
  - Ten sourcing-channel choices
  - Job advertisement
  - Boolean search string
  - Direct-sourcing message to a passive candidate
  - Deterministic formative scoring and feedback

- Downloadable Markdown team report
- Editable scenario and scoring files
- Unit tests for the scoring engine

## Design choice: no paid AI dependency in the MVP

The first prototype uses a curated response bank for the hiring manager. This provides a stable baseline for testing the learning design and scoring before introducing a live language model. The interface is deliberately structured so that a later `generate_manager_response()` adapter can replace the fixed response lookup.

This is useful pedagogically because the hidden candidate/job ground truth and all scores remain deterministic. A future AI model should vary dialogue and coaching, not alter the scoring rules.

## Run locally

1. Install Python 3.10 or newer.
2. Open a terminal in this folder.
3. Create and activate a virtual environment if desired.
4. Install the dependency:

```bash
pip install -r requirements.txt
```

5. Start the app:

```bash
streamlit run app.py
```

Streamlit will open the game in your browser, usually at `http://localhost:8501`.

## Deploy free on Streamlit Community Cloud

1. Create a new public GitHub repository.
2. Upload this entire folder, preserving the `data` and `.streamlit` directories.
3. Sign in to Streamlit Community Cloud.
4. Choose **Create app**, select the repository and set the entrypoint to `app.py`.
5. Deploy and share the resulting `streamlit.app` URL with students.

No student account is required for a public app. Each browser session has its own temporary game state. The MVP does **not** store submissions after the session ends.

## Edit the content

- `data/scenario.json` controls the company, rough brief, intake questions, manager responses, competencies, budget, channels and outreach profile.
- `data/scoring_rubrics.json` controls points, concept terms, target weights, portfolio bonuses and penalties.
- `scoring.py` contains the generic deterministic scoring functions.
- `ai_adapter.py` provides the curated manager-response function and the seam for a future LLM.
- `app.py` contains the interface and game flow.
- `TEST_SCRIPT.md` contains a high-scoring manual test submission for instructors.

### Scoring philosophy

The engine gives credit for evidence-related concepts rather than exact sentences. It normalises case and accents, so French and English variants can be added to the keyword lists. It also applies a small number of transparent penalties for exclusionary or unnecessarily narrow criteria.

Keyword scoring is deliberately simple for an MVP. During pilot testing, review false positives and false negatives and update the concept lists. For summative assessment, use the game score as formative evidence and grade the decision rationale separately.

## Tests

Run:

```bash
pytest -q
```

The tests compare strong and weak submissions and verify core budget/channel behaviour.

## Suggested classroom test

- 5 minutes: briefing
- 20 minutes: Round 1 intake and hiring brief
- 15 minutes: competency scorecard
- 20 minutes: Round 2 channel strategy
- 20 minutes: advert, Boolean search and outreach
- 20–30 minutes: facilitated debrief

## Important limitations

- The app has no authentication or persistent database.
- Scoring is keyword- and rule-based; it is not a semantic evaluator.
- Channel costs and yields are fictional teaching assumptions.
- A public Streamlit deployment should not contain real applicant or student personal data.
- Session state can be lost if the browser is closed or the free host restarts.
