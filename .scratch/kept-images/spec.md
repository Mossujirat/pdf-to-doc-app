# Kept images

Status: ready-for-agent

## Problem Statement

People who convert a scanned or signed document to DOCX often want a Word file that looks like the original, not a transcript of it. Today they cannot get one:

- **Scans are read with OCR, always.** On the DOCX, each scan becomes OCR text. That text loses:
  - highlights and ink drawn on the page;
  - stamps, signatures and logos inside the scan;
  - the look of forms and tables.

  It can also hold misreads. They are marked as uncertain text, but they are still not what the page says.
- **Pictures on text pages become placeholders,** in the DOCX as well as the Markdown. The DOCX of a signed contract shows `[ลายเซ็น]` where the signature was, and `[รูปภาพ]` in place of a chart or a photo.
- **OCR is slow.** It takes about 6 seconds a page, so a 150-page scan takes about 15 minutes. Someone who only wants the scans in Word waits for text they do not need.

A typical case is the contract with scanned attachments that someone has highlighted and annotated before passing it on. The person who needs it in Word wants the pages as they are, highlights and notes included.

## Solution

A conversion setting, **kept images**, chosen once for the whole source file. There are two options:

- **OCR (the default):** scans are read with OCR, as today.
- **Kept images:** the converter keeps scans and pictures as images.
  - **In the DOCX:** each scan is the page as it looks, highlights and notes included, edge to edge. Each picture on a text page is the picture itself, where its placeholder would be.
  - **In the Markdown:** a scan becomes a `[หน้าสแกน]` placeholder. Any trustworthy text the source file already holds on that page follows it, such as a typed note, or the hidden text of a searchable scan. Pictures keep today's placeholders.
  - **What it changes:** only scans and pictures. A page with text drawn as shapes, or a text page whose text layer cannot be trusted, is still read with OCR.

The purpose is a DOCX that looks like the original. Speed is not the goal, though kept scans skip OCR and so convert much faster.

There is no option for both images and OCR text. The command line takes `--keep-images`. The web page shows the two options above the drop area, because a dropped file starts converting at once.

## User Stories

1. As a document user, I want to choose to keep scans as images, so that my DOCX looks like the original instead of holding OCR text.
2. As a document user, I want OCR to stay the default, so that nothing changes unless I ask for it.
3. As a document user, I want to make the choice once for the whole file, so that I don't decide page by page.
4. As a document user, I want each scan in the DOCX to show the whole page as it looks in the original, so that nothing on it is lost or changed.
5. As a document user, I want highlights, ink and typed notes on a scan to show in the DOCX, so that I can see what someone marked before passing it on.
6. As a document user, I want stamps, signatures and logos inside a scan to show in the DOCX, so that the Word file proves the document was signed and stamped.
7. As a document user, I want each scan to fill its Word page from edge to edge, so that it looks like the printed page and not like a picture pasted into a margin.
8. As a document user, I want a scan's Word page to face the same way as the original page, landscape or portrait, so that wide pages are not squeezed onto a tall one.
9. As a document user, I want a sideways page kept as it is, so that it looks as it does in the original.
10. As a document user, I want each page of the original to take exactly one Word page, with no blank pages between scans, so that the page count matches the original.
11. As a document user, I want text pages in the same DOCX to stay editable text with normal margins, so that I can still edit the parts that were typed.
12. As a document user, I want a picture on a text page to appear as the picture itself, where its placeholder would be, so that charts, photos and logos stay in the document.
13. As a document user, I want signatures and stamps on text pages to appear as themselves in the DOCX, so that the Word file shows who signed.
14. As a document user, I want a picture to keep its size on the page, shrunk only when it is wider or taller than the text area, so that it does not spill off the Word page.
15. As a document user, I want pictures with a transparent ground, such as a signature pasted over a line, to stay transparent, so that they do not cover the text around them with a white box.
16. As a document user, I want pictures on a rotated page to stand upright, as they do in the original, so that they are not shown on their side.
17. As a document user, I want logos repeated at the edge of every page left out, as they are today, so that the DOCX does not repeat page furniture.
18. As a document user, I want a background image behind a text page's text left out, as it is today, so that the text stays editable and readable.
19. As a document user, I want a searchable scan, one with its text hidden behind the picture, kept as an image too, so that it looks like the original like any other scan.
20. As a document user, I want a page whose visible text lies over a background image to stay a text page, so that letterheads with a picture behind them still give editable text.
21. As a document user, I want a page whose text is drawn as shapes still read with OCR, so that I still get its text, as it is not a scan.
22. As a document user, I want a text page whose text layer is wrong still read with OCR, so that I still get the right text.
23. As a document user, I want a scan whose hidden text is wrong kept as an image without that text, so that the DOCX looks like the original and the Markdown never passes on wrong text.
24. As a document user, I want the Markdown to say `[หน้าสแกน]` where a scan was kept, so that the AI chat and I know a page was there.
25. As a document user, I want text the file already holds on a scan, such as a typed note or the hidden text of a searchable scan, to follow the placeholder in the Markdown, so that the AI still gets what can be read without OCR.
26. As a document user, I want headers and footers repeated over scans left out of the Markdown, as they are on other pages, so that they do not waste AI tokens.
27. As a document user, I want pictures in the Markdown to keep today's placeholders, so that the Markdown is the same plain text an AI chat reads well.
28. As a document user, I want the summary to say how many pages were kept as images, and which, so that I know which pages hold no text in the DOCX.
29. As a document user, I want a summary without kept pages to read exactly as it does today, so that the default output does not change.
30. As a document user, I want the outputs to stay within 50 MB, even for 150 scanned pages, so that the web service can return them and my mail can carry them.
31. As a document user, I want the converter to lower the images' resolution only when it must, and only as far as it must, so that pages stay as sharp as they can.
32. As a document user, I want the summary to say when the images' resolution was lowered, and to what, so that I know why the pages look less sharp.
33. As a document user, I want to see progress while the page images are made, as I see it for OCR, so that I know the conversion is moving.
34. As a document user on the web, I want the two options above the drop area, so that I can choose before a dropped file starts converting.
35. As a document user on the web, I want OCR selected each time the page opens, so that I never keep images by accident.
36. As a document user on the web, I want to choose an option without opening the file picker, so that choosing and dropping stay separate actions.
37. As a document user on the web, I want the choice to work at phone width and without a script, so that every browser can use it.
38. As a document user on the web, I want the conversion's steps to show a step for the page images, so that I can follow it as I follow OCR.
39. As a document user on the web, I want the finished conversion's table to say which pages were kept as images, so that I can see it page by page.
40. As a document user on the web, I want the home page's "how it works" section to explain both options truthfully, so that I know what each one does before I choose.
41. As a document user on the command line, I want a `--keep-images` option, so that I can keep images without the web service.
42. As a document user, I want the setting to make no difference to a DOCX source, so that the setting never changes what I get from a Word file.
43. As a document user, I want a file of scans kept as images to convert in a fraction of OCR's time, so that I don't wait for text I did not ask for.
44. As an operator, I want the web app to stop taking new files while too many large outputs are held, so that it never runs short of memory on the server it shares with Chatbot.
45. As an operator, I want the memory cap set in the environment, so that I can tune it without changing code.
46. As an operator, I want uploads refused by the cap counted apart from a full queue, so that I can tell which limit people meet.
47. As an operator, I want the statistics to count kept pages as a page kind, so that I can see how much the setting is used.
48. As a developer, I want the setting passed from the web app through the launcher to the sandbox as untrusted data, checked at each step, so that it cannot be used to change how a sandbox runs.
49. As a developer, I want kept images rendered from the same document model as everything else, so that both outputs agree about what each page holds (ADR 0003).
50. As a developer, I want the conversion with kept images tested through the conversion function with synthetic PDFs, so that the tests describe what users see.
51. As a maintainer, I want the corpus and the quality harness to give the same results as before, so that I know the default path did not change.
52. As a maintainer, I want the peak memory of a 150-page conversion with kept images measured in the sandbox's image, so that I know it fits the 2 GiB limit.

## Implementation Decisions

### The setting

- **The conversion function takes a `keep_images` flag, off by default.**
  - With it off, every output is the same, byte for byte, as without this feature.
  - The CLI's flag is `--keep-images`.
  - It is chosen once per source file. It has no effect on a DOCX source.
- **Only scans and pictures on text pages change.** Pages whose text is drawn as shapes, and text pages whose text layer cannot be trusted, are read with OCR either way. Pictures on OCR pages stay out of scope (ticket 24).

### Which pages are kept

The converter first reads each page as it does today: the text layer's rows, the text-layer check, and the test for whether a page needs OCR. With kept images on, a page is a **kept page** when it is a scan:

- **A scan.** The page needs OCR, by today's test or because its text layer cannot be trusted, and its images together cover most of the page's body, outside the edge bands.
  - A page whose text is drawn as shapes has no such picture, so it is still read with OCR.
  - The exact share is the implementer's. Set it on synthetic pages, then check it on the samples during /implement if the user allows.
- **A searchable scan.** By today's rule it is a text page, read from its text layer, but that text is hidden: drawn before an image that covers it, or drawn invisible.
  - PyMuPDF's bounding-box log records what the page draws, in order. It shows text drawn under an image (`fill-text` before `fill-image`) and invisible text (`ignore-text`). Checked on synthetic pages with PyMuPDF 1.28.2.
  - A page whose visible text lies over a background image, such as a letterhead, stays a text page.
- **A scan whose text layer cannot be trusted is still kept** (decided with the user on 2026-10-24). Its text layer passes on nothing, as an untrusted text layer passes nothing on OCR pages today. The Markdown then gets the placeholder alone.
- **What is not kept.** Untrusted text layers on pages that are not scans, such as a font that turns "การ" into "กำร", are read with OCR as today.
- **Kept pages are never given to the OCR engine.** A file whose OCR pages are all kept never loads it.
- **What was checked with PyMuPDF 1.28.2 on synthetic pages:**
  - A typed note made as a FreeText annotation comes through the text layer.
  - A render includes annotations.

### Document model

- **A third page kind, `kept`,** beside text pages and OCR pages (glossary: Kept page).
- **A kept page's blocks:**
  - It opens with a placeholder of a new kind, scan, labelled `หน้าสแกน`, which carries the page image.
  - The blocks from its trusted text layer follow. Page furniture is removed across the document as usual.
  - Page layout treats them as it treats an OCR page's rows: no headings, and they do not count towards the document's body size. The font sizes of hidden text are whatever the scanner's software set.
- **Pictures on text pages.** Their placeholders (image, signature, stamp) carry the picture when kept images is on, and nothing when it is off.
- **A carried image is compressed bytes,** never raw pixels:
  - JPEG, or PNG where it has transparency;
  - with the size it is shown at on the page, in points.
- **Both renderers read the same model** (ADR 0003): the Markdown writes the placeholder's label, and the DOCX writes its image.

### Page images and pictures

- **A kept page's image:**
  - It shows the page as it is shown: rotation applied, and annotations included (highlights, ink, notes).
  - It is rendered in RGB at 150 dpi and encoded as JPEG at once. The raw pixmap is dropped straight away.
  - The JPEG quality is the implementer's. On a noisy synthetic A4 scan, quality 75 gave 280 KB in 0.3 s. The real sample averaged about 190 KB a page at 150 dpi.
- **A picture on a text page is the image object itself,** not a crop of the page:
  - nothing drawn over or under it is included;
  - its soft mask becomes transparency;
  - it is turned and flipped as it is shown on the page, so a picture on a rotated page stands upright (ticket 19);
  - its resolution is at most 150 dpi at the size it is placed;
  - other colour spaces, such as CMYK, are converted to RGB.
- **Pictures that get no placeholder today are not kept either:** images too small to be pictures, images behind text, and images repeated at an edge (ticket 09's rules).

### DOCX renderer

- **Text pages are unchanged:** A4, 2.54 cm margins, editable text.
- **Each kept page is a Word section of its own:**
  - It has the size and orientation of the original page as shown, and no margins.
  - The page image fills it from edge to edge.
  - Word allows at most 22 inches a side, so a larger page is scaled down to fit, keeping its shape.
  - The section after it returns to A4 with normal margins.
- **A kept page holds only its image.** The image shows its text, so the DOCX holds none for that page, and Word cannot search it. This follows from the grilling's decision.
- **One Word page per kept page, and no blank pages.**
  - python-docx adds a section break in a new empty paragraph. After an image as tall as the page, that paragraph falls onto a page of its own and leaves a blank page.
  - The break must be carried so that this cannot happen. Check it in real Word.
- **The summary stays the first paragraph,** on an A4 page. When page 1 is kept, the summary has the first Word page to itself.
- **A picture on a text page** sits in its own paragraph, where its placeholder would be. It keeps the size it is placed at, shrunk to the text area if it is larger.
- **Uncertain text** is still highlighted yellow.

### Markdown renderer

- **A kept page:** its page marker, then `[หน้าสแกน]`, then its text.
- **Pictures** keep today's placeholders.
- **No images** are embedded in the Markdown.

### Output size

- **The limit is 50 MB for all outputs together.**
  - It is the most the web service takes back from a sandbox.
  - The converter and the sandbox protocol share it as one value, so the CLI keeps to it too.
- **When kept images would pass it, the converter lowers their resolution step by step until the outputs fit.**
  - This covers kept page images and pictures alike.
  - The steps are the implementer's. Take the highest resolution that fits.
  - The lowest step must fit the largest source file taken (150 pages); confirm it by arithmetic.
  - A noisy 150-page scan at 150 dpi comes to about 42 MB of images, so the limit will be met in practice.
- **The summary records the resolution** the images were lowered to.

### Summary

- **Kept pages are counted:** "เก็บเป็นภาพ N หน้า ได้แก่หน้า …".
  - The sentence shows only when there are kept pages. The headline of a conversion with none is unchanged.
  - The scan placeholder is not counted among placeholders: the page count already says it.
- **When the resolution was lowered,** the headline says so and gives the resolution. Every output carries the note, and so do the CLI's last line and the web page.
- **The sandbox's summary event** carries the new page kind and the resolution. The web app's schema accepts both, strictly as now.

### Progress

- **A new progress stage for the page images,** with a current and total count, as OCR has.
  - Its place among reading, OCR and writing is the implementer's. The web's steps follow it.
- **The CLI** prints one line per page image, as it does per OCR page.
- **The web's steps:**
  - There is a step for the page images, "เก็บหน้าสแกนเป็นภาพ", with its page count and progress bar.
  - It is shown only when kept images was chosen, and marked as not needed when no page was kept.
  - Without kept images, the steps are as today.

### CLI

- **`--keep-images`,** with Thai help text that says:
  - scans and pictures stay images in the DOCX instead of being read with OCR;
  - the Markdown gets `[หน้าสแกน]`.
- **The README** documents it.

### Sandbox entry point, launcher and Docker

- **The sandbox entry point** reads the setting from `PDF_TO_DOC_KEEP_IMAGES` in its environment. It is its second setting, beside the OCR thread count. Its run function takes the setting as a parameter, for tests.
- **The web app sends the setting to the launcher** with the source file, in the frame that starts the conversion.
  - The launcher reads it as untrusted, like every frame: anything but the two values breaks the frames.
  - The frame's exact shape is the implementer's.
- **The launcher's Docker engine creates the sandbox with the variable set.** Nothing else in the sandbox's configuration changes (ADR 0004).
- **The local sandbox,** for development, sets the same variable on its process.
- **Event lines still carry none of the file's content.**

### Web app

- **The control:**
  - Two options above the drop area, inside the upload form, so that the choice goes with a dropped or picked file.
  - OCR is selected whenever the page opens, and the choice is not remembered.
  - It works without a script, through the noscript button.
- **The form field:**
  - Missing, it means OCR, as from a page loaded before this change.
  - Any other value is refused as not an upload.
- **Design:**
  - Use the impeccable skill, inheriting DESIGN.md and PRODUCT.md, including the One Green Rule.
  - It must work at phone width.
  - Choosing an option never opens the file picker, and dropping a file anywhere on the form still sends it.
  - DESIGN.md records the new control.
- **Copy on the home page.** The "how it works" step about waiting says that OCR on scans takes minutes; it now mentions the option. The section "ข้างในทำอะไรกับไฟล์ของคุณ" changes in the same ticket, as its rule requires:
  - reading page by page shows the kept-images option;
  - the placeholders paragraph says pictures show as themselves in the DOCX when images are kept.

  The examples stay made up.
- **The conversion's page:**
  - the step for the page images;
  - "เก็บเป็นภาพ" in the "อ่านจาก" column of the finished table;
  - kept pages in the headline.

  A conversion holds the setting while it waits or runs, but none of the file's content beyond what it holds today.
- **The cap on held outputs** (decided with the user on 2026-10-24):
  - A new setting, `max_held_outputs`, in bytes, 1 GB by default, set through `PDF_TO_DOC_MAX_HELD_OUTPUTS`.
  - When the outputs held by ended conversions total the cap or more, a new upload gets the "คิวเต็ม" page until older outputs expire or are deleted.
  - Running conversions may add up to their own outputs on top, which is the headroom.
  - The statistics count these refusals under a kind of their own.
- **Statistics** count kept pages among pages by kind. The counter already counts by kind.
- **The privacy page** needs no change. Outputs are still held in memory, and deleted within 10 minutes or when the visitor deletes them.

### Memory and time

- **Memory:**
  - The sandbox has 2 GiB. A 150-page conversion with OCR peaked at 1.34 GiB.
  - With kept images, each kept page holds only its JPEG. 150 pages come to 30–42 MB, held in the model and again in the DOCX while it is written.
  - Raw pixmaps are never kept beyond the page being encoded.
- **Time:** making a kept page's image takes about 0.3 s, against about 6 s to read a page with OCR. The 30-minute time limit and the daily page allowance are unchanged.

### Glossary

**Kept page** is added to `GLOSSARY.md`, and **Kept images** and **OCR page** are narrowed to match the decisions above.

## Testing Decisions

- **Seams, confirmed with the user on 2026-10-24: only existing ones.**
  - **The conversion function** tests the feature's behaviour, with synthetic PDFs and the fake OCR engine.
  - **The existing outer seams** test the plumbing: the CLI's main function, the sandbox's run function, the launcher with fake Docker, and the web app with a fake sandbox.
  - No new seam is added.
- **A good test** converts a real synthetic source file and asserts only on what a user sees:
  - the DOCX read back: sections, page size, orientation and margins, pictures and their sizes, no text on kept pages, text pages on A4;
  - the Markdown's text;
  - the summary.

  It never asserts on internal structures, intermediate images or which helper ran.
- **The fake OCR engine** shows whether a page was read: it records every image it is given. Tests confirm two things:
  - a kept page is never read;
  - a page whose text is drawn as shapes, and a text page with a broken text layer, are still read.
- **`pdf_builder` needs new pages:**
  - a searchable scan, with its text invisible and with its text under the image;
  - a page whose text is drawn as shapes;
  - a scan with a highlight annotation, to check the kept image shows it;
  - a picture with transparency on a rotated page.
- **Output size:** at least one test pushes the outputs past the limit and checks two things: the outputs fit, and the summary gives the lowered resolution.
  - The test may use a few large, noisy colour pages.
  - If that is too slow for the fast tests, mark it, or run it under the Linux image's checks only.
- **The default path is unchanged:**
  - every existing test passes unchanged;
  - the corpus and `pdf-to-doc-eval` give the same results;
  - CI's conversion steps pass.
- **Real Word,** once, on a synthetic DOCX with kept images. Automated checks cannot see this. Check that:
  - kept pages are edge to edge;
  - each takes one Word page, with no blank page;
  - landscape pages are landscape;
  - pictures stand upright and stay transparent.
- **Memory:** convert a 150-page synthetic scan with kept images in the Linux image, and read the peak from Docker's statistics. It must stay well under 2 GiB.
- **Final check on the local samples,** only with the user's permission, asked for at /implement:
  - convert the supplement and the 110-page contract with kept images on this machine;
  - look at the DOCX in Word.

  Nothing of them is committed or put in a ticket, and the output is deleted after.
- **Prior art:**
  - placeholder tests for pictures on text pages;
  - DOCX output tests, with the test DOCX reader;
  - OCR page tests with the fake engine, including rotated and sideways pages;
  - the outputs-and-progress tests;
  - sandbox tests;
  - launcher tests, with fake Docker;
  - the web app's home, pages, queue and statistics tests.

## Out of Scope

- An option that gives both images and OCR text, for the same page or file.
- Images in the Markdown output.
- **Other tickets** stay as they are, unless the user decides to bring one in:
  - converter tickets 14–17;
  - 20: highlights and notes on text pages;
  - 22: page furniture on scans;
  - 23;
  - 24: pictures on OCR pages that are not scans;
  - 25–32.
- Remembering the web visitor's choice between visits.
- Changing the time limit, the page allowance or the 150-page and 50 MB intake limits.
- Accurate mode (ticket 15). It does not touch kept pages, which are not read with OCR.
- **Deploying.** `main` is ahead of production. Nothing is deployed until the user says so.

## Further Notes

- **Where the decisions come from:**
  - Grilled with the user on 2026-10-22.
  - Checked against the code on 2026-10-24: `main` at 98d187e, with tickets 19, 21 and 18 merged since the grilling.
  - The questions settled on 2026-10-24 are noted where they apply: untrusted scans, the cap on held outputs, and the seams.
- **Code that changed since the grilling, and what it means here:**
  - OCR pages are now turned upright when sideways (ticket 21), and read column by column (ticket 18). Both happen inside OCR reading, which kept pages never reach.
  - The text layer is read on the page as shown (ticket 19). Kept page images and pictures on rotated pages rely on it.
- **The "ข้างในทำอะไรกับไฟล์ของคุณ" section** (`src/pdf_to_doc/web/pages.py`) states the converter's rules as they are. The ticket that changes the rules changes the section.
- **Delivery.** The tickets are in `issues/`. Each ticket is a commit on its branch, and each branch merges into `main` through a PR (the user's choice, 2026-10-24).

  | Branch | Tickets |
  |---|---|
  | `feat/kept-images` | 01–04: the converter and the CLI |
  | `feat/kept-images-web` | 05–07: the web, the cap on held outputs, and the final check on the samples |

  Ticket 06 needs no other ticket, but it ships with the web branch, so that the cap is in place before visitors can choose kept images.
- **Sample files.** `docs/example_pdf/` holds real contracts, one marked confidential. Converting or opening them needs the user's permission each time. Nothing of them goes into the spec, the tickets, the tests or a commit.
- **Glossary terms used:**
  - Kept images, Kept page
  - Scan, Picture
  - Text page, OCR page
  - Text layer, Page furniture
  - Placeholder, Uncertain text
  - Document model, Output, Conversion
