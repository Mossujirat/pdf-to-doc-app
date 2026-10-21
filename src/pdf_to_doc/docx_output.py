"""Renders the document model as a Word file for editing, keeping its structure rather than its page layout."""

import io
import re
from collections.abc import Iterator

import docx
from docx.document import Document as WordDocument
from docx.enum.text import WD_COLOR_INDEX
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.oxml.xmlchemy import BaseOxmlElement
from docx.shared import Cm, Mm, Pt
from docx.table import Table as WordTable
from docx.text.paragraph import Paragraph as WordParagraph

from pdf_to_doc.model import (
    DEEPEST_HEADING,
    Block,
    Document,
    Heading,
    ListItem,
    Span,
    Table,
    TableCell,
    stretches,
    uncertain_text,
)
from pdf_to_doc.summary import Summary
from pdf_to_doc.thai import THAI_LETTER

# Thai and English alike, so lines that mix them keep one size.
_FONT = "TH Sarabun New"
_BODY_SIZE = 16  # points
# Heading sizes by level; deeper levels are bold at the body size.
_HEADING_SIZES = {1: 20, 2: 18}
# The space the template leaves after each paragraph, kept below a table too.
_SPACE_AFTER_TABLE = Pt(10)

# A run of English: from a letter or digit to a letter or digit, holding ASCII spaces
# and punctuation, typographic apostrophes and the en dash in between.
_LATIN = re.compile(r"[A-Za-z0-9](?:[ -~\u2018\u2019\u2013]*[A-Za-z0-9])?")
_LETTER = re.compile(r"[A-Za-z]")
_THAI = re.compile(THAI_LETTER)


def render_docx(document: Document, summary: Summary) -> bytes:
    word = docx.Document()
    [section] = word.sections
    # A4 with Word's usual margins, in place of the template's US Letter.
    section.page_width, section.page_height = Mm(210), Mm(297)
    section.left_margin = section.right_margin = section.top_margin = section.bottom_margin = Cm(2.54)
    _set_default_font(word.styles.element)
    for level in range(1, DEEPEST_HEADING + 1):
        _set_heading_font(word.styles[f"Heading {level}"].element, _HEADING_SIZES.get(level, _BODY_SIZE))
    unmarked_list_id = _add_unmarked_list(word.part.numbering_part.element)
    summary_paragraph = word.add_paragraph()
    _add_text(summary_paragraph, "สรุปการแปลง", bold=True)
    _add_text(summary_paragraph, f" {summary.headline(uncertain_marked_as='ไฮไลต์สีเหลือง')}")
    for index, page in enumerate(document.pages):
        first: WordParagraph | None = None
        previous: Block | None = None
        for block in page.blocks:
            if isinstance(previous, Table) and isinstance(block, Table):
                word.add_paragraph()  # Word joins tables that touch into one
            paragraph = _add_block(word, block, unmarked_list_id)
            first = first or paragraph
            if isinstance(previous, Table) and not isinstance(block, (Heading, Table)):
                # Headings have space above them already; other text would sit on the table's bottom line.
                paragraph.paragraph_format.space_before = _SPACE_AFTER_TABLE
            previous = block
        if index > 0:
            # Each page of the original starts a new page, at its own first paragraph. A page
            # break in a paragraph of its own falls onto a page of its own when the page before
            # is full, and leaves that page blank. An empty page is an empty paragraph.
            (first or word.add_paragraph()).paragraph_format.page_break_before = True
    # Written to memory: a conversion leaves no file behind.
    buffer = io.BytesIO()
    word.save(buffer)
    return buffer.getvalue()


def _add_block(word: WordDocument, block: Block, unmarked_list_id: int) -> WordParagraph:
    """Adds the block, and returns the paragraph it starts with: for a table, its first cell's."""
    if isinstance(block, Table):
        first_paragraph: WordParagraph = _add_table(word, block).cell(0, 0).paragraphs[0]
        return first_paragraph
    if isinstance(block, Heading):
        paragraph = word.add_paragraph(style=f"Heading {block.level}")
    elif isinstance(block, ListItem) and block.bulleted:
        paragraph = word.add_paragraph(style="List Bullet")
    elif isinstance(block, ListItem):
        paragraph = word.add_paragraph(style="List Paragraph")
        numbering = paragraph._p.get_or_add_pPr().get_or_add_numPr()
        numbering.get_or_add_ilvl().val = 0
        numbering.get_or_add_numId().val = unmarked_list_id
    else:
        paragraph = word.add_paragraph()
    _add_text(paragraph, block.text, uncertain=uncertain_text(block))
    return paragraph


def _add_table(word: WordDocument, table: Table) -> WordTable:
    """A Word table with real merged cells, its columns of equal width."""
    placed = list(_place_cells(table))
    columns = max(column + cell.colspan for _, column, cell in placed)
    word_table: WordTable = word.add_table(rows=len(table.rows), cols=columns)
    word_table.style = "Table Grid"
    for row, column, cell in placed:
        target = word_table.cell(row, column)
        if cell.rowspan > 1 or cell.colspan > 1:
            last_row = min(row + cell.rowspan, len(table.rows)) - 1
            target = target.merge(word_table.cell(last_row, column + cell.colspan - 1))
        _add_text(target.paragraphs[0], cell.text)
    return word_table


def _place_cells(table: Table) -> Iterator[tuple[int, int, TableCell]]:
    """Each cell with the row and column it starts at. A cell starts at the first column
    of its row that no merged cell from the rows above reaches into."""
    covered: set[tuple[int, int]] = set()
    for row, cells in enumerate(table.rows):
        column = 0
        for cell in cells:
            while (row, column) in covered:
                column += 1
            yield row, column, cell
            covered.update(
                (row + down, column + across) for down in range(cell.rowspan) for across in range(cell.colspan)
            )
            column += cell.colspan


def _add_unmarked_list(numbering: BaseOxmlElement) -> int:
    """A list whose items show nothing of Word's before them, for items that keep their own
    number or letter as text. Their text lines up with that of bulleted items. Returns its numbering id."""
    taken = [int(abstract.get(qn("w:abstractNumId"))) for abstract in numbering.findall(qn("w:abstractNum"))]
    abstract_id = max(taken) + 1
    abstract = parse_xml(
        f'<w:abstractNum {nsdecls("w")} w:abstractNumId="{abstract_id}">'
        '<w:multiLevelType w:val="singleLevel"/>'
        '<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="none"/>'
        # No tab after the empty number, or the text would start at the next tab stop.
        '<w:suff w:val="nothing"/><w:lvlText w:val=""/><w:lvlJc w:val="left"/>'
        '<w:pPr><w:ind w:left="360" w:hanging="0"/></w:pPr></w:lvl>'
        "</w:abstractNum>"
    )
    # Every abstract definition comes before the first numbering instance.
    numbering.find(qn("w:num")).addprevious(abstract)
    return int(numbering.add_num(abstract_id).numId)


def _set_default_font(styles: BaseOxmlElement) -> None:
    """Every style starts from TH Sarabun New in all four font slots, Thai as the complex-script language."""
    run_properties = styles.find(f"{qn('w:docDefaults')}/{qn('w:rPrDefault')}/{qn('w:rPr')}")
    _set_font(run_properties, _BODY_SIZE)
    language = run_properties.find(qn("w:lang"))
    language.set(qn("w:bidi"), "th-TH")


def _set_heading_font(style: BaseOxmlElement, size: float) -> None:
    """Bold TH Sarabun New in both slots, black and upright, in place of the template's theme fonts and colours."""
    run_properties = style.get_or_add_rPr()
    for child in list(run_properties):
        run_properties.remove(child)
    _set_font(run_properties, size)
    for index, tag in enumerate(("w:b", "w:bCs"), start=1):
        run_properties.insert(index, OxmlElement(tag))


def _set_font(run_properties: BaseOxmlElement, size: float) -> None:
    """Names the font in every slot, so no theme font applies, and sets the plain and complex-script sizes."""
    fonts = run_properties.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        run_properties.insert(0, fonts)
    fonts.attrib.clear()
    for slot in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        fonts.set(qn(slot), _FONT)
    for tag in ("w:sz", "w:szCs"):
        element = run_properties.find(qn(tag))
        if element is None:
            element = OxmlElement(tag)
            run_properties.append(element)
        element.set(qn("w:val"), str(round(size * 2)))  # half-points


def _add_text(paragraph: WordParagraph, text: str, *, bold: bool = False, uncertain: tuple[Span, ...] = ()) -> None:
    """Thai goes in runs marked complex script, so Word breaks its lines between words. English
    words get runs of their own without the mark, or Word would proof them as Thai. Uncertain
    text is highlighted yellow."""
    for highlighted, stretch in stretches(text, uncertain):
        for latin, piece in _pieces(stretch):
            run = paragraph.add_run(piece)
            if not latin and _THAI.search(piece):
                run.font.complex_script = True
            if bold:
                # Thai is drawn with the complex-script bold, other text with the plain one.
                run.font.bold = run.font.cs_bold = True
            if highlighted:
                run.font.highlight_color = WD_COLOR_INDEX.YELLOW


def _pieces(text: str) -> list[tuple[bool, str]]:
    """The text cut into English runs and the rest, in order. Numbers alone stay with the text around them."""
    pieces: list[tuple[bool, str]] = []
    position = 0
    for match in _LATIN.finditer(text):
        if not _LETTER.search(match[0]):
            continue
        if match.start() > position:
            pieces.append((False, text[position : match.start()]))
        pieces.append((True, match[0]))
        position = match.end()
    if position < len(text):
        pieces.append((False, text[position:]))
    return pieces
