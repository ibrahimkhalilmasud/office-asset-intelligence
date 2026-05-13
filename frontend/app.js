const API = "http://127.0.0.1:8000";
let token = "";

async function ensureAuth() {
  const user = "admin";
  const pass = "admin123";

  await fetch(`${API}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username: user, password: pass }),
  }).catch(() => {});

  const body = new URLSearchParams({ username: user, password: pass });
  const res = await fetch(`${API}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  const data = await res.json();
  token = data.access_token;
}

async function authFetch(path) {
  const res = await fetch(`${API}${path}`, { headers: { Authorization: `Bearer ${token}` } });
  return res.json();
}

function renderAssets(assets) {
  const rows = document.getElementById("assetRows");
  rows.innerHTML = assets
    .map(
      (asset) => `
      <tr>
        <td>${asset.name}</td>
        <td>${asset.category}</td>
        <td>${asset.status}</td>
        <td>${asset.office_id}</td>
        <td>$${asset.purchase_cost.toFixed(2)}</td>
      </tr>`
    )
    .join("");
}

async function loadDashboard() {
  const analytics = await authFetch("/dashboard/analytics");
  document.getElementById("totalAssets").textContent = `Total assets: ${analytics.total_assets}`;
  document.getElementById("totalCost").textContent = `Total cost: $${Number(analytics.total_cost).toFixed(2)}`;
  document.getElementById("maintenanceCount").textContent = `Maintenance events: ${analytics.maintenance_events}`;
  document.getElementById("departmentUsage").innerHTML = analytics.department_usage
    .map((entry) => `<li>${entry.department}: ${entry.assignments} assignments</li>`)
    .join("");

  const assets = await authFetch("/assets");
  renderAssets(assets);
}

function setupFilters() {
  const search = document.getElementById("searchInput");
  const category = document.getElementById("categoryFilter");
  const handler = async () => {
    const q = search.value.trim();
    const c = category.value.trim();
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (c) params.set("category", c);
    const assets = await authFetch(`/assets?${params.toString()}`);
    renderAssets(assets);
  };

  search.addEventListener("input", handler);
  category.addEventListener("change", handler);
}

(async function init() {
  await ensureAuth();
  setupFilters();
  await loadDashboard();
})();
