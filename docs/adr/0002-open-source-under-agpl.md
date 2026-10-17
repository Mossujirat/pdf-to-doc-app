# Open source under AGPL-3.0

In our benchmark, PyMuPDF was the most accurate and fastest of seven text-layer extractors on Thai. It also reads the PDF's /ActualText, which pdf.js and pdfminer ignore. PyMuPDF is licensed under AGPL-3.0 or a paid commercial licence, and running it in a public web service under the AGPL means publishing the service's source. We chose to open-source the whole project under AGPL-3.0 rather than buy a licence or settle for a weaker extractor. Publishing the source also lets users check our claim that files are not stored.

## Consequences

- Every dependency must be AGPL-compatible.
- Test files committed to the repo must be public or synthetic. Confidential samples stay local and git-ignored.
