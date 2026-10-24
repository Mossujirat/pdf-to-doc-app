# 29: Sideways text inside upright pages is lost

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What goes wrong:** Some upright pages hold a little text printed a quarter turn, such as column headers set sideways to keep a table's columns narrow. On a scan, OCR reads that text as junk. It is marked uncertain, but its words are lost.

**Blocked by:** none

**Status:** needs-triage

**Seen on:** a 110-page Thai contract among the local samples in `docs/example_pdf/`, converted on 2026-10-23 with the user's permission. Upright tables on its scans have sideways column headers, and they came out as marked junk.

**What is known so far**
- **Split out of ticket 21.** That ticket turns a page whose whole content is sideways. These pages stay upright, rightly: on a synthetic upright table with sideways headers, the tall boxes held 0.12 of the text area, against 0.85 or more on a sideways page.
- **How PaddleOCR reads such text:** it turns every crop at least 1.5 times as tall as wide a quarter turn counter-clockwise before reading it. So headers turned clockwise may already read right, while headers turned the other way read upside down.
- **The same thing in a text layer has not been seen** in the samples: a text page whose rows run sideways. `text_rows` would make tall rows of it.

**To decide at triage**
- Whether to read each tall crop both ways and keep the better reading, and what that costs on pages with many tall boxes.
- Where the headers' text goes once read: into the table's header row, which needs ticket 14, or as a line before the table.
- Whether the text-layer case belongs here, or waits until a sample shows it.
