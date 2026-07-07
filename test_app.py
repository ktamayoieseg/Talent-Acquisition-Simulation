from streamlit.testing.v1 import AppTest


def test_welcome_and_round1_render_without_exceptions():
    app = AppTest.from_file("app.py", default_timeout=20)
    app.run()
    assert not app.exception
    assert any(button.label == "Start the simulation" for button in app.button)

    app.text_input[0].set_value("Pilot Team")
    next(button for button in app.button if button.label == "Start the simulation").click()
    app.run()

    assert not app.exception
    assert any(header.value == "Round 1 — Intake meeting and job analysis" for header in app.header)
    assert len(app.multiselect) >= 2
