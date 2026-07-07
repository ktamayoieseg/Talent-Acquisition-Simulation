def test_app_importable():
    import scoring
    assert callable(scoring.score_round1)
