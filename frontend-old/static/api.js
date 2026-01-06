(function () {
  function getCookie(name) {
    const m = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
    return m ? decodeURIComponent(m[2]) : null;
  }

  async function apiFetch(path, options) {
    const opts = options || {};
    opts.method = opts.method || "GET";
    opts.headers = opts.headers || {};

    // Always send cookies (JWT cookie + CSRF cookie)
    opts.credentials = "include";

    // For state-changing requests, attach CSRF header (double-submit cookie)
    const method = (opts.method || "GET").toUpperCase();
    if (["POST", "PATCH", "DELETE"].includes(method)) {
      const csrf = getCookie("csrf_token");
      if (csrf) {
        opts.headers["X-CSRF-Token"] = csrf;
      }
    }

    // JSON default
    if (opts.body && typeof opts.body === "object" && !(opts.body instanceof FormData)) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(opts.body);
    }

    const res = await fetch(path, opts);
    const text = await res.text();
    let data = null;
    try { data = text ? JSON.parse(text) : null; } catch { data = { raw: text }; }

    if (!res.ok) {
      const msg = (data && (data.detail || data.message)) ? (data.detail || data.message) : ("HTTP " + res.status);
      const err = new Error(msg);
      err.status = res.status;
      err.data = data;
      throw err;
    }
    return data;
  }

  window.API = {
    getCookie,
    apiFetch,
  };
})();