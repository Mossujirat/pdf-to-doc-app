# Each web conversion runs in its own throwaway gVisor container

The web service takes PDFs from anyone and runs on gmt, the server that also holds the Chatbot project's database and keys. A crafted PDF that exploits the parser must reach neither those nor other users' files. So each conversion gets a fresh container that is thrown away when it ends: the gVisor runtime (runsc) as a second wall between the converter and the host's Linux kernel, no network, a read-only file system, a non-root user, no capabilities, 4 CPUs and 2 GB of memory. The source file goes in on stdin and the outputs come back on stdout. Stopping the container is how a conversion is cancelled. Only a small launcher, separate from the internet-facing web app, can start containers, and it can start only this one.

## Considered Options

- **A long-running worker container** that takes conversions over a socket. It is simpler and needs no Docker access, but code that took it over would see every later user's file. Measurements also showed memory growing across conversions in one process (1.0 to 1.27 GB over six), and a conversion can only be stopped by killing its process.
- **The normal runtime (runc) without gVisor.** This is the fallback if PaddleOCR does not run under gVisor on staging, with every other restriction kept.

## Consequences

- The converter needs a stdin/stdout mode, and must render both outputs from one conversion.
- PaddleOCR must be told how many CPUs the container has. It always starts 10 threads, and under a 4-CPU limit that ran almost three times slower (8.8 instead of 3.3 seconds a page).
- Each conversion pays the OCR model load, about 5–6 seconds, as it already did (ticket 12).
- gVisor is installed on gmt once and kept up to date.
