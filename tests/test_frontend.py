"""Playwright end-to-end tests for the Red Planet Mission Control dashboard."""

import pytest
from playwright.sync_api import Page, expect


# ---------------------------------------------------------------------------
# Health indicator
# ---------------------------------------------------------------------------

def test_health_dot_turns_green(page: Page, live_server: str):
    """Status dot must become green once the backend responds."""
    page.goto(live_server)
    expect(page.locator("#dot")).to_have_class("status-dot ok", timeout=6_000)


def test_health_message_shows_mission(page: Page, live_server: str):
    """Health message must mention 'Red Planet' after connecting."""
    page.goto(live_server)
    expect(page.locator("#health-msg")).to_contain_text("Red Planet", timeout=6_000)


# ---------------------------------------------------------------------------
# Stats analysis — happy path
# ---------------------------------------------------------------------------

def test_analyze_shows_results_panel(page: Page, live_server: str):
    """Results panel must appear after submitting valid readings."""
    page.goto(live_server)
    page.fill("#readings", "10, 20, 30, 40, 50")
    page.click("#analyze-btn")
    expect(page.locator("#results")).to_be_visible(timeout=5_000)


def test_analyze_count(page: Page, live_server: str):
    """Count stat must equal the number of readings submitted."""
    page.goto(live_server)
    page.fill("#readings", "1, 2, 3, 4, 5")
    page.click("#analyze-btn")

    rows = page.locator(".stat-row")
    expect(rows).to_have_count(6, timeout=5_000)  # count/mean/median/std_dev/min/max

    count_value = page.locator(".stat-row").nth(0).locator(".stat-value")
    expect(count_value).to_have_text("5")


def test_analyze_mean(page: Page, live_server: str):
    """Mean of [10, 20, 30] must be 20."""
    page.goto(live_server)
    page.fill("#readings", "10, 20, 30")
    page.click("#analyze-btn")

    mean_value = page.locator(".stat-row").nth(1).locator(".stat-value")
    expect(mean_value).to_have_text("20", timeout=5_000)


def test_analyze_min_max(page: Page, live_server: str):
    """Min and max must match the smallest and largest readings."""
    page.goto(live_server)
    page.fill("#readings", "5, 99, 42")
    page.click("#analyze-btn")

    rows = page.locator(".stat-row")
    min_value = rows.nth(4).locator(".stat-value")
    max_value = rows.nth(5).locator(".stat-value")
    expect(min_value).to_have_text("5", timeout=5_000)
    expect(max_value).to_have_text("99")


def test_analyze_single_reading(page: Page, live_server: str):
    """A single reading must produce std_dev of 0."""
    page.goto(live_server)
    page.fill("#readings", "42")
    page.click("#analyze-btn")

    std_value = page.locator(".stat-row").nth(3).locator(".stat-value")
    expect(std_value).to_have_text("0", timeout=5_000)


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

def test_empty_input_shows_error(page: Page, live_server: str):
    """Submitting with no readings must show an inline error message."""
    page.goto(live_server)
    page.click("#analyze-btn")
    expect(page.locator("#error")).to_be_visible()
    expect(page.locator("#error")).not_to_be_empty()


def test_non_numeric_input_shows_error(page: Page, live_server: str):
    """Non-numeric input (no parseable floats) must show an error."""
    page.goto(live_server)
    page.fill("#readings", "alpha, beta, gamma")
    page.click("#analyze-btn")
    expect(page.locator("#error")).to_be_visible(timeout=3_000)


def test_results_hidden_before_submit(page: Page, live_server: str):
    """Results panel must be hidden on initial page load."""
    page.goto(live_server)
    expect(page.locator("#results")).to_be_hidden()


# ---------------------------------------------------------------------------
# Button state during request
# ---------------------------------------------------------------------------

def test_button_re_enables_after_response(page: Page, live_server: str):
    """Analyze button must be enabled again after results arrive."""
    page.goto(live_server)
    page.fill("#readings", "1, 2, 3")
    page.click("#analyze-btn")
    expect(page.locator("#results")).to_be_visible(timeout=5_000)
    expect(page.locator("#analyze-btn")).to_be_enabled()
    expect(page.locator("#analyze-btn")).to_have_text("Analyze")
