// assets/router.js
export function path() {
  const h = window.location.hash || "#/";
  const p = h.startsWith("#") ? h.slice(1) : h;
  return p || "/";
}

export function go(p) {
  if (!p.startsWith("/")) p = "/" + p;
  window.location.hash = "#" + p;
}

export function onRouteChange(cb) {
  window.addEventListener("hashchange", cb);
  window.addEventListener("load", cb);
}