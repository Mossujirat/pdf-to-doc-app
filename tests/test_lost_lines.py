"""Lines the detector found and dropped on a scan, and the lines a blurred reading recovers there.

The regions and boxes are shaped as the PaddleOCR detector found them on a 300-dpi scan of an A4
page, 2481 pixels wide, among the local samples: where they lay and how they scored, never what
they said."""

import numpy as np

from pdf_to_doc.paddle import Reading, lost_lines, recovered

WIDTH = 2481


def region(x0: float, y0: float, x1: float, y1: float) -> np.ndarray:
    """A detector region: the four corners of its box, clockwise from the top left."""
    return np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], dtype=float)


# The lines the detector kept around the lost one: 60–90 pixels tall.
KEPT = [
    (region(390, 474, 2223, 537), 0.86),
    (region(390, 559, 2226, 622), 0.88),
    (region(378, 966, 580, 1056), 0.87),
    (region(856, 1198, 2224, 1258), 0.84),
    (region(387, 1633, 1495, 1708), 0.78),
    (region(388, 1825, 1063, 1894), 0.84),
]
# A whole line of a clause, 99 pixels tall and more than half the page wide.
LOST_LINE = region(844, 1721, 2232, 1820)


def test_a_dropped_region_one_line_tall_across_the_page_is_a_lost_line() -> None:
    [lost] = lost_lines([*KEPT, (LOST_LINE, 0.59)], WIDTH)

    assert np.array_equal(lost, LOST_LINE)


def test_a_dotted_signing_line_a_logo_and_a_word_are_no_lost_lines() -> None:
    dropped = [
        (region(1556, 3289, 1595, 3308), 0.52),  # dots under initials: a fifth of a line tall
        (region(446, 1691, 1296, 2113), 0.17),  # a logo: over five lines tall
        (region(1840, 2020, 1960, 2083), 0.58),  # a line tall, but 5% of the page wide at most
    ]

    assert lost_lines([*KEPT, *dropped], WIDTH) == []


def test_a_region_the_detector_kept_is_no_lost_line() -> None:
    assert lost_lines(KEPT, WIDTH) == []


# What the first reading read: the kept regions, each with its text and confidence.
READ = [Reading(f"บรรทัดที่ {number}", 0.95, polygon) for number, (polygon, _) in enumerate(KEPT, 1)]


def blurred(polygon: np.ndarray, shift: float = 2.0) -> np.ndarray:
    """A region as a blurred reading boxes it: a pixel or two from where the first reading did."""
    return polygon + shift


def test_a_line_a_blurred_reading_finds_in_a_lost_line_is_recovered_alone() -> None:
    line = Reading("ทั้งนี้ ข้อความของบรรทัดที่หายไปทั้งบรรทัด", 0.94, region(850, 1735, 2228, 1806))
    again = [reading._replace(corners=blurred(reading.corners)) for reading in READ] + [line]

    assert recovered([LOST_LINE], READ, again) == [line]


def test_text_the_first_reading_read_is_not_recovered_again() -> None:
    # A region two lines tall over a table's labels, dropped while each label was read on its own:
    # the blurred reading finds the same labels in it.
    labels = [
        Reading("ชื่อรายการแรก", 0.97, region(1170, 2330, 1640, 2370)),
        Reading("ชื่อรายการที่สอง", 0.96, region(1170, 2378, 1700, 2410)),
    ]
    dropped = region(1165, 2318, 1803, 2413)

    again = [reading._replace(corners=blurred(reading.corners)) for reading in labels]

    assert recovered([dropped], [*READ, *labels], again) == []


def test_text_over_two_lines_read_already_is_not_recovered_again() -> None:
    # A box across the lines above and below a dropped region: under half of it lies inside any one
    # of them, but more than half inside them all.
    dropped = region(400, 1700, 1500, 1830)
    across = Reading("ข้อความซ้ำสองบรรทัด", 0.9, region(420, 1683, 1480, 1850))

    assert recovered([dropped], [*READ, Reading("บรรทัดใต้", 0.95, region(388, 1795, 1500, 1894))], [across]) == []


def test_text_a_blurred_reading_finds_outside_the_lost_lines_is_not_recovered() -> None:
    # The blurred reading also finds a word the first one did not, by a stamp in the margin; the
    # detector dropped no line there, so the first reading stands.
    word = Reading("ประทับตรา", 0.9, region(2050, 300, 2300, 360))

    assert recovered([LOST_LINE], READ, [word]) == []


def test_junk_read_unsurely_and_a_lone_letter_are_not_recovered() -> None:
    # A signature beside a signing line, 6% of the page wide, read as junk; and a mark read as a
    # letter, surely. The real text the samples' blurred readings found read at 0.67 or more.
    signature = region(1636, 3173, 1789, 3289)
    mark = region(1533, 1630, 1669, 1669)
    again = [
        Reading("16", 0.24, region(1650, 3190, 1770, 3270)),
        Reading("nu ae", 0.6, region(1640, 3180, 1785, 3280)),
        Reading("o", 0.89, region(1540, 1635, 1660, 1665)),
    ]

    assert recovered([signature, mark], READ, again) == []
