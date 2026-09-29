import os

from growthmcp.core.auth import AuthManager, MetaConfig, TokenInfo


def test_token_info_expiry():
    token = TokenInfo("x" * 30, expires_in=60)
    assert token.is_expired() is False


def test_meta_config_reads_environment(monkeypatch):
    monkeypatch.setenv("META_APP_ID", "test-app-id")
    config = MetaConfig()
    config.set_app_id("test-app-id")
    assert config.get_app_id() == "test-app-id"


def test_auth_url_uses_operator_app(monkeypatch):
    monkeypatch.setenv("META_APP_ID", "123456789")
    manager = AuthManager("123456789")
    url = manager.get_auth_url()
    assert "client_id=123456789" in url
    assert "facebook.com" in url
