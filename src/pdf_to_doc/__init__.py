"""Convert PDF files into Markdown or DOCX whose Thai and English text reads exactly as the original."""

from pdf_to_doc.conversion import ConversionResult, DocxToDocx, convert
from pdf_to_doc.intake import (
    CopyRestricted,
    DamagedFile,
    IntakeError,
    PasswordRequired,
    TooLarge,
    UnsupportedFormat,
    WrongPassword,
)
from pdf_to_doc.ocr import Language, OcrEngine, PageImage, TextBox
from pdf_to_doc.ocr_models import ModelsMissing
from pdf_to_doc.progress import Opened, Progress, ProgressCallback
from pdf_to_doc.summary import PageSummary, Summary

__all__ = [
    "ConversionResult",
    "CopyRestricted",
    "DamagedFile",
    "DocxToDocx",
    "IntakeError",
    "Language",
    "ModelsMissing",
    "OcrEngine",
    "Opened",
    "PageImage",
    "PageSummary",
    "PasswordRequired",
    "Progress",
    "ProgressCallback",
    "Summary",
    "TextBox",
    "TooLarge",
    "UnsupportedFormat",
    "WrongPassword",
    "convert",
]
