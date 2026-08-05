"""config.load_settings works from process env without configs/.env."""

from __future__ import annotations

import os

import pytest

from ingestion import config


def test_load_settings_from_env_only(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setattr(config, "ENV_PATH", tmp_path / "missing.env")
    monkeypatch.setenv("HUBSPOT_TOKEN", "hs")
    monkeypatch.setenv("DATABRICKS_HOST", "https://example.cloud.databricks.com/")
    monkeypatch.setenv("DATABRICKS_HTTP_PATH", "/sql/1.0/warehouses/abc")
    monkeypatch.setenv("DATABRICKS_TOKEN", "dapi")
    monkeypatch.delenv("DATABRICKS_CATALOG", raising=False)
    monkeypatch.delenv("DATABRICKS_BRONZE_SCHEMA", raising=False)

    settings = config.load_settings()
    assert settings.hubspot_token == "hs"
    assert settings.databricks_host == "example.cloud.databricks.com"
    assert settings.databricks_http_path == "/sql/1.0/warehouses/abc"
    assert settings.catalog == "crm"
    assert settings.bronze_schema == "bronze"


def test_load_settings_missing_vars_mentions_job_secrets(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setattr(config, "ENV_PATH", tmp_path / "missing.env")
    for name in config.REQUIRED_VARS:
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(RuntimeError, match="hubspot-crm"):
        config.load_settings()
