import pytest

from growthmcp.core.utils import BlockedURLError, redact_secret, validate_public_url


def test_redact_secret_does_not_expose_token():
    assert redact_secret("super-secret-token") == "<redacted:18 chars>"


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:8080/internal",
        "http://169.254.169.254/latest/meta-data",
        "http://10.0.0.5/service",
        "ftp://example.com/file",
    ],
)
def test_validate_public_url_blocks_unsafe_targets(url):
    with pytest.raises(BlockedURLError):
        validate_public_url(url)


def test_validate_public_url_accepts_public_literal_ip():
    validate_public_url("https://8.8.8.8/")


def test_validate_public_url_requires_host():
    with pytest.raises(BlockedURLError):
        validate_public_url("https:///missing-host")
