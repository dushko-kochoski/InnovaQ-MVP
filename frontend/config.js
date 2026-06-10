// ── InnovaQ frontend configuration ──────────────────────────────────────
// Single source of truth for the API base URL, loaded by every page that
// talks to the backend (auth/*, app/*). No build step: pages include this
// via <script src="/config.js"></script> and read window.API_BASE_URL.
//
// After deploying the backend to Railway, set PRODUCTION_API below to your
// service URL (no trailing slash), e.g. "https://innovaq-api.up.railway.app".
(function () {
  const LOCAL_API = "http://127.0.0.1:8000";
  const PRODUCTION_API = "https://YOUR-BACKEND.up.railway.app"; // ← edit after deploy

  const isLocal = ["127.0.0.1", "localhost"].includes(window.location.hostname);
  window.API_BASE_URL = isLocal ? LOCAL_API : PRODUCTION_API;
})();
