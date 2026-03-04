from marketflows import cli


class TestCli:
    def test_main_success(self, monkeypatch):
        monkeypatch.setattr(cli, "run_pipeline", lambda **_k: None)
        monkeypatch.setattr(cli, "configure_logging", lambda **_k: None)
        assert cli.main([]) == 0
