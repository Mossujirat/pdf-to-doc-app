# 41: Text beside other text on the same rows, in the body's own type, is read across

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What goes wrong:** On OCR pages, and on text pages drawn line by line across, a narrow panel set beside a letter in the letter's own type, such as the sender's offices and bank details, is joined line by line with the letter. An account or registry number lands in the letter's sentences. Nothing marks it.

**Blocked by:** none

**Status:** needs-info

**Split from:** ticket 32, on 2026-11-04. Ticket 32 reads a panel set in smaller type after the body beside it: its lines do not share the body's baselines, as labels beside their values do. A panel in the body's own type shares them, so it looks like labels and values set apart, and the column finder keeps it row by row.

**What is known so far**
- **The test fixture** "a letter with a panel of addresses in its own type" in `tests/test_ocr_pages.py` pins today's reading, row by row.
- **On the samples,** both side panels seen were in smaller type (the GIZ supplement's letter and the 110-page contract's privacy notice), and ticket 32 reads them.
- **Cues not yet tried:** the panel's lines are much shorter than the body's on every row; the panel sits at the page's edge and runs down more lines than any label column; the body's lines read as sentences that run on from row to row.

**To decide at triage**
- Whether a sample shows this layout at all, before building for it.
- Which cue separates it from labels and values, measured on the label–value fixtures.

## Comments

**2026-11-11, triage (grilled with the user, together with ticket 39)**

- **Widened:** this ticket now covers any text set beside other text in the body's own type on the same rows, every line sharing a baseline with the text beside it. That is a side panel in the body's own type, and bank details paired with signatories line by line, as in ticket 39's first fixture ("bank details beside the signatories" in `tests/test_ocr_pages.py`). Ticket 39 now covers only blocks that keep their own rows.
- **Why it waits:** on the same rows, box positions alone cannot tell these layouts from labels and values, which must stay row by row (ticket 18). It needs a cue from the text instead, such as the body's sentences running on from row to row. None of the four samples in `docs/example_pdf/` shows the layout: their side panels are set in smaller type, and their bank details keep their own rows.
- **Wanted to go on:** a real file that shows the layout, to measure a cue on.
- **The known limitation** points to this ticket alone once ticket 39 closes. Wording agreed with the user, to finalize at the deploy: "แถบข้อความข้างจดหมาย หรือรายละเอียดบัญชีข้างรายชื่อผู้ลงนาม ที่ตัวอักษรขนาดเท่าเนื้อความและเรียงบรรทัดตรงกับข้อความข้างๆ บนหน้าสแกน ยังถูกอ่านปนกัน เลขบัญชีอาจไปอยู่ผิดที่".
