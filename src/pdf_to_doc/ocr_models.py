"""The OCR models: which ones, pinned to exact files, where they live, and fetching them.

Models are downloaded once, at install or image build time, by `pdf-to-doc-models`.
A conversion never downloads anything.
"""

import hashlib
import os
import shutil
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from pdf_to_doc.console import thai_safe_output

# Where the models live, unless this environment variable says otherwise.
FOLDER_VARIABLE = "PDF_TO_DOC_MODELS"
DEFAULT_FOLDER = Path.home() / ".cache" / "pdf-to-doc" / "models"
_SOURCE = "https://huggingface.co/PaddlePaddle/{name}/resolve/{revision}/{file}"


@dataclass(frozen=True)
class Model:
    name: str
    revision: str  # the Hugging Face commit
    files: dict[str, str]  # file name: SHA-256


DETECTOR = Model(
    name="PP-OCRv5_mobile_det",
    revision="0d63e78e2b680928f6b1747d76a08db6e645efb7",
    files={
        "config.json": "7ac1c33f377ba58561f4b89d3180b6add2b7c5c60a4edac90fa4e0ceccdc6665",
        "inference.json": "05feef1acb00aa4cd7362b15f7f501fc4f99d7b1fa73c1c871e0c7b1504b0f5c",
        "inference.pdiparams": "afa1820cb16c1fd0dad589d0f8b389139061c1ef6d68019685fd07be997dda5b",
        "inference.yml": "98069072e1b6b37d727fd9d9f11725faa46d6ea0de012f2ed26caea011c37699",
    },
)
THAI_RECOGNISER = Model(
    name="th_PP-OCRv5_mobile_rec",
    revision="9e25080455925d3943f5db885fddc79db6a07ca3",
    files={
        "config.json": "4a23fb6c20225c198d8d9130534475e578da5d0a1d5c93852ae8857dbd7ac120",
        "inference.json": "b92a9442af5ac6da3c6ba30ce1672d00a2d7a0fbd8068ed543ac6dcb9d5c7764",
        "inference.pdiparams": "45ec91f2322b58b8d30ba27d18fcfdbb8bf388b918dd978162d2af91e0c66d4b",
        "inference.yml": "f6ba7fefc38ca1ff398ddafa75d67d16e0b3757c4e6c833adffee98a981766c9",
    },
)
MODELS = (DETECTOR, THAI_RECOGNISER)


class ModelsMissing(RuntimeError):
    """The OCR models are not in the models folder; `pdf-to-doc-models` fetches them."""

    def __init__(self, folder: Path) -> None:
        super().__init__(f"OCR models not found in {folder}")
        self.folder = folder


def models_folder() -> Path:
    return Path(os.environ[FOLDER_VARIABLE]) if os.environ.get(FOLDER_VARIABLE) else DEFAULT_FOLDER


def model_path(folder: Path, model: Model) -> Path:
    """The model's folder, if all its files are there."""
    path = folder / model.name
    if not all((path / file).is_file() for file in model.files):
        raise ModelsMissing(folder)
    return path


def download(folder: Path) -> None:
    """Fetch every model that is not there yet, and check each file against its hash.

    A model is fetched into a folder of its own beside the target, and moved into
    place only once complete, so an interrupted download is never mistaken for a
    model.
    """
    folder.mkdir(parents=True, exist_ok=True)
    for model in MODELS:
        target = folder / model.name
        if target.is_dir():
            continue
        partial = folder / f"{model.name}.partial"
        shutil.rmtree(partial, ignore_errors=True)
        partial.mkdir()
        for file, sha256 in model.files.items():
            url = _SOURCE.format(name=model.name, revision=model.revision, file=file)
            with urllib.request.urlopen(url, timeout=60) as response:
                data = response.read()
            if hashlib.sha256(data).hexdigest() != sha256:
                raise RuntimeError(f"{model.name}/{file} does not match its pinned hash")
            (partial / file).write_bytes(data)
        partial.rename(target)


def main() -> int:
    thai_safe_output()
    folder = models_folder()
    download(folder)
    print(f"model สำหรับ OCR พร้อมใช้ที่ {folder}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
