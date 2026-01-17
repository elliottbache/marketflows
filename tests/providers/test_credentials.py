import pytest

from marketflows.providers import _credentials


class TestReadApiKey:
    def test_read_api_key_normal_file(self, tmp_path):
        # create fake api_key file with fake api_key
        api_key = "\nthisismyapikey "
        p = tmp_path / "api_key.txt"
        p.write_text(api_key)

        # check that we read the same api_key from the file
        assert _credentials.read_api_key(tmp_path / "api_key.txt") == api_key.strip()

    @pytest.mark.parametrize(
        "api_key, api_key_file, exc, exc_text",
        [
            (
                "thisismyapikey",
                "api_keyp.txt",
                FileNotFoundError,
                "API key file not found",
            ),
            ("thisismyapikey", "", IsADirectoryError, "API key file is a directory"),
            ("", "api_key.txt", ValueError, "API key is empty"),
        ],
        ids=["not_a_file", "is_directory", "empty_file"],
    )
    def test_read_api_key_exception(
        self, tmp_path, api_key, api_key_file, exc, exc_text
    ):
        # create fake api_key file with fake api_key
        p = tmp_path / "api_key.txt"
        p.write_text(api_key)

        # check that we read the same api_key from the file
        with pytest.raises(exc, match=exc_text):
            _credentials.read_api_key(tmp_path / api_key_file)
