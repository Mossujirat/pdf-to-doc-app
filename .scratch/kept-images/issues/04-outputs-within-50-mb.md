# 04: Keep outputs within 50 MB

**Parent:** Kept images spec, in this feature folder.

**What to build:** However many scans and pictures a file has, all outputs of one conversion together stay within 50 MB. That is the most the web service takes back from a sandbox. When kept images would pass it, the converter lowers their resolution, only as far as it must, and the summary says to what. A noisy 150-page scan comes to about 42 MB of page images at 150 dpi, so large files will meet the limit.

**Blocked by:** 01, 03

**Status:** ready-for-agent

**Branch:** `feat/kept-images`

**The limit**
- [ ] One value, 50 MB for all outputs together, shared by the converter and the sandbox protocol. The protocol's own cap comes from it, so the CLI keeps to the same limit.
- [ ] When kept images would pass it, the converter lowers the resolution of kept page images and of pictures, step by step, until the outputs fit.
  - The steps are the implementer's. Take the highest resolution that fits.
  - Lower from the JPEGs it holds, or render again while the PDF is open; the implementer chooses.
  - Show by arithmetic that the lowest step fits the largest source file taken: 150 pages, with pictures.

**The summary**
- [ ] The summary records the resolution the images were lowered to. When they were, the headline says so and gives the resolution. That shows in every output, in the CLI's last line and on the web's conversion page.
- [ ] The sandbox's summary event carries the resolution, and the web app's schema accepts it, strictly as now. A summary without lowering sends none.

**Tests**
- [ ] Push the outputs past the limit, for example with a few large, noisy colour pages. Check that:
  - the outputs fit;
  - the summary gives the lowered resolution;
  - the DOCX images are smaller than 150 dpi.

  If this is too slow for the fast tests, mark it, or run it under the Linux image's checks only.
- [ ] A file under the limit keeps 150 dpi and says nothing about resolution.
- [ ] A summary event with the resolution passes the web app's schema, and one with a malformed value does not.

**Memory and time** (in the Linux image)
- [ ] Convert a 150-page synthetic scan with kept images in a container limited as a sandbox is (4 CPUs, 2 GiB). Read the peak memory from Docker's statistics. It must stay well under 2 GiB; OCR's peak was 1.34 GiB.
- [ ] Record the peak, the time per page, and the size of the DOCX in this ticket's Comments.
- [ ] pytest, mypy, the harness and the checks in the Linux image all pass.
