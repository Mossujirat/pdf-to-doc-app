# 05: Choose kept images on the web

**Parent:** Kept images spec, in this feature folder.

**What to build:**
- **Choosing:** on the home page, a visitor chooses OCR or kept images above the drop area, before a dropped file starts converting.
- **Plumbing:** the choice goes with the file from the web app through the launcher to the sandbox, checked as untrusted at each step.
- **Following it:** while the file converts, its page shows a step for the page images. Once it has finished, the page shows which pages were kept.
- **The home page** explains both options truthfully.

**Blocked by:** 01

**Status:** done

**Branch:** `feat/kept-images-web`

**From the form to the sandbox**
- [x] **The form:** the choice is a field inside the upload form, so it goes with a dropped or picked file.
  - Missing, it means OCR, as from a page loaded before this change.
  - Any other value is refused as not an upload.
- [x] **The conversion** holds the setting while it waits or runs.
- [x] **The launcher:** the web app sends it the setting with the source file, in the frame that starts the conversion.
  - The launcher reads it as untrusted, like every frame: anything but the two values breaks the frames.
  - The frame's shape is the implementer's.
- [x] **Docker:** the launcher creates the sandbox with `PDF_TO_DOC_KEEP_IMAGES` set. Nothing else in the sandbox's configuration changes (ADR 0004).
- [x] **The sandbox entry point** reads that variable, its second setting beside the OCR thread count. Its run function takes the setting as a parameter, for tests.
- [x] **The local sandbox,** for development, sets the same variable on its process.
- [x] **Event lines** still carry none of the file's content.

**The home page**
- [x] **The control:** two options above the drop area.
  - OCR is selected whenever the page opens, and the choice is not remembered.
  - It works without a script, through the noscript button.
  - It works at phone width.
  - Choosing an option never opens the file picker, and dropping a file anywhere on the form still sends it.
- [x] **Design:** made with the impeccable skill, inheriting DESIGN.md and PRODUCT.md, including the One Green Rule. DESIGN.md records the new control.
- [x] **Copy:**
  - The step about waiting in "แปลงอย่างไร" says scans take minutes with OCR. It now mentions the option.
  - In "ข้างในทำอะไรกับไฟล์ของคุณ", reading page by page shows the kept-images option.
  - The placeholders paragraph says pictures show as themselves in the DOCX when images are kept.
  - The examples stay made up.

**The conversion's page**
- [x] **The page images step:** a step, "เก็บหน้าสแกนเป็นภาพ", with its page count and progress bar.
  - It shows only when kept images was chosen.
  - It is marked as not needed when no page was kept.
  - Without kept images, the steps are as today.
- [x] **The finished table:** its "อ่านจาก" column says "เก็บเป็นภาพ" for kept pages. The headline shows kept pages from the summary.
- [x] **A kept page whose text layer could not be trusted** (ticket 02) is noted as such in the table, not as "ข้อความในไฟล์ผิด จึงอ่านด้วย OCR", which is what the table says today for every page whose text layer could not be trusted. The headline already says "จึงไม่ได้นำมาใช้".
- [x] **Statistics** count kept pages among pages by kind.
- [x] **The privacy page** is unchanged. Outputs are still held in memory, and deleted within 10 minutes or when the visitor deletes them.

**Tests**
- [x] **The web app with a fake sandbox:**
  - the setting reaches the sandbox for each option, and for a missing field;
  - another value is refused.
- [x] **The launcher with fake Docker:**
  - the setting reaches the sandbox's environment;
  - a frame with a bad setting is refused.

  Run the launcher's socket tests in the Linux image.
- [x] **The sandbox's run function** with the setting on and off. The local sandbox passes it too.
- [x] **The home page:** the control sits inside the upload form, with OCR selected. The copy changes.
- [x] **The conversion's page:** the page images step, waiting, running and skipped, and the finished table with kept pages.
- [x] **Statistics** with kept pages.
- [x] **Checked by eye** with `pdf-to-doc-web --dev` and a synthetic scan, at desktop and phone width:
  - choose kept images;
  - drop the file;
  - follow the steps;
  - download the DOCX.
- [x] pytest, mypy, and the checks in the Linux image all pass.

## Comments

**2026-10-25, implemented on branch `feat/kept-images-web`**, branched from `feat/kept-images` because PR #15 was not merged yet.

- **From the form to the sandbox**
  - **The form field** is `keep_images`, `no` or `yes` (`upload.KEEP_IMAGES_VALUES`). Missing, it is `no`; any other value is refused as not an upload, before the bot check.
  - **The conversion** holds the choice as `Conversion.keep_images` and passes it to `Sandbox.convert(source, keep_images=...)`.
  - **The launcher's frame:** the web app starts a conversion with a `run` frame, as before, or a `run-keeping-images` frame. A frame of any other kind breaks the frames, so no sandbox starts. An old web app's `run` still means OCR.
  - **Docker:** `sandbox_config` adds `PDF_TO_DOC_KEEP_IMAGES=0` or `=1` to `Env`, and nothing else changes; a test compares the two configurations whole. The staging smoke test asks for `keep_images=False`, since its uploads make no choice.
  - **The sandbox entry point** reads the variable: unset, empty or `0` reads scans with OCR, and `1` keeps images. Any other value stops it before it reads the file. Its traceback then reaches the launcher as a line that is not an event, so the conversion fails as a broken protocol. `sandbox.keep_images_setting` is the one place the value is written; Docker's config, the local sandbox and the decoder all use it.
  - **Fake Docker** now starts each sandbox with the `Env` of `sandbox_config`, so the launcher tests check that the variable Docker sets is the one the entry point reads.
- **The conversion's page**
  - **The step** "เก็บหน้าสแกนเป็นภาพ" sits between reading and OCR, as the converter makes kept pages first. It shows only when kept images was chosen. It is skipped ("ไม่ต้องใช้") when no page was kept. It shows "หน้า x/y" and a progress bar, as OCR does.
  - **Stages reached:** `Conversion.reached`, the set of stages the sandbox reported, replaced `read_with_ocr`. Both optional steps read it.
  - **The heading** while pages are kept is "เก็บภาพหน้า x/y", as the CLI prints it.
  - **A sandbox reporting kept pages for a conversion that did not ask for them** is malformed: the conversion fails. Otherwise the page could not place the step.
  - **The table** says "เก็บเป็นภาพ" for a kept page. A kept page whose text layer could not be trusted is noted "ข้อความในไฟล์ผิด จึงไม่ได้นำมาใช้"; an OCR page keeps "จึงอ่านด้วย OCR".
  - **Statistics** needed no code: pages are counted by kind, and a test shows `kept` among them.
- **The home page**
  - **The control:** two radio cards in a `fieldset` above the drop area, inside the form. Each card is wholly its radio button's label, outside the drop area's.
    - The chosen card is Pale Leaf with a Contract Green line, and the radio's green dot, as the One Green Rule allows.
    - The radios carry `autocomplete="off"`, so a reload does not bring back an earlier choice; `app.js` already resets the form on a page shown from history.
    - DESIGN.md records it, under "Choice above the drop area", with its contrast (Muted Slate on Pale Leaf 6.04:1). PRODUCT.md's first step mentions the choice.
  - **The copy, approved by the user on 2026-10-25:**
    - the option cards;
    - the waiting step;
    - a paragraph and the chip "OCR หรือภาพ" in "อ่านทีละหน้า";
    - a sentence in the placeholders row;
    - a sentence in "จับข้อความในไฟล์ที่ผิด", since a kept scan's wrong text is dropped, not read again;
    - an exception in "เอกสารเดียว ได้สองไฟล์", since with kept images the DOCX shows images where the Markdown shows placeholders.
- **Checked by eye** with `pdf-to-doc-web --dev`, driven in Edge at 1280 and 390 pixels wide:
  - OCR was chosen when the page opened;
  - choosing the other card opened no file picker;
  - a synthetic scan dropped on that card was sent;
  - the steps showed "เก็บภาพหน้า 1/2" with its bar;
  - the table said "เก็บเป็นภาพ";
  - the DOCX downloaded.
  - **Without the script,** the noscript button submits the form with the choice in it. The bot check cannot pass without a script, so that path stops there, as it does today.
- **Checks:**
  - **Windows:** pytest (539 passed) and mypy.
  - **Linux image,** with `src`, `tests`, `corpus`, `scripts` and `pyproject.toml` mounted:
    - mypy;
    - pytest: 540 passed, including the launcher's socket test;
    - `pytest -m ocr`: 15 passed;
    - `pytest -m slow`: 1 passed;
    - the harness: OCR CER 0.0072, unchanged;
    - the CLI with and without `--keep-images`;
    - the sandbox entry point with the variable unset, `0`, `1` and `maybe`. Unset and `0` gave an OCR page, and `1` a kept page. `maybe` exited 1 with no parts.
  - **After the review's changes,** in the Linux image again: mypy, pytest (540 passed), the CLI and the sandbox entry point, with the same results.
- **Code review** (two axes):
  - **Spec, fixed:**
    - the two home-page sentences above;
    - "อาจใช้เวลาหลายนาที" on the OCR card;
    - fake Docker taking `sandbox_config`'s `Env`.
  - **Spec, left:** a summary with kept pages, from a sandbox that was not asked to keep images, is still accepted. It shows as it would, and nothing breaks.
  - **Standards, fixed:**
    - no inset ring on the chosen card;
    - spacing and line heights on DESIGN.md's scale;
    - option titles in the Three Weights Rule;
    - one helper for the setting's value;
    - `reached` instead of two flags;
    - "kept pages" rather than "page images" in names, which clashed with `ocr.PageImage`;
    - `keep_images` passed by keyword;
    - the held sandbox's reports as a tuple;
    - a test helper instead of two `type: ignore`s.
  - **Standards, kept:** `web/docker.py` imports the variable from `pdf_to_doc.sandbox`. The launcher already loads the converter through `web/protocol.py`, so this costs nothing new.
  - **Found outside this ticket:** `--ease: var(--ease)` in `site.css` refers to itself, so no transition or fade has run since ticket 11. The user chose to fix it in a commit of its own on this branch.
