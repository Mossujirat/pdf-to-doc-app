# 38: Signatures, stamps and pictures inside scans are lost

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What goes wrong:** On a scan read with OCR, signatures, stamps, logos, QR codes and photos are part of the page image. OCR reads them as junk text, marked uncertain, or they vanish. No placeholder stands for them, so the Markdown of a signed contract never says it was signed.

**Blocked by:** none

**Status:** needs-triage

**Seen on:** a 110-page Thai contract among the local samples in `docs/example_pdf/`, converted on 2026-10-23 with the user's permission. None of its 91 OCR pages has a placeholder; its only placeholders are on two text pages. That follows the spec, which gives OCR pages no placeholders on the grounds that they are images themselves.

**Split from:** ticket 24, on 2026-11-03, in triage. Ticket 24 keeps the pictures that are separate images in the PDF, on OCR pages that are not scans: the text-page placeholder rules can serve them. Finding a picture inside a page image takes image analysis, so it is a ticket of its own.

**To decide at triage**
- How to find a signature, a stamp or a picture in the page image, and tell it from text and table rules.
- Which placeholder kinds it can tell apart, and when it is unsure.
- Whether its ink is blanked before OCR reads the page.

## Comments
