"""The exit codes of the command line and of the sandbox entry point, which share them."""

from pdf_to_doc.conversion import DocxToDocx
from pdf_to_doc.intake import (
    CopyRestricted,
    DamagedFile,
    IntakeError,
    PasswordRequired,
    TooLarge,
    UnsupportedFormat,
    WrongPassword,
)

EXIT_OK = 0
# Exit code 1 is Python's for a crash, and 2 is argparse's for bad arguments.
EXIT_UNSUPPORTED_FORMAT = 3
EXIT_TOO_LARGE = 4
EXIT_PASSWORD_REQUIRED = 5
EXIT_WRONG_PASSWORD = 6
EXIT_COPY_RESTRICTED = 7
EXIT_DAMAGED_FILE = 8
EXIT_MODELS_MISSING = 9
# Only the sandbox entry point uses this: any other error, which it reports as a
# failure event. A crash it could not report still exits with Python's 1.
EXIT_FAILED = 10

# The exit code for each kind of refusal.
REFUSAL_EXIT_CODES: dict[type[IntakeError], int] = {
    UnsupportedFormat: EXIT_UNSUPPORTED_FORMAT,
    DocxToDocx: EXIT_UNSUPPORTED_FORMAT,
    TooLarge: EXIT_TOO_LARGE,
    PasswordRequired: EXIT_PASSWORD_REQUIRED,
    WrongPassword: EXIT_WRONG_PASSWORD,
    CopyRestricted: EXIT_COPY_RESTRICTED,
    DamagedFile: EXIT_DAMAGED_FILE,
}
