# 05: Choose kept images on the web

**Parent:** Kept images spec, in this feature folder.

**What to build:**
- **Choosing:** on the home page, a visitor chooses OCR or kept images above the drop area, before a dropped file starts converting.
- **Plumbing:** the choice goes with the file from the web app through the launcher to the sandbox, checked as untrusted at each step.
- **Following it:** while the file converts, its page shows a step for the page images. Once it has finished, the page shows which pages were kept.
- **The home page** explains both options truthfully.

**Blocked by:** 01

**Status:** ready-for-agent

**Branch:** `feat/kept-images-web`

**From the form to the sandbox**
- [ ] **The form:** the choice is a field inside the upload form, so it goes with a dropped or picked file.
  - Missing, it means OCR, as from a page loaded before this change.
  - Any other value is refused as not an upload.
- [ ] **The conversion** holds the setting while it waits or runs.
- [ ] **The launcher:** the web app sends it the setting with the source file, in the frame that starts the conversion.
  - The launcher reads it as untrusted, like every frame: anything but the two values breaks the frames.
  - The frame's shape is the implementer's.
- [ ] **Docker:** the launcher creates the sandbox with `PDF_TO_DOC_KEEP_IMAGES` set. Nothing else in the sandbox's configuration changes (ADR 0004).
- [ ] **The sandbox entry point** reads that variable, its second setting beside the OCR thread count. Its run function takes the setting as a parameter, for tests.
- [ ] **The local sandbox,** for development, sets the same variable on its process.
- [ ] **Event lines** still carry none of the file's content.

**The home page**
- [ ] **The control:** two options above the drop area.
  - OCR is selected whenever the page opens, and the choice is not remembered.
  - It works without a script, through the noscript button.
  - It works at phone width.
  - Choosing an option never opens the file picker, and dropping a file anywhere on the form still sends it.
- [ ] **Design:** made with the impeccable skill, inheriting DESIGN.md and PRODUCT.md, including the One Green Rule. DESIGN.md records the new control.
- [ ] **Copy:**
  - The step about waiting in "แปลงอย่างไร" says scans take minutes with OCR. It now mentions the option.
  - In "ข้างในทำอะไรกับไฟล์ของคุณ", reading page by page shows the kept-images option.
  - The placeholders paragraph says pictures show as themselves in the DOCX when images are kept.
  - The examples stay made up.

**The conversion's page**
- [ ] **The page images step:** a step, "เก็บหน้าสแกนเป็นภาพ", with its page count and progress bar.
  - It shows only when kept images was chosen.
  - It is marked as not needed when no page was kept.
  - Without kept images, the steps are as today.
- [ ] **The finished table:** its "อ่านจาก" column says "เก็บเป็นภาพ" for kept pages. The headline shows kept pages from the summary.
- [ ] **Statistics** count kept pages among pages by kind.
- [ ] **The privacy page** is unchanged. Outputs are still held in memory, and deleted within 10 minutes or when the visitor deletes them.

**Tests**
- [ ] **The web app with a fake sandbox:**
  - the setting reaches the sandbox for each option, and for a missing field;
  - another value is refused.
- [ ] **The launcher with fake Docker:**
  - the setting reaches the sandbox's environment;
  - a frame with a bad setting is refused.

  Run the launcher's socket tests in the Linux image.
- [ ] **The sandbox's run function** with the setting on and off. The local sandbox passes it too.
- [ ] **The home page:** the control sits inside the upload form, with OCR selected. The copy changes.
- [ ] **The conversion's page:** the page images step, waiting, running and skipped, and the finished table with kept pages.
- [ ] **Statistics** with kept pages.
- [ ] **Checked by eye** with `pdf-to-doc-web --dev` and a synthetic scan, at desktop and phone width:
  - choose kept images;
  - drop the file;
  - follow the steps;
  - download the DOCX.
- [ ] pytest, mypy, and the checks in the Linux image all pass.
