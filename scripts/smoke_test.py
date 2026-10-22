"""The smoke test of staging, run from a developer's machine over the tailnet by scripts/deploy.sh
after each staging deploy (docs/DEPLOY.md). It sends synthetic corpus files through the real
path: Tailscale, the web app, the launcher and a gVisor sandbox. It checks:

- the outputs, both Markdown and DOCX, against the corpus's reference text
- that a sandbox runs under every restriction the launcher asks for, in gVisor
- that a client-IP header the visitor forges does not change whose allowance is charged
- that /source-code opens the commit deployed, and that no sandbox is left behind

It prints how many seconds an OCR page takes, and exits 1 if any check fails. A check that
cannot be made, as when ssh to the server fails, fails rather than passes.

    uv run python scripts/smoke_test.py https://pdf-staging.tail46a117.ts.net --commit <sha> --ssh gmt
"""

import argparse
import io
import json
import re
import subprocess
import sys
import threading
import time
from dataclasses import replace
from html import unescape
from pathlib import Path
from typing import Any

import docx
import httpx
import pymupdf

from pdf_to_doc.docx_reading import read_docx
from pdf_to_doc.markdown import render_markdown, split_pages
from pdf_to_doc.model import Document, Paragraph
from pdf_to_doc.quality import score_page
from pdf_to_doc.summary import summarize
from pdf_to_doc.web.bot_check import TOKEN_FIELD
from pdf_to_doc.web.docker import sandbox_config
from pdf_to_doc.web.settings import Environment

REPOSITORY = "https://github.com/Mossujirat/pdf-to-doc-app"
CORPUS = Path(__file__).resolve().parent.parent / "corpus" / "synthetic"
ENVIRONMENT: Environment = "staging"  # whose sandboxes, by their label
# A text page and a scanned one, then two scans with stamps: both ways a page is read. With the
# real OCR engine every one of these pages scored a CER of 0 in the quality harness (2026-10-22).
FILES = ["mixed-text-and-scan", "stamped-scans"]
MAX_CER = 0.01
# Each request forges another client address, as a visitor could. If the web app believed them,
# each file would be charged to a different address, and the last would find a full allowance.
FORGED = ["203.0.113.11", "203.0.113.12", "203.0.113.13"]
WAIT = 600  # seconds a conversion may take, OCR in gVisor included
SUMMARY = "สรุปการแปลง"  # how the summary at the top of each output starts


class StagingSmokeTest:
    def __init__(self, site: str, commit: str, ssh: str, pages_per_day: int) -> None:
        self.site = site.rstrip("/")
        self.commit = commit
        self.ssh = ssh
        self.pages_per_day = pages_per_day
        self.failures: list[str] = []
        # One browser: its cookie names it, and it names the site's own origin on every request.
        self.client = httpx.Client(base_url=self.site, headers={"Origin": self.site}, timeout=60)

    def check(self, passed: bool, what: str) -> None:
        print(f"{'ok  ' if passed else 'FAIL'} {what}")
        if not passed:
            self.failures.append(what)

    def run(self) -> int:
        self.check(self.reachable(), "/health answers ok through Tailscale")
        home = self.client.get("/")
        self.check(home.status_code == 200 and "cf-turnstile" in home.text, "the home page shows the bot check")
        expected = f"{REPOSITORY}/tree/{self.commit}"
        source_code = self.client.get("/source-code")
        self.check(source_code.headers.get("location") == expected, f"/source-code opens {expected}")

        charged = 0
        for index, name in enumerate(FILES):
            source = CORPUS / f"{name}.pdf"
            inspected: dict[str, Any] = {}
            ended = threading.Event()
            watcher = None
            if index == 0:  # one sandbox is enough to see its restrictions
                watcher = threading.Thread(target=self.inspect_sandbox, args=(inspected, ended), daemon=True)
                watcher.start()
            link = self.upload(source.name, source.read_bytes(), FORGED[index])
            state, ocr_started, ended_at = self.wait(link)
            ended.set()
            self.check(state == "finished", f"{name}: the conversion finished (it ended {state})")
            if watcher is not None:
                watcher.join()
                self.check_restrictions(inspected)
            if state != "finished":
                continue
            charged += pymupdf.open(source).page_count
            self.check_outputs(name, link)
            if ocr_started is not None:
                ocr_pages = self.ocr_pages(link)
                seconds = (ended_at - ocr_started) / max(ocr_pages, 1)
                print(f"     {name}: {seconds:.1f} s per OCR page ({ocr_pages} OCR pages)")
            self.client.post(f"{link}/delete")

        self.check_allowance(charged)
        self.check(not self.sandboxes(running_only=False), "no sandbox is left behind")
        if self.failures:
            print(f"\n{len(self.failures)} check(s) failed")
            return 1
        print("\nevery check passed")
        return 0

    def reachable(self) -> bool:
        """Whether /health answers ok, waiting for a node just started: it joins the tailnet, and
        asks for its HTTPS certificate on the first connection."""
        deadline = time.monotonic() + WAIT
        while time.monotonic() < deadline:
            try:
                if self.client.get("/health").text == "ok":
                    return True
            except httpx.HTTPError:
                pass
            time.sleep(5)
        return False

    def upload(self, name: str, data: bytes, forged: str) -> str:
        response = self.client.post(
            "/conversions",
            data={TOKEN_FIELD: "smoke-test"},  # the test keys' secret passes any token
            files={"file": (name, data, "application/pdf")},
            headers={"X-Forwarded-For": forged},
        )
        if response.status_code != 303:
            raise SystemExit(f"FAIL the upload of {name} was answered {response.status_code}")
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
        """Each output page against its reference text. The DOCX output is also checked for broken
        text as it was written: reading it back repairs Thai text, and would hide some."""
        references = {
            int(match.group(1)): path.read_text(encoding="utf-8-sig")
            for path in (CORPUS / name).glob("page-*.reference.md")
            if (match := re.fullmatch(r"page-(\d{3})\.reference\.md", path.name))
        }
        if not references:
            self.check(False, f"{name}: reference text found in {CORPUS / name}")
            return
        markdown = split_pages(self.client.get(f"{link}/markdown").content.decode("utf-8"))
        docx_bytes = self.client.get(f"{link}/docx").content
        document = _without_summary(read_docx(docx_bytes))
        read_back = split_pages(render_markdown(document, summarize(document)))
        for output, pages in (("Markdown", markdown), ("DOCX", read_back)):
            for number, reference in sorted(references.items()):
                score = score_page(pages.get(number, ""), reference)
                self.check(
                    score.broken.total == 0 and score.cer <= MAX_CER,
                    f"{name} page {number}, {output}: CER {score.cer:.3f}, broken text {score.broken.total}",
                )
        written = "\n".join(p.text for p in docx.Document(io.BytesIO(docx_bytes)).paragraphs if not p.text.startswith(SUMMARY))
        broken = score_page(written, "\n".join(references[number] for number in sorted(references))).broken
        self.check(broken.total == 0, f"{name}, DOCX as written: broken text {broken.total}")

    def ocr_pages(self, link: str) -> int:
        """How many pages were read with OCR, as the result's pages table says."""
        return len(re.findall(r"<td>อ่านด้วย OCR</td>", self.client.get(link).text))

    def check_allowance(self, charged: int) -> None:
        """A file with more pages than are left today is stopped, and its page says how many are
        left: the allowance less what this visitor has used, whatever addresses it forged."""
        pdf = pymupdf.open()
        for _ in range(self.pages_per_day + 1):
            pdf.new_page()
        link = self.upload("over-the-allowance.pdf", pdf.tobytes(), FORGED[-1])
        state, _, _ = self.wait(link)
        text = re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", self.client.get(link).text)))
        left = self.pages_per_day - charged
        self.check(
            state == "over_allowance" and f"วันนี้แปลงได้อีก {left} หน้า" in text,
            f"a forged X-Forwarded-For does not change whose allowance is charged ({left} pages left)",
        )

    def inspect_sandbox(self, found: dict[str, Any], ended: threading.Event) -> None:
        """Find a sandbox of staging's while it runs, until the conversion has ended, and read how
        Docker started it."""
        while not ended.is_set():
            for identifier in self.sandboxes(running_only=True):
                inspected = self.remote(["docker", "inspect", identifier])
                found.update(json.loads(inspected)[0])
                return
            time.sleep(0.2)

    def check_restrictions(self, inspected: dict[str, Any]) -> None:
        if not inspected:
            self.check(False, "a sandbox was seen while it ran")
            return
        wanted = sandbox_config(image="", environment=ENVIRONMENT, runtime="runsc")
        for key, value in wanted["HostConfig"].items():
            actual = inspected["HostConfig"].get(key)
            self.check(_holds(actual, value), f"the sandbox runs with {key} {json.dumps(value)} (Docker: {json.dumps(actual)})")
        config = inspected["Config"]
        for key in ("User", "NetworkDisabled", "OpenStdin", "StdinOnce"):
            self.check(config.get(key) == wanted[key], f"the sandbox runs with {key} {json.dumps(wanted[key])}")
        self.check(not inspected.get("Mounts"), "the sandbox has no volume or folder of the server's")
        # The image's own environment holds no secret (Dockerfile); anything else came from elsewhere.
        image_env = json.loads(self.remote(["docker", "image", "inspect", inspected["Image"], "--format", "{{json .Config.Env}}"]))
        extra = set(config.get("Env") or []) - set(image_env) - set(wanted["Env"])
        self.check(not extra, f"the sandbox's environment is the image's own, and the launcher's {', '.join(wanted['Env'])}")

    def sandboxes(self, *, running_only: bool) -> list[str]:
        command = ["docker", "ps", "-q", "--filter", f"label=pdf-to-doc.sandbox={ENVIRONMENT}"]
        if not running_only:
            command.insert(2, "-a")
        return self.remote(command).split()

    def remote(self, command: list[str]) -> str:
        """A command's output on the server. If ssh fails, the test stops: a check that cannot be
        made must not pass."""
        result = subprocess.run(["ssh", "-n", self.ssh, *command], capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            raise SystemExit(f"FAIL {' '.join(command)} on {self.ssh}: {result.stderr.strip()}")
        return result.stdout


def _without_summary(document: Document) -> Document:
    """The DOCX output read back, without the summary that opens it: read back, it is the first
    paragraph of page 1, while the Markdown keeps its own above the first page."""
    first, *rest = document.pages
    if first.blocks and isinstance(first.blocks[0], Paragraph) and first.blocks[0].text.startswith(SUMMARY):
        first = replace(first, blocks=first.blocks[1:])
    return replace(document, pages=(first, *rest))


def _holds(actual: object, wanted: object) -> bool:
    """Whether Docker's value holds everything asked for: a mapping may hold more, as Docker adds
    its own defaults."""
    if isinstance(wanted, dict):
        return isinstance(actual, dict) and all(_holds(actual.get(key), value) for key, value in wanted.items())
    return actual == wanted


def main() -> None:
    parser = argparse.ArgumentParser(description="The smoke test of staging.")
    parser.add_argument("site", help="staging's address, such as https://pdf-staging.tail46a117.ts.net")
    parser.add_argument("--commit", required=True, help="the commit deployed, which /source-code must open")
    parser.add_argument("--ssh", default="gmt", help="the server, to see its sandboxes")
    # As compose.staging.yaml sets it.
    parser.add_argument("--pages-per-day", type=int, default=60, help="staging's daily allowance")
    args = parser.parse_args()
    sys.exit(StagingSmokeTest(args.site, args.commit, args.ssh, args.pages_per_day).run())


if __name__ == "__main__":
    main()
