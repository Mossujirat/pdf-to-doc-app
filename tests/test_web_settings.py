"""The service's settings, as its containers take them: from the environment, each named
`PDF_TO_DOC_` and the setting's name in capitals. A value that a setting cannot take stops the
service from starting, as does a public service that would run unsafely."""

from dataclasses import replace

import pytest
from fake_sandbox import FakeSandbox
from web_browser import PRODUCTION

from pdf_to_doc.web.app import create_app
from pdf_to_doc.web.settings import LauncherSettings, Misconfigured, Settings, from_environment


def test_without_the_environment_every_setting_keeps_its_default() -> None:
    assert from_environment(Settings, {}) == Settings()


def test_each_setting_in_the_environment_replaces_its_default() -> None:
    environment = {
        "PDF_TO_DOC_MAX_WAITING": "5",
        "PDF_TO_DOC_MAX_HELD_OUTPUTS": "500000000",
        "PDF_TO_DOC_KEEP_FOR": "90.5",
        "PDF_TO_DOC_PRODUCTION": "true",
        "PDF_TO_DOC_SECURE_COOKIES": "0",
        "PDF_TO_DOC_HOSTNAME": "pdf.example.org",
        "PDF_TO_DOC_SANDBOX": "local",
        "PDF_TO_DOC_MODELS": "/opt/models",  # the converter's own, which is not a web setting
    }

    settings = from_environment(Settings, environment)

    assert settings == replace(
        Settings(),
        max_waiting=5,
        max_held_outputs=500_000_000,
        keep_for=90.5,
        production=True,
        secure_cookies=False,
        hostname="pdf.example.org",
        sandbox="local",
    )


def test_an_empty_value_leaves_a_setting_unset() -> None:
    # As compose passes a variable that its own environment lacks.
    settings = from_environment(Settings, {"PDF_TO_DOC_TURNSTILE_SECRET_KEY": "", "PDF_TO_DOC_MAX_RUNNING": ""})

    assert settings.turnstile_secret_key is None
    assert settings.max_running == 3


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("PDF_TO_DOC_PRODUCTION", "perhaps"),
        ("PDF_TO_DOC_MAX_RUNNING", "three"),
        ("PDF_TO_DOC_MAX_RUNNING", "³"),  # a digit to `isdigit`, but not to `int`
        ("PDF_TO_DOC_MAX_HELD_OUTPUTS", "1GB"),
        ("PDF_TO_DOC_MAX_HELD_OUTPUTS", "-1"),
        ("PDF_TO_DOC_KEEP_FOR", "ten minutes"),
        ("PDF_TO_DOC_KEEP_FOR", "inf"),
        ("PDF_TO_DOC_KEEP_FOR", "nan"),
        ("PDF_TO_DOC_KEEP_FOR", "0"),
        ("PDF_TO_DOC_KEEP_FOR", "-600"),
        ("PDF_TO_DOC_SANDBOX", "docker"),
    ],
)
def test_a_value_a_setting_cannot_take_stops_the_service_without_repeating_it(name: str, value: str) -> None:
    with pytest.raises(Misconfigured) as refused:
        from_environment(Settings, {name: value})

    assert name in str(refused.value)
    assert value not in str(refused.value)  # a value could be a secret


def test_the_outputs_held_are_capped_at_1_gb_unless_told_otherwise() -> None:
    # A GB of 1024 MB, as the output limit's 50 MB is 50 of 1024 * 1024 bytes.
    assert from_environment(Settings, {}).max_held_outputs == 1024 * 1024 * 1024


def test_the_launcher_takes_its_settings_from_the_environment() -> None:
    environment = {"PDF_TO_DOC_ENVIRONMENT": "staging", "PDF_TO_DOC_SANDBOX_RUNTIME": "runc", "PDF_TO_DOC_TIME_LIMIT": "600"}

    assert from_environment(LauncherSettings, environment) == LauncherSettings(
        environment="staging", sandbox_runtime="runc", time_limit=600
    )


def test_the_launcher_runs_sandboxes_in_gvisor_for_30_minutes_unless_told_otherwise() -> None:
    settings = from_environment(LauncherSettings, {"PDF_TO_DOC_ENVIRONMENT": "production"})

    assert settings.sandbox_runtime == "runsc"
    assert settings.time_limit == 30 * 60


def test_the_launcher_refuses_to_start_without_its_environment() -> None:
    # Without it, staging's launcher could take production's sandboxes for its own leftovers.
    with pytest.raises(Misconfigured) as refused:
        from_environment(LauncherSettings, {})

    assert "PDF_TO_DOC_ENVIRONMENT" in str(refused.value)


@pytest.mark.parametrize(
    "settings",
    [
        pytest.param(replace(PRODUCTION, sandbox="local"), id="converting outside the launcher's sandboxes"),
        pytest.param(replace(PRODUCTION, secure_cookies=False), id="a cookie that is not Secure"),
    ],
)
def test_the_public_service_refuses_to_start_unsafely(settings: Settings) -> None:
    with pytest.raises(Misconfigured):
        create_app(FakeSandbox(), settings)
