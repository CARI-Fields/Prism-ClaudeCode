def test_harness_imports():
    import experiment.harness
    assert hasattr(experiment.harness, "__version__")
