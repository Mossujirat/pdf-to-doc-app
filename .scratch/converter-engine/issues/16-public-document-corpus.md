# 16: Public-document corpus

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What to build:** The committed corpus gains real Thai documents that anyone may redistribute, each with hand-checked reference text. Quality can then be measured on real-world PDFs, not only synthetic ones, without confidential files. The mix covers:

- text-layer PDFs exported from Word
- scanned PDFs
- documents with tables

**Blocked by:** 02

**Status:** ready-for-human

**Branch:** `chore/quality-gate`

**Choosing the documents**
- [ ] Choose 5–10 public Thai documents, for example government announcements, regulations or forms whose terms allow redistribution.
- [ ] Record each document's source URL and licence or terms beside it in the corpus.

**Reference text**
- [ ] For each chosen page, a human checks reference text against the page in the harness's format. A draft from OCR may be used as a starting point, but every character is verified by a person.
- [ ] Include at least two scanned pages and two pages with tables.

**Finishing**
- [ ] Add the documents to the committed corpus, and confirm that the harness runs on them.
