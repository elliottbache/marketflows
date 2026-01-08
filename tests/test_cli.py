from marketflows import cli


class TestCli:
    def test_main_success(self):
        assert cli.main() == 0
