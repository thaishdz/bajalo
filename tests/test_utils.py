import pytest

from bajalo.utils import is_valid_url


@pytest.mark.parametrize(
    "text, expected",
    [
        pytest.param("https://www.youtube.com/watch?v=YE7VzlLtp-4", True, id="youtube-https"),
        pytest.param("http://example.com/video.mp4", True, id="plain-http"),
        pytest.param("  https://youtu.be/abc  ", True, id="surrounding-spaces"),
        pytest.param("youtube.com/watch?v=abc", False, id="no-scheme"),
        pytest.param("ftp://example.com/a", False, id="wrong-scheme"),
        pytest.param("https://", False, id="no-domain"),
        pytest.param("hola", False, id="plain-text"),
        pytest.param("", False, id="empty"),
        pytest.param("   ", False, id="only-spaces"),
    ],
)
def test_is_valid_url(text, expected):
    assert is_valid_url(text) is expected