# 04: Keep outputs within 50 MB

**Parent:** Kept images spec, in this feature folder.

**What to build:** However many scans and pictures a file has, all outputs of one conversion together stay within 50 MB. That is the most the web service takes back from a sandbox. When kept images would pass it, the converter lowers their resolution, only as far as it must, and the summary says to what. A noisy 150-page scan comes to about 42 MB of page images at 150 dpi, so large files will meet the limit.

**Blocked by:** 01, 03

**Status:** done

**Branch:** `feat/kept-images`

**The limit**
- [x] One value, 50 MB for all outputs together, shared by the converter and the sandbox protocol. The protocol's own cap comes from it, so the CLI keeps to the same limit.
- [x] When kept images would pass it, the converter lowers the resolution of kept page images and of pictures, step by step, until the outputs fit.
  - The steps are the implementer's. Take the highest resolution that fits.
  - Lower from the JPEGs it holds, or render again while the PDF is open; the implementer chooses.
  - Show by arithmetic that the lowest step fits the largest source file taken: 150 pages, with pictures.

**The summary**
- [x] The summary records the resolution the images were lowered to. When they were, the headline says so and gives the resolution. That shows in every output, in the CLI's last line and on the web's conversion page.
- [x] The sandbox's summary event carries the resolution, and the web app's schema accepts it, strictly as now. A summary without lowering sends none.

**Tests**
- [x] Push the outputs past the limit, for example with a few large, noisy colour pages. Check that:
  - the outputs fit;
  - the summary gives the lowered resolution;
  - the DOCX images are smaller than 150 dpi.

  If this is too slow for the fast tests, mark it, or run it under the Linux image's checks only.
- [x] A file under the limit keeps 150 dpi and says nothing about resolution.
- [x] A summary event with the resolution passes the web app's schema, and one with a malformed value does not.

**Memory and time** (in the Linux image)
- [x] Convert a 150-page synthetic scan with kept images in a container limited as a sandbox is (4 CPUs, 2 GiB). Read the peak memory from Docker's statistics. It must stay well under 2 GiB; OCR's peak was 1.34 GiB.
- [x] Record the peak, the time per page, and the size of the DOCX in this ticket's Comments.
- [x] pytest, mypy, the harness and the checks in the Linux image all pass.

## Comments

**2026-10-25, implemented on branch `feat/kept-images`**

- **The limit.** `MAX_OUTPUTS` (50 MiB) moved from the web protocol to `intake`, beside the other limits. The converter, the launcher's cap on what a sandbox sends, and the summary's sentence all take it from there.
- **Lowering** (`conversion._within_the_limit`):
  - **When:** the outputs at 150 dpi pass the limit and the document holds kept images.
  - **What:** every kept image, page images and pictures alike, is lowered to one of 120, 100, 85, 72, 60, 50, 40, 30 or 20 dpi. It is re-encoded from the JPEG or PNG held, since the PDF is closed by then.
  - **Checking a step:** whether a step fits is reckoned from the images' bytes, counting each image once, as python-docx stores it once. The rest of the outputs is taken from the first rendering.
  - **Choosing a step:**
    - The first step is guessed by taking JPEG size to go with the square of the resolution.
    - Then it walks up while the next step fits, or down until one does. So the highest step that fits is taken, usually in one or two tries.
    - The step found is rendered and checked, and should it not fit, the next step down is taken.
  - **The 150-dpi outputs are dropped before lowering:** they are as large as the limit or more.
- **The summary:**
  - **Where it is recorded:** `Summary.images_lowered_to` holds the resolution, and so does `Document`, which `summarize` copies it from.
  - **What the headline says:** "ภาพใน DOCX ลดความละเอียดเหลือ N dpi ให้ผลลัพธ์ไม่เกิน 50 MB". It shows in every output, on the CLI's last line and on the web page.
  - **The sandbox's summary event:** the key is left out when nothing was lowered, so every other summary goes out as before. `SummaryEvent` takes a whole number from 1 to below 150, strictly. Tests check that a string, 150 and 0 fail and that 100 finishes.
- **Page images are capped at the size Word shows** (this was not in the spec; recorded there).
  - A page larger than 22 inches a side is rendered at 150 dpi of the size Word shrinks it to, and its `KeptImage` holds that size.
  - Without this, such a page made an image of up to 30,000 pixels a side. In the reviewer's run, lowering then measured resolution against the page's own size: 8 noisy pages of 100 inches came to 54.9 MB at "30 dpi". They now come to 41.9 MB at 120 dpi.
- **A memory leak in PyMuPDF 1.28.2, found and worked around.**
  - **What happened:** a 150-page noisy colour file that needed lowering was killed at 2 GiB. Memory grew by 500–600 MB with each step tried.
  - **The cause, measured in the Linux image:** MuPDF's `fz_scale_pixmap`, behind `Pixmap(pix, w, h, None)`, never frees the scaled copy. That is about 1.5 MB per A4 image, whether called through PyMuPDF or directly, and neither `gc.collect()` nor `TOOLS.store_shrink` frees it. The other constructors used do not leak: colourspace conversion, adding or dropping alpha, decoding, encoding, and `shrink`.
  - **The fix:** images are now resized with numpy, each new pixel the mean of the old ones it covers (`np.add.reduceat`), in `pdf_images._resized`. Masks are resized the same way.
  - **The cost:** about 210 ms for an A4 image, against MuPDF's 19 ms; decoding and encoding take 390 and 260 ms on noise.
- **The lowest step, by arithmetic.**
  - **Kept pages:** at 20 dpi, the largest page Word takes is 440 pixels a side. As pixel-level colour noise, as hard as anything compresses, it is a JPEG of 212 KB (measured), so 150 such pages come to 31 MB.
  - **A rejected arithmetic:** the reviewer measured pixel noise at 30 dpi at 70 MB for 150 such pages, against the 8 MB first written here from noise averaged down. Hence the added 20 dpi step.
  - **Pictures:** a picture is never sharper than the source file holds it, and the source is at most 50 MB.
  - **The case left over:** a source built of many overlapping pictures of noise, already stored at 20 dpi or less, could in principle still pass the limit at the lowest step. On the web the conversion then fails, as any oversized output does today. The CLI writes the files anyway. No real file is expected to come near it.
- **Memory and time, in the Linux image limited as a sandbox (4 CPUs, 2 GiB, no swap):**

  | File | Peak | Time | DOCX |
  |---|---|---|---|
  | 150-page synthetic grey scan, 48.6 MB source, no lowering needed | 462 MB | 54 s (0.36 s a page) | 43 MB |
  | 150 noisy colour A4 pages, 38.7 MB source, lowered to 60 dpi (after trying 72) | 679 MB | 196 s | 41 MB |

  In the second file, the 150-dpi rendering of 209 MB is the peak, and memory stays flat while lowering. Both stay well under 2 GiB; OCR's peak was 1.34 GiB.
- **The 50 MB test is marked `slow`** (about 50 s). The default `pytest` leaves it out. CI runs it as `pytest -m slow`, and CLAUDE.md says so.
- **`pdf_builder`'s `Pasted`** gains `noise_pixels` and `seed`, a scan of colour noise. Each seed gives its own, so python-docx does not store one image for all pages.
- **Checks:**
  - **Default output:** the same as `main` on the 17 corpus PDFs: Markdown byte for byte, and DOCX except `docProps/core.xml`.
  - **Corpus:** regenerating it leaves every committed file unchanged.
  - **Windows:** pytest and mypy.
  - **Linux image:**
    - mypy;
    - pytest;
    - `pytest -m ocr`;
    - `pytest -m slow`;
    - the harness: OCR CER 0.0072, unchanged;
    - the CLI;
    - the sandbox entry point.
- **Code review** (two axes):
  - **Spec, fixed:**
    - the lowering against the wrong size for pages over 22 inches;
    - the wrong lowest-step arithmetic, and the 20 dpi step added;
    - this Comments section.
  - **Spec, left:** no test runs the CLI past the limit. The CLI prints the same headline, and existing tests cover that it prints it; another such test would add a minute to the slow tests.
  - **Standards, fixed:**
    - the bound in `SummaryEvent` taken from `KEPT_DPI`;
    - `_MB` in the summary;
    - one helper for the images' bytes and one for lowering them all;
    - names: `lowered_images`, `replacements`, `noise_pixels`;
    - the sandbox comment now says why;
    - `with_kept_images` uses `replace`;
    - `LARGEST_PAGE` in the test;
    - the slow test named "lowered".
  - **Standards, kept as they are:**
    - `LARGEST_PAGE` in the model, as both the page images and the DOCX need it;
    - the output limit in `intake`, beside the other limits, its docstring updated.

