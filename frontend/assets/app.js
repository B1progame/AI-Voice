// assets/app.js
import { onRouteChange } from "./router.js";
import { render } from "./ui.js";

async function boot() {
  try {
    await render();
  } catch (e) {
    console.error("Render crashed:", e);
    const root = document.querySelector("#app");
    if (root) root.textContent = "UI Crash: " + (e?.message || String(e));
  }
}

onRouteChange(boot);
boot();