"""What the launcher creates each sandbox's container with, in Docker.

CI cannot run Docker, so these tests guard the restrictions the launcher asks for. That Docker
applies them was checked by hand on Docker Desktop (ticket 09), and staging's smoke test checks
it again on the server (ticket 14).
"""

import pytest

from pdf_to_doc.web.docker import sandbox_config, sandbox_name
from pdf_to_doc.web.settings import Environment


def test_a_sandbox_container_is_created_under_every_restriction() -> None:
    config = sandbox_config(image="sha256:0123abcd", environment="production", runtime="runsc", keep_images=False)
    host = config["HostConfig"]

    # The sandbox entry point, from the image the launcher itself runs, in the runtime asked for.
    assert config["Image"] == "sha256:0123abcd"
    assert config["Cmd"] == ["pdf-to-doc-sandbox"]
    assert host["Runtime"] == "runsc"
    # No network.
    assert config["NetworkDisabled"] is True
    assert host["NetworkMode"] == "none"
    # A read-only root, with a small scratch area in memory.
    assert host["ReadonlyRootfs"] is True
    assert list(host["Tmpfs"]) == ["/tmp"]
    assert "size=" in host["Tmpfs"]["/tmp"]
    # The image's non-root user, with no capabilities and no new privileges.
    assert config["User"] == "converter"
    assert host["CapDrop"] == ["ALL"]
    assert "CapAdd" not in host
    assert host["SecurityOpt"] == ["no-new-privileges"]
    assert "Privileged" not in host
    # 4 CPUs, 2 GB of memory and no swap, and a limit on processes.
    assert host["NanoCpus"] == 4_000_000_000
    assert host["Memory"] == 2 * 1024**3
    assert host["MemorySwap"] == host["Memory"]
    assert host["PidsLimit"] > 0  # 0 and -1 would be none
    # No volumes, and no environment beyond the OCR thread count, which matches the CPUs, and
    # whether to keep images.
    assert "Binds" not in host
    assert "Mounts" not in host
    assert config["Env"] == ["PDF_TO_DOC_OCR_THREADS=4", "PDF_TO_DOC_KEEP_IMAGES=0"]
    # The source file comes on stdin, which closes once it has all come.
    assert (config["AttachStdin"], config["OpenStdin"], config["StdinOnce"], config["Tty"]) == (True, True, True, False)
    # Docker keeps no log of what the sandbox writes: the outputs are the document's text.
    assert host["LogConfig"] == {"Type": "none"}


def test_a_sandbox_container_keeping_images_differs_only_in_that_setting() -> None:
    reading = sandbox_config(image="sha256:0123abcd", environment="production", runtime="runsc", keep_images=False)
    keeping = sandbox_config(image="sha256:0123abcd", environment="production", runtime="runsc", keep_images=True)

    assert keeping["Env"] == ["PDF_TO_DOC_OCR_THREADS=4", "PDF_TO_DOC_KEEP_IMAGES=1"]
    assert {**keeping, "Env": None} == {**reading, "Env": None}


@pytest.mark.parametrize("environment", ["production", "staging"])
def test_a_sandbox_container_is_named_and_labelled_for_its_environment(environment: Environment) -> None:
    config = sandbox_config(image="sha256:0123abcd", environment=environment, runtime="runc", keep_images=False)

    assert sandbox_name(environment).startswith(f"pdf-to-doc-sandbox-{environment}-")
    assert sandbox_name(environment) != sandbox_name(environment)
    assert config["Labels"] == {"pdf-to-doc.sandbox": environment}
