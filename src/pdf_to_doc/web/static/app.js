// The pages' only script: no build step, and no inline script anywhere.

// A conversion waiting or in progress asks for its state every 2 seconds, shows it on the
// page and in the tab's title, and shows the page again once it has ended.
const status = document.getElementById("status");
if (status) {
  const ask = async () => {
    try {
      const response = await fetch(status.dataset.state, { cache: "no-store" });
      if (response.status === 404) {
        location.reload();
        return;
      }
      if (response.ok) {
        const state = await response.json();
        if (!state.ongoing) {
          location.reload();
          return;
        }
        status.textContent = state.text;
        document.title = state.text;
      }
    } catch {
      // Offline for a moment, or the phone suspended the tab: ask again later.
    }
    setTimeout(ask, 2000);
  };
  setTimeout(ask, 2000);
}

// The Markdown is fetched as soon as the result shows, so that a click can copy it at once:
// some browsers allow writing to the clipboard only straight from the click.
const copy = document.getElementById("copy");
if (copy) {
  const markdown = fetch(copy.dataset.markdown).then((response) => response.text());
  let text = null;
  markdown.then((value) => {
    text = value;
  });
  copy.addEventListener("click", async () => {
    await navigator.clipboard.writeText(text ?? (await markdown));
    copy.textContent = "คัดลอกแล้ว";
  });
}

// A file dropped anywhere on the form is sent, as one picked with the button is.
const form = document.getElementById("upload");
if (form) {
  const input = form.querySelector("input[type=file]");
  form.addEventListener("dragover", (event) => event.preventDefault());
  form.addEventListener("drop", (event) => {
    event.preventDefault();
    if (event.dataTransfer.files.length === 1) {
      input.files = event.dataTransfer.files;
      form.requestSubmit();
    }
  });
}
