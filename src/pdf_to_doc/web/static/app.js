// The pages' only script: no build step, and no inline script anywhere.

// While the tab is away, a lit step stays lit: it fades only once someone can see it.
const awayClass = () => document.documentElement.classList.toggle("is-away", document.hidden);
document.addEventListener("visibilitychange", awayClass);
awayClass();

// A conversion waiting or in progress asks for its state every 2 seconds, shows it on the
// page, in its steps and in the tab's title, and shows the page again once it has ended.
// A step whose state changed is tinted for a moment.
const status = document.getElementById("status");
const steps = document.getElementById("steps");
if (status && status.dataset.state) {
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
        // Only a change is written, or a screen reader may announce the same status every time.
        if (status.textContent !== state.text) {
          status.textContent = state.text;
          document.title = state.text;
        }
        // Each step is updated in place, not replaced, so that one still lit keeps its fade.
        if (steps && state.steps) {
          const fresh = document.createElement("template");
          fresh.innerHTML = state.steps;
          for (const step of fresh.content.querySelectorAll("[data-step]")) {
            const shown = steps.querySelector(`[data-step="${step.dataset.step}"]`);
            if (!shown) {
              continue;
            }
            if (shown.dataset.at !== step.dataset.at) {
              shown.className = `${step.className} is-lit`;
              shown.dataset.at = step.dataset.at;
            }
            if (shown.innerHTML !== step.innerHTML) {
              shown.innerHTML = step.innerHTML;
            }
          }
        }
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
    try {
      await navigator.clipboard.writeText(text ?? (await markdown));
      copy.lastChild.textContent = " คัดลอกแล้ว";
    } catch {
      copy.lastChild.textContent = " คัดลอกไม่ได้ ใช้ปุ่มดาวน์โหลดแทน";
    }
  });
}

// A file is sent as soon as it is picked, or dropped anywhere on the form.
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
  const drop = form.querySelector(".drop");
  const title = form.querySelector("[data-drop-title]");
  const name = form.querySelector("[data-file-name]");
  const ready = title?.textContent;
  const send = () => {
    const file = input.files[0];
    if (!file) {
      return;
    }
    if (title) {
      title.textContent = "กำลังส่งไฟล์";
    }
    if (name) {
      name.textContent = file.name;
    }
    form.requestSubmit();
  };
  // A page the browser shows again from its history no longer sends anything.
  window.addEventListener("pageshow", (event) => {
    if (event.persisted) {
      form.reset();
      if (title) {
        title.textContent = ready;
      }
      if (name) {
        name.textContent = "";
      }
    }
  });
  input.addEventListener("change", send);
  for (const type of ["dragenter", "dragover"]) {
    form.addEventListener(type, (event) => {
      event.preventDefault();
      drop?.classList.add("is-over");
    });
  }
  form.addEventListener("dragleave", (event) => {
    if (!form.contains(event.relatedTarget)) {
      drop?.classList.remove("is-over");
    }
  });
  form.addEventListener("drop", (event) => {
    event.preventDefault();
    drop?.classList.remove("is-over");
    if (event.dataTransfer.files.length === 1) {
      input.files = event.dataTransfer.files;
      send();
    }
  });
}
