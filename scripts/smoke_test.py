"""The smoke test of a deployed web service, run from a developer's machine over the tailnet by
scripts/deploy.sh after each staging deploy (docs/DEPLOY.md). It sends synthetic corpus files
through the real path: Tailscale, the web app, the launcher and a gVisor sandbox. It checks:

- the outputs, both Markdown and DOCX, against the corpus's reference text
- that a sandbox runs under every restriction the launcher asks for, in gVisor
- that a client-IP header the visitor forges does not change whose allowance is charged
- that /source-code opens the commit deployed, and that no sandbox is left behind

It prints how many seconds an OCR page takes, and exits 1 if any check fails.

    uv run python scripts/smoke_test.py https://pdf-staging.taila2e363.ts.net --commit <sha> --ssh gmt
"""

import argparse
import json
import re
import subprocess
import sys
import tempfile
import threading
import time
from html import unescape
from pathlib import Path
from typing import Any

import httpx
import pymupdf

from pdf_to_doc.docx_reading import read_docx
from pdf_to_doc.markdown import render_markdown, split_pages
from pdf_to_doc.quality import score_page
from pdf_to_doc.summary import summarize
from pdf_to_doc.web.bot_check import TOKEN_FIELD
from pdf_to_doc.web.docker import sandbox_config
from pdf_to_doc.web.settings import Environment

REPOSITORY = "https://github.com/Mossujirat/pdf-to-doc-app"
CORPUS = Path(__file__).resolve().parent.parent / "corpus" / "synthetic"
# A text page and a scanned one, then two scans with stamps: both ways a page is read. With the
# real OCR engine every one of these pages scored a CER of 0 in the quality harness (2026-10-22).
FILES = ["mixed-text-and-scan", "stamped-scans"]
MAX_CER = 0.01
# Each request forges another client address, as a visitor could. If the web app believed them,
# each file would be charged to a different address, and the last would find a full allowance.
FORGED = ["203.0.113.11", "203.0.113.12", "203.0.113.13"]
WAIT = 600  # seconds a conversion may take, OCR in gVisor included


class Smoke:
    def __init__(self, site: str, commit: str, ssh: str, environment: Environment, pages_per_day: int) -> None:
        self.site = site.rstrip("/")
        self.commit = commit
        self.ssh = ssh
        self.environment: Environment = environment
        self.pages_per_day = pages_per_day
        self.failures: list[str] = []
        # One browser: its cookie names it, and it names the site's own origin on every request.
        self.client = httpx.Client(base_url=self.site, headers={"Origin": self.site}, timeout=60)

    def check(self, passed: bool, what: str) -> None:
        print(f"{'ok  ' if passed else 'FAIL'} {what}")
        if not passed:
            self.failures.append(what)

    def run(self) -> int:
        self.check(self.client.get("/health").text == "ok", "/health answers ok")
        home = self.client.get("/")
        self.check(home.status_code == 200 and "cf-turnstile" in home.text, "the home page shows the bot check")
        expected = f"{REPOSITORY}/tree/{self.commit}"
        source_code = self.client.get("/source-code")
        self.check(source_code.headers.get("location") == expected, f"/source-code opens {expected}")

        charged = 0
        for index, name in enumerate(FILES):
            source = CORPUS / f"{name}.pdf"
            inspected: dict[str, Any] = {}
            watcher = None
            if index == 0:  # one sandbox is enough to see its restrictions
                watcher = threading.Thread(target=self.inspect_sandbox, args=(inspected,), daemon=True)
                watcher.start()
            link = self.upload(source, FORGED[index])
            state, ocr_started, ended = self.wait(link)
            self.check(state == "finished", f"{name}: the conversion finished (it ended {state})")
            if watcher is not None:
                watcher.join(timeout=WAIT)
                self.check_restrictions(inspected)
            if state != "finished":
                continue
            charged += pymupdf.open(source).page_count
            self.check_outputs(name, link)
            if ocr_started is not None:
                ocr_pages = self.ocr_pages(link)
                seconds = (ended - ocr_started) / max(ocr_pages, 1)
                print(f"     {name}: {seconds:.1f} s per OCR page ({ocr_pages} OCR pages)")
            self.client.post(f"{link}/delete")

        self.check_allowance(charged)
        self.check(not self.sandboxes(), "no sandbox is left behind")
        if self.failures:
            print(f"\n{len(self.failures)} check(s) failed")
            return 1
        print("\nevery check passed")
        return 0

    def upload(self, source: Path, forged: str) -> str:
        response = self.client.post(
            "/conversions",
            data={TOKEN_FIELD: "smoke-test"},  # the test keys' secret passes any token
            files={"file": (source.name, source.read_bytes(), "application/pdf")},
            headers={"X-Forwarded-For": forged},
        )
        if response.status_code != 303:
            raise SystemExit(f"FAIL the upload of {source.name} was answered {response.status_code}")
        return response.headers["location"]

    def wait(self, link: str) -> tuple[str, float | None, float]:
        """Wait for the conversion to end: how it ended, when OCR began and when it ended."""
        deadline = time.monotonic() + WAIT
        ocr_started = None
        while time.monotonic() < deadline:
            state = self.client.get(f"{link}/state").json()
            if ocr_started is None and state["text"].startswith("OCR"):
                ocr_started = time.monotonic()
            if not state["ongoing"]:
                return state["state"], ocr_started, time.monotonic()
            time.sleep(0.5)
        raise SystemExit(f"FAIL {link} did not end within {WAIT} seconds")

    def check_outputs(self, name: str, link: str) -> None:
        references = {
            int(match.group(1)): path.read_text(encoding="utf-8-sig")
            for path in (CORPUS / name).glob("page-*.reference.md")
            if (match := re.fullmatch(r"page-(\d{3})\.reference\.md", path.name))
        }
        markdown = split_pages(self.client.get(f"{link}/markdown").content.decode("utf-8"))
        document = read_docx(self.client.get(f"{link}/docx").content)
        docx = split_pages(render_markdown(document, summarize(document)))
        for output, pages in (("Markdown", markdown), ("DOCX", docx)):
            for number, reference in sorted(references.items()):
                score = score_page(pages.get(number, ""), reference)
                self.check(
                    score.broken.total == 0 and score.cer <= MAX_CER,
                    f"{name} page {number}, {output}: CER {score.cer:.3f}, broken text {score.broken.total}",
                )

    def ocr_pages(self, link: str) -> int:
        """How many pages were read with OCR, as the result's pages table says."""
        return len(re.findall(r"<td>อ่านด้วย OCR</td>", self.client.get(link).text))

    def check_allowance(self, charged: int) -> None:
        """A file with more pages than are left today is stopped, and its page says how many are
        left: the allowance less what this visitor has used, whatever addresses it forged."""
        pdf = pymupdf.open()
        for _ in range(self.pages_per_day + 1):
            pdf.new_page()
        big = Path(tempfile.gettempdir()) / "over-the-allowance.pdf"
        big.write_bytes(pdf.tobytes())
        link = self.upload(big, FORGED[-1])
        state, _, _ = self.wait(link)
        big.unlink()
        text = re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", self.client.get(link).text)))
        left = self.pages_per_day - charged
        self.check(
            state == "over_allowance" and f"วันนี้แปลงได้อีก {left} หน้า" in text,
            f"a forged X-Forwarded-For does not change whose allowance is charged ({left} pages left)",
        )

    def inspect_sandbox(self, found: dict[str, Any]) -> None:
        """Find this environment's sandbox while it runs, and read how Docker started it."""
        deadline = time.monotonic() + WAIT
        while time.monotonic() < deadline:
            for identifier in self.sandboxes():
                inspected = self.remote(["docker", "inspect", identifier])
                if inspected:
                    found.update(json.loads(inspected)[0])
                    return
            time.sleep(0.2)

    def check_restrictions(self, inspected: dict[str, Any]) -> None:
        if not inspected:
            self.check(False, "a sandbox was seen while it ran")
            return
        wanted = sandbox_config(image="", environment=self.environment, runtime="runsc")
        for key, value in wanted["HostConfig"].items():
            actual = inspected["HostConfig"].get(key)
            self.check(_holds(actual, value), f"the sandbox runs with {key} {json.dumps(value)} (Docker: {json.dumps(actual)})")
        config = inspected["Config"]
        self.check(config.get("User") == "converter", "the sandbox runs as the converter user")
        self.check(config.get("NetworkDisabled") is True, "the sandbox has its network disabled")

    def sandboxes(self) -> list[str]:
        return self.remote(["docker", "ps", "-aq", "--filter", f"label=pdf-to-doc.sandbox={self.environment}"]).split()

    def remote(self, command: list[str]) -> str:
        result = subprocess.run(["ssh", "-n", self.ssh, *command], capture_output=True, text=True, timeout=60)
        return result.stdout if result.returncode == 0 else ""


def _holds(actual: object, wanted: object) -> bool:
    """Whether Docker's value holds everything asked for: a mapping may hold more, as Docker adds
    its own defaults."""
    if isinstance(wanted, dict):
        return isinstance(actual, dict) and all(_holds(actual.get(key), value) for key, value in wanted.items())
    return actual == wanted


def main() -> None:
    parser = argparse.ArgumentParser(description="The smoke test of a deployed web service.")
    parser.add_argument("site", help="the deployed site, such as https://pdf-staging.taila2e363.ts.net")
    parser.add_argument("--commit", required=True, help="the commit deployed, which /source-code must open")
    parser.add_argument("--ssh", default="gmt", help="the server, to see its sandboxes")
    parser.add_argument("--environment", default="staging", choices=["staging", "production"])
    parser.add_argument("--pages-per-day", type=int, default=60, help="the deployed daily allowance")
    args = parser.parse_args()
    sys.exit(Smoke(args.site, args.commit, args.ssh, args.environment, args.pages_per_day).run())


if __name__ == "__main__":
    main()
