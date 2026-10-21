# 06: Refusal and failure messages

**Parent:** Web service MVP spec, in this feature folder.

**What to build:** Every source file the converter refuses gets a clear Thai message on the web page, in the same words as the CLI, from one shared table. The web adds messages of its own:
- **password-protected PDFs:** not supported yet; remove the password and send the file again
- **a conversion stopped by the time limit**
- **a conversion that failed**

The sandbox's own text is never shown. The web maps each refusal kind to its own message.

**Blocked by:** 03

**Status:** ready-for-agent

**Branch:** `feat/web-core`

**Messages**
- [ ] The refusal messages move into one table that both the CLI and the web use. The CLI's output does not change, and its tests still pass.
- [ ] The web shows a message for every intake refusal:
  - a legacy .doc
  - an Office file locked with a password
  - a file that is neither PDF nor DOCX
  - a DOCX that unpacks to more than 200 MB
  - a file over 50 MB
  - a file over 150 pages
  - a PDF that forbids copying
  - a damaged file
- [ ] A PDF that needs a password gets the web's own message.
- [ ] A failed conversion, and one stopped by the time limit, each get a message that tells the visitor to try again. Neither shows any detail from the sandbox.

**Tests**
- [ ] HTTP tests with the fake sandbox running the real conversion function. They cover every refusal, using the corpus and test builders' files: legacy .doc, locked Office, password-protected and copy-protected PDFs, oversized files, damaged files.
- [ ] A scripted sandbox covers failure and the time limit.
