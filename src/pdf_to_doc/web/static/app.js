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

// The bot check puts its token in the form a moment after the page loads. A file sent sooner
// waits for it, for up to 15 seconds, rather than being refused for want of it. A token is good
// for one upload only, so a page the browser shows again from its history gets a fresh one.
if (form && form.querySelector(".cf-turnstile")) {
  window.addEventListener("pageshow", (event) => {
    if (event.persisted && window.turnstile) {
      window.turnstile.reset();
      delete form.dataset.waited;
    }
  });
  const token = () => form.querySelector('[name="cf-turnstile-response"]')?.value;
  form.addEventListener("submit", (event) => {
    if (token() || form.dataset.waited) {
      return;
    }
    event.preventDefault();
    const started = Date.now();
    const wait = () => {
      if (token() || Date.now() - started > 15000) {
        form.dataset.waited = "yes";
        form.requestSubmit();
      } else {
        setTimeout(wait, 200);
      }
    };
    wait();
  });
}

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
