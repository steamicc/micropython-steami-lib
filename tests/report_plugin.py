"""Pytest plugin that generates Markdown test reports for versioning.

Generates a directory per test session containing:
- README.md: general summary with context and links to driver reports
- <driver>.md: detailed report per driver with measured values
"""

import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest

REPORTS_DIR = Path(__file__).parent.parent / "reports"


def _get_board_info(port):
    """Query board info via mpremote."""
    if not port:
        return {}
    try:
        result = subprocess.run(
            ["mpremote", "connect", port, "exec",
             "import sys, os\n"
             "print(sys.implementation.name)\n"
             "print('.'.join(str(x) for x in sys.implementation.version[:3]))\n"
             "print(sys.implementation._machine)\n"
             "print(sys.implementation._build)\n"
             "print(sys.platform)"],
            capture_output=True, text=True, timeout=15, check=False,
        )
        if result.returncode == 0:
            lines = result.stdout.strip().splitlines()
            if len(lines) >= 5:
                return {
                    "runtime": lines[0],
                    "version": lines[1],
                    "machine": lines[2],
                    "build": lines[3],
                    "platform": lines[4],
                }
    except Exception:
        # Best-effort: report metadata is optional, never fail the test session.
        return {}
    return {}


class ReportCollector:
    """Collects test results during a pytest session."""

    def __init__(self):
        self.results = []
        self.port = None
        self.board_info = {}
        self.start_time = None
        self.end_time = None

    def add_result(self, driver, test_name, mode, status, detail=""):
        self.results.append({
            "driver": driver,
            "test": test_name,
            "mode": mode,
            "status": status,
            "detail": detail,
        })


# Global collector instance
_collector = ReportCollector()


def get_collector():
    """Return the global report collector."""
    return _collector


def pytest_configure(config):
    config.pluginmanager.register(ReportPlugin(config), "report_plugin")


class ReportPlugin:
    def __init__(self, config):
        self.config = config

    @pytest.hookimpl(tryfirst=True)
    def pytest_sessionstart(self, session):
        _collector.start_time = datetime.now(tz=timezone.utc)
        _collector.port = session.config.getoption("--port", default=None)
        if _collector.port:
            _collector.board_info = _get_board_info(_collector.port)

    @pytest.hookimpl(trylast=True)
    def pytest_runtest_logreport(self, report):
        if report.when != "call":
            return

        # Parse test ID: driver/test_name/mode
        node_id = report.nodeid
        if "[" in node_id and "]" in node_id:
            params = node_id.split("[")[1].rstrip("]")
            parts = params.rsplit("/", 2)
            if len(parts) == 3:
                driver, test_name, mode = parts
            else:
                driver, test_name, mode = "?", params, "?"
        else:
            driver, test_name, mode = "?", node_id, "?"

        if report.passed:
            status = "PASS"
        elif report.failed:
            status = "FAIL"
        elif report.skipped:
            status = "SKIP"
        else:
            status = "?"

        detail = ""
        if report.failed and report.longreprtext:
            for line in report.longreprtext.splitlines():
                if "AssertionError" in line or "assert" in line.lower():
                    detail = line.strip()
                    break
        if report.capstdout:
            detail = report.capstdout.strip()

        _collector.add_result(driver, test_name, mode, status, detail)

    @pytest.hookimpl(trylast=True)
    def pytest_sessionfinish(self, session, exitstatus):
        _collector.end_time = datetime.now(tz=timezone.utc)

        report_opt = session.config.getoption("--report", default=None)
        if report_opt is None or report_opt == "none":
            return

        generate_report(_collector, report_opt)


def pytest_addoption(parser):
    parser.addoption(
        "--report",
        action="store",
        default=None,
        help="Generate Markdown test reports. "
             "Value is the report directory name, "
             "or 'auto' for timestamped name, or 'none' to disable.",
    )


def _context_lines(collector):
    """Build the context section (shared between index and driver reports)."""
    now = collector.end_time or datetime.now(tz=timezone.utc)
    lines = []
    lines.append("| | |")
    lines.append("|---|---|")
    lines.append(f"| **Date** | {now.strftime('%Y-%m-%d %H:%M:%S')} |")
    if collector.port:
        lines.append(f"| **Port** | `{collector.port}` |")
    info = collector.board_info
    if info:
        lines.append(f"| **Board** | {info.get('machine', '?')} |")
        lines.append(f"| **Build** | {info.get('build', '?')} |")
        lines.append(f"| **Firmware** | {info.get('runtime', '?')} {info.get('version', '?')} |")
        lines.append(f"| **Platform** | {info.get('platform', '?')} |")
    if collector.start_time and collector.end_time:
        dt = (collector.end_time - collector.start_time).total_seconds()
        lines.append(f"| **Duration** | {dt:.1f}s |")
    return lines


def _status_for(results):
    """Return PASS/FAIL status for a list of results."""
    return "PASS" if all(r["status"] in ("PASS", "SKIP") for r in results) else "FAIL"


def _count(results):
    """Return (passed, failed, skipped, total) counts."""
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    skipped = sum(1 for r in results if r["status"] == "SKIP")
    return passed, failed, skipped, len(results)


def _results_table(results):
    """Build a Markdown results table from a list of results."""
    lines = []
    lines.append("| Test | Mode | Status | Detail |")
    lines.append("|------|------|:------:|--------|")
    for r in results:
        detail = r["detail"].replace("\n", " ").replace("|", "\\|")
        if len(detail) > 120:
            detail = detail[:117] + "..."
        lines.append(f"| {r['test']} | {r['mode']} | **{r['status']}** | {detail} |")
    return lines


def generate_report(collector, report_name=None):
    """Generate a report directory with index + per-driver reports."""
    if not collector.results:
        return

    now = collector.end_time or datetime.now(tz=timezone.utc)
    if report_name and report_name not in ("auto", "none"):
        dir_name = report_name
    else:
        dir_name = now.strftime("%Y-%m-%d_%H%M%S")

    report_dir = REPORTS_DIR / dir_name
    report_dir.mkdir(parents=True, exist_ok=True)

    # Group by driver
    drivers = {}
    for r in collector.results:
        drivers.setdefault(r["driver"], []).append(r)

    passed, failed, skipped, total = _count(collector.results)
    global_status = _status_for(collector.results)

    # === Generate README.md (index) ===
    lines = []
    lines.append(f"# Test Report - {now.strftime('%d/%m/%Y %H:%M')}")
    lines.append("")

    # Context
    lines.append("## Context")
    lines.append("")
    lines.extend(_context_lines(collector))
    lines.append("")

    # Global summary
    lines.append(f"## Summary: {global_status}")
    lines.append("")
    lines.append("| Passed | Failed | Skipped | Total |")
    lines.append("|:------:|:------:|:-------:|:-----:|")
    lines.append(f"| {passed} | {failed} | {skipped} | {total} |")
    lines.append("")

    # Driver overview table with links
    lines.append("## Drivers")
    lines.append("")
    lines.append("| Driver | Status | Passed | Failed | Skipped | Report |")
    lines.append("|--------|:------:|:------:|:------:|:-------:|--------|")

    for driver in sorted(drivers):
        results = drivers[driver]
        d_passed, d_failed, d_skipped, d_total = _count(results)
        d_status = _status_for(results)
        lines.append(
            f"| `{driver}` | **{d_status}** | {d_passed} | {d_failed} "
            f"| {d_skipped} | [{driver}.md]({driver}.md) |"
        )
    lines.append("")

    index_path = report_dir / "README.md"
    index_path.write_text("\n".join(lines), encoding="utf-8")

    # === Generate per-driver reports ===
    for driver, results in sorted(drivers.items()):
        d_passed, d_failed, d_skipped, d_total = _count(results)
        d_status = _status_for(results)

        lines = []
        lines.append(f"# {driver} - Test Report")
        lines.append("")
        lines.append("[< Back to summary](README.md)")
        lines.append("")

        # Context
        lines.append("## Context")
        lines.append("")
        lines.extend(_context_lines(collector))
        lines.append("")

        # Summary
        lines.append(f"## Summary: {d_status}")
        lines.append("")
        lines.append("| Passed | Failed | Skipped | Total |")
        lines.append("|:------:|:------:|:-------:|:-----:|")
        lines.append(f"| {d_passed} | {d_failed} | {d_skipped} | {d_total} |")
        lines.append("")

        # Separate mock and hardware results
        mock_results = [r for r in results if r["mode"] == "mock"]
        hw_results = [r for r in results if r["mode"] == "hardware"]

        if mock_results:
            lines.append("## Mock tests")
            lines.append("")
            lines.extend(_results_table(mock_results))
            lines.append("")

        if hw_results:
            lines.append("## Hardware tests")
            lines.append("")
            lines.extend(_results_table(hw_results))
            lines.append("")

        driver_path = report_dir / f"{driver}.md"
        driver_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"\nReport saved to: {report_dir}/")
    return report_dir
