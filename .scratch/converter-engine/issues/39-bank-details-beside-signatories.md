# 39: Bank details beside a list of signatories are read across

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What goes wrong:** On OCR pages and on text pages drawn line by line across, bank details set beside a list of signatories are joined line by line with it. An account number can land beside the wrong name. Nothing marks it.

**Blocked by:** none

**Status:** needs-triage

**Split from:** ticket 32, on 2026-11-03, in triage. Ticket 32 keeps side panels and signature blocks side by side, which each have a cue. This layout has none yet.

**What is known so far** (ticket 32, synthetic pages)
- **Today's CER:** 0.36 on a scan, 0.56 on a text page drawn across.
- **Neither of ticket 32's cues covers it.** Both sides are set in the same type on the same rows, so their lines pair as fully as a label–value list's, and no signing word repeats on a row.
- **It looks like a label–value list with a second list beside it,** which the column finder's guard rightly keeps whole.

**To decide at triage**
- A cue that tells it from a label–value list, if there is one.
- Whether it is a known limitation of its own on the what's-new page.

## Comments

**2026-11-04, from ticket 32**

- **A known limitation,** together with ticket 41, worded with the user: "แถบข้อความข้างจดหมายที่ตัวอักษรขนาดเท่าเนื้อความ และเลขบัญชีที่วางข้างรายชื่อผู้ลงนาม บนหน้าสแกน ยังถูกอ่านปนกับข้อความข้างๆ เลขบัญชีอาจไปอยู่ผิดที่".
