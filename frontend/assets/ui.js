// assets/ui.js
import { api } from "./api.js";
import { state, loadMeOnce, resetMeCache } from "./state.js";
import { go, path } from "./router.js";

function qs(sel, root = document) { return root.querySelector(sel); }

function safeJson(x) {
  try { return JSON.stringify(x); }
  catch { return String(x); }
}

export function formatError(e) {
  if (!e) return "Unbekannter Fehler";
  if (typeof e === "string") return e;

  // Fehler aus api.js: Error mit .status und .data
  if (e instanceof Error) {
    const msg = e.message || "Fehler";
    const status = e.status ? ` (HTTP ${e.status})` : "";
    if (e.data) {
      // e.data kann {detail:"..."} oder {raw:"..."} sein
      const detail = e.data.detail || e.data.message || e.data.raw || safeJson(e.data);
      // Detail nicht doppelt anhängen
      if (detail && detail !== msg) return `${msg}${status}: ${detail}`;
    }
    return `${msg}${status}`;
  }

  // sonstiges Objekt (z.B. {detail:"..."})
  if (e.detail || e.message) return e.detail || e.message;

  return safeJson(e);
}

function renderInto(html) {
  const root = qs("#app");
  if (!root) throw new Error("Kein #app Element in index.html gefunden.");
  root.innerHTML = html;
  return root;
}

export async function render() {
  const p = path();

  // Auth-Status einmal holen (verhindert flackern)
  try { await loadMeOnce(); } catch (e) { console.error("loadMeOnce failed:", e); }

  // Routen
  if (p === "/login") return renderLogin();
  if (p === "/register") return renderRegister();

  // Default: wenn nicht eingeloggt -> login
  if (state.auth !== "authed") {
    go("/login");
    return;
  }
  return renderApp();
}

function authHeader() {
  const email = state.me?.email ? `Eingeloggt: ${state.me.email}` : "Nicht eingeloggt";
  return `
    <div class="topbar">
      <div>${email}</div>
      <div style="display:flex; gap:8px;">
        <button id="btn-logout">Logout</button>
      </div>
    </div>
  `;
}

function renderLogin() {
  const root = renderInto(`
    <div class="page">
      <h1>Login</h1>
      <p id="status" style="min-height:20px;"></p>

      <form id="loginForm" autocomplete="on">
        <label>Email</label>
        <input id="email" type="email" required autocomplete="username" />
        <label>Password</label>
        <input id="password" type="password" required autocomplete="current-password" />
        <button type="submit">Login</button>
      </form>

      <p style="margin-top:12px;">
        Noch keinen Account?
        <a href="#/register" id="toRegister">Registrieren</a>
      </p>
    </div>
  `);

  const status = qs("#status", root);

  qs("#loginForm", root).addEventListener("submit", async (ev) => {
    ev.preventDefault();
    status.textContent = "…";

    const email = qs("#email", root).value.trim();
    const password = qs("#password", root).value;

    try {
      // optional: csrf init (wenn /api/csrf existiert)
      try { await api.csrf?.(); } catch {}

      await api.login(email, password);

      // Auth-Cache reset & neu laden
      resetMeCache();
      await loadMeOnce();

      go("/"); // oder /app
    } catch (e) {
      status.textContent = formatError(e);
      console.error("LOGIN ERROR:", e);
    }
  });

  return root;
}

function renderRegister() {
  const root = renderInto(`
    <div class="page">
      <h1>Registrieren</h1>
      <p id="status" style="min-height:20px;"></p>

      <form id="regForm" autocomplete="on">
        <label>Email</label>
        <input id="email" type="email" required autocomplete="username" />
        <label>Password</label>
        <input id="password" type="password" required autocomplete="new-password" />
        <button type="submit">Account erstellen</button>
      </form>

      <p style="margin-top:12px;">
        Schon einen Account?
        <a href="#/login">Zum Login</a>
      </p>
    </div>
  `);

  const status = qs("#status", root);

  qs("#regForm", root).addEventListener("submit", async (ev) => {
    ev.preventDefault();
    status.textContent = "…";

    const email = qs("#email", root).value.trim();
    const password = qs("#password", root).value;

    try {
      try { await api.csrf?.(); } catch {}
      await api.register(email, password);
      status.textContent = "Registrierung ok. Du kannst dich jetzt einloggen.";
      // Optional: direkt zum login
      setTimeout(() => go("/login"), 250);
    } catch (e) {
      status.textContent = formatError(e);
      console.error("REGISTER ERROR:", e);
    }
  });

  return root;
}

function renderApp() {
  const root = renderInto(`
    ${authHeader()}
    <div class="page">
      <h2>App</h2>
      <p>✅ Login funktioniert, wenn du hier bist.</p>

      <p>Als nächstes: Conversation-Liste + Messages rendern.</p>

      <pre id="debug" style="white-space:pre-wrap;"></pre>
    </div>
  `);

  qs("#debug", root).textContent = safeJson({ me: state.me, auth: state.auth });

  qs("#btn-logout", root).addEventListener("click", async () => {
    try {
      await api.logout();
    } catch (e) {
      console.error("logout error", e);
    } finally {
      resetMeCache();
      await loadMeOnce(); // setzt anon
      go("/login");
    }
  });

  return root;
}