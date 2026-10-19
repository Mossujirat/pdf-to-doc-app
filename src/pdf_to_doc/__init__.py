"""Convert PDF files into Markdown whose Thai and English text reads exactly as the original."""

from pdf_to_doc.conversion import ConversionResult, convert
from pdf_to_doc.intake import (
    CopyRestricted,
    DamagedFile,
    IntakeError,
    PasswordRequired,
    TooLarge,
    UnsupportedFormat,
    WrongPassword,
)
from pdf_to_doc.summary import PageSummary, Summary

__all__ = [
    "ConversionResult",
    "CopyRestricted",
    "DamagedFile",
    "IntakeError",
    "PageSummary",
    "PasswordRequired",
    "Summary",
    "TooLarge",
    "UnsupportedFormat",
    "WrongPassword",
    "convert",
]
