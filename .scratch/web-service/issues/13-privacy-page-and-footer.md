# 13: Privacy page and footer

**Parent:** Web service MVP spec, in this feature folder.

**What to build:** A privacy page in plain Thai (นโยบายความเป็นส่วนตัว) tells a visitor exactly what happens to their file and their data, who runs the service, and how to reach them, as the PDPA requires. Every page gets a footer linking to:
- the source code, at the exact commit the server runs, as the AGPL requires
- the privacy page
- GitHub Issues

**Blocked by:** 11

**Status:** ready-for-agent

**Branch:** `feat/web-design`

**Privacy page**
- [ ] Who runs the service: Sujirat Attawibulkul, as an individual.
- [ ] Contact for personal data: sujirat.attawibulkul@gmail.com. Bugs go to GitHub Issues.
- [ ] What happens to a file:
  - what is received
  - the source file is deleted when its conversion ends
  - the outputs are deleted 10 minutes after it finishes, or on request
  - a restart deletes everything
- [ ] What is not kept or seen:
  - content, file names and IP addresses are never logged
  - IP addresses are held in memory only, for the daily allowance
- [ ] The file travels encrypted to our own server, through no third party.
- [ ] The bot check shows Cloudflare browser data, but never the file.
- [ ] The only cookie is the strictly necessary one. There are no analytics.
- [ ] The visitor's rights under the PDPA, and how to exercise them.

**Footer**
- [ ] The image records the commit it was built from. The footer links to the repository at that commit.
- [ ] Links to the privacy page and to GitHub Issues.

**Tests**
- [ ] The privacy page states the retention times from the service's settings, the operator and the contact.
- [ ] The footer's source link carries the running commit.
