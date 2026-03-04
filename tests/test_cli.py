from marketflows import cli


def test_main_success(monkeypatch):
    called = {"run": False, "log": False}

    def fake_run_pipeline(**_k):
        called["run"] = True

    def fake_configure_logging(**_k):
        called["log"] = True

    monkeypatch.setattr(cli, "run_pipeline", fake_run_pipeline)
    monkeypatch.setattr(cli, "configure_logging", fake_configure_logging)

    assert cli.main([]) == 0
    assert called["log"] is True
    assert called["run"] is True
