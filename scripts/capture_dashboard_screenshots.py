from __future__ import annotations

import argparse
import subprocess
import time
from pathlib import Path
from urllib.request import urlopen

from playwright.sync_api import sync_playwright


APP_PATH = "app/streamlit_app.py"

SHOTS = [
    ("Overview", "reports/figures/dashboard/dashboard_overview.png"),
    ("Selected month", "reports/figures/dashboard/dashboard_selected_month.png"),
    ("Diagnostics", "reports/figures/dashboard/dashboard_diagnostics.png"),
    ("Lead time", "reports/figures/dashboard/dashboard_lead_time.png"),
    ("Dataset intake", "reports/figures/dashboard/dashboard_dataset_intake.png"),
    ("Reviewer files", "reports/figures/dashboard/dashboard_reviewer_files.png"),
]


def wait_for_app(url: str, timeout_seconds: int = 60) -> None:
    start = time.time()

    while time.time() - start < timeout_seconds:
        try:
            with urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return
        except Exception:
            time.sleep(1)

    raise RuntimeError(f"Streamlit did not become ready: {url}")


def start_streamlit(port: int) -> subprocess.Popen:
    return subprocess.Popen(
        [
            "streamlit",
            "run",
            APP_PATH,
            "--server.headless=true",
            f"--server.port={port}",
            "--browser.gatherUsageStats=false",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def capture(url: str) -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        page.goto(url, wait_until="networkidle")

        for tab_name, output in SHOTS:
            page.get_by_role("tab", name=tab_name).click()
            page.wait_for_timeout(1500)

            path = Path(output)
            path.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(path), full_page=True)
            print(f"OK | screenshot={path}")

        browser.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8502)
    args = parser.parse_args()

    url = f"http://localhost:{args.port}"
    proc = start_streamlit(args.port)

    try:
        wait_for_app(url)
        capture(url)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()

    print("OK | dashboard screenshots captured")


if __name__ == "__main__":
    main()
