const appState = {
  activeView: "dashboard",
  data: null,
  watchQuery: "",
  watchType: "All",
  watchRisk: "All",
  watchSort: "finalScore",
  selectedTicker: null,
  detailTab: "Overview",
  picksTheme: "All",
  picksType: "All",
  picksRisk: "All",
  picksSort: "score",
  editingTransactionId: null,
  skippedTickers: [],
  sidebarCollapsed: false,
  expandedWatchRows: [],
  expandedHoldingRows: [],
};

const views = [
  ["dashboard", "Recommendation Dashboard", "Personal watchlist and holdings only"],
  ["weekly", "Weekly Picks", "Research candidates from the universe"],
  ["watchlist", "Watchlist Detail", "Quantitative watchlist analysis"],
  ["portfolio", "Portfolio / Holdings", "Manual ledger and calculated holdings"],
  ["settings", "Settings", "Preferences and candidate universe"],
];

const actionColors = {
  "Strong Buy": "green",
  "Buy": "blue",
  "Small Buy / Watch": "yellow",
  "Hold / Watch": "gray",
  Avoid: "red",
  Add: "green",
  Hold: "blue",
  "Do not add": "yellow",
  Trim: "orange",
  "Take profit": "orange",
  "Sell alert": "red",
  "Review with LLM": "purple",
  Rebalance: "orange",
  Warning: "orange",
  OK: "green",
};

const riskColors = {
  Low: "green",
  Medium: "blue",
  "Medium-High": "orange",
  High: "red",
};

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("sidebar-toggle").addEventListener("click", toggleSidebar);
  renderNav();
  document.getElementById("refresh-button").addEventListener("click", loadState);
  loadState();
});

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    let message = response.statusText;
    try {
      const payload = await response.json();
      message = payload.error || message;
    } catch {
      message = response.statusText;
    }
    throw new Error(message);
  }
  return response.json();
}

async function apiText(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(response.statusText);
  return response.text();
}

async function loadState() {
  try {
    appState.data = await api("/api/state");
    if (!appState.selectedTicker && appState.data.watchlistAnalysis.length) {
      appState.selectedTicker = appState.data.watchlistAnalysis[0].ticker;
    }
    render();
  } catch (error) {
    document.getElementById("app").innerHTML = `<div class="empty-state">${escapeHtml(error.message)}</div>`;
  }
}

function renderNav() {
  const nav = document.getElementById("nav");
  document.querySelector(".app-shell").classList.toggle("sidebar-collapsed", appState.sidebarCollapsed);
  document.getElementById("sidebar-toggle").textContent = appState.sidebarCollapsed ? "›" : "‹";
  nav.innerHTML = views
    .map(([id, label]) => `<button type="button" class="${id === appState.activeView ? "active" : ""}" onclick="setView('${id}')" title="${escapeAttr(label)}"><span class="nav-short">${shortNavLabel(id)}</span><span class="nav-label">${label}</span></button>`)
    .join("");
}

function shortNavLabel(id) {
  return {
    dashboard: "Dash",
    weekly: "Picks",
    watchlist: "Watch",
    portfolio: "Hold",
    settings: "Set",
  }[id] || id;
}

function toggleSidebar() {
  appState.sidebarCollapsed = !appState.sidebarCollapsed;
  renderNav();
}

function setView(view) {
  appState.activeView = view;
  const meta = views.find(([id]) => id === view);
  document.getElementById("page-title").textContent = meta[1];
  document.getElementById("page-kicker").textContent = meta[2];
  renderNav();
  render();
}

function render() {
  if (!appState.data) return;
  const app = document.getElementById("app");
  const renderer = {
    dashboard: renderDashboard,
    weekly: renderWeeklyPicks,
    watchlist: renderWatchlist,
    portfolio: renderPortfolio,
    settings: renderSettings,
  }[appState.activeView];
  app.innerHTML = renderer();
  bindViewEvents();
}

function bindViewEvents() {
  if (appState.activeView === "dashboard") bindDashboardEvents();
  if (appState.activeView === "weekly") bindWeeklyEvents();
  if (appState.activeView === "watchlist") bindWatchlistEvents();
  if (appState.activeView === "portfolio") bindPortfolioEvents();
  if (appState.activeView === "settings") bindSettingsEvents();
}

function renderDashboard() {
  const { summaryCards, settings, recommendation } = appState.data;
  const noBuy = recommendation.noBuy || !recommendation.mainRecommendations.length;
  return `
    <div class="stack">
      ${renderCards(summaryCards)}
      <div class="grid two">
        <section class="panel">
          <div class="panel-header">
            <div>
              <h3>Investment Input</h3>
              <p>Recommendation inputs</p>
            </div>
            <button class="secondary-button" type="button" id="save-rec-settings">Save Defaults</button>
          </div>
          <div class="form-grid">
            ${field("Investment amount", "number", "investmentAmount", settings.investmentAmount)}
            ${selectField("Currency", "investmentCurrency", ["CAD", "USD"], settings.investmentCurrency)}
            ${selectField("Risk mode", "riskMode", ["Conservative", "Balanced", "Aggressive"], settings.riskMode)}
            ${field("Max recommendations", "number", "maxRecommendations", settings.maxRecommendations)}
            ${checkboxField("Prefer CAD ETFs", "preferCadEtfs", settings.preferCadEtfs)}
            ${checkboxField("Allow USD tickers", "allowUsdTickers", settings.allowUsdTickers)}
            ${checkboxField("Allow fractional shares", "allowFractionalShares", settings.allowFractionalShares)}
          </div>
          <div class="button-row" style="margin-top: 14px;">
            <button class="primary-button" type="button" id="calculate-recommendations">Calculate</button>
            <button class="ghost-button" type="button" id="copy-recommendation">Copy Recommendation Summary for LLM</button>
          </div>
        </section>
        <section class="panel">
          <div class="panel-header">
            <div>
              <h3>Allocation Chart</h3>
              <p>Main allocation${recommendation.planB.length ? " and active Plan B" : ""}</p>
            </div>
          </div>
          ${renderAllocationChart(recommendation)}
        </section>
      </div>
      <section class="panel">
        <div class="panel-header">
          <div>
            <h3>Main Recommended Buys</h3>
            <p>Only tickers already in the personal watchlist</p>
          </div>
        </div>
        ${noBuy ? `<div class="empty-state">No strong buy candidates today. Consider holding cash or adding only to core ETF positions.</div>` : renderRecommendationTable(recommendation.mainRecommendations)}
      </section>
      <section class="panel">
        <div class="panel-header"><div><h3>${appState.data.settings.useTargetAllocationMode ? "Target Allocation Notes" : "Current Holding Context"}</h3><p>${appState.data.settings.useTargetAllocationMode ? "Optional target allocation mode" : "Information only, never a default block"}</p></div></div>
        ${appState.data.settings.useTargetAllocationMode ? renderWarnings(recommendation.portfolioWarnings || []) : renderHoldingContext(recommendation.holdingContext || [])}
      </section>
      ${recommendation.planB.length ? `<section class="panel">
        <div class="panel-header"><div><h3>Plan B Allocation</h3><p>Alternative for manually skipped recommendations</p></div></div>
        ${renderPlanB(recommendation.planB)}
      </section>` : ""}
      <section class="panel">
        <div class="panel-header"><div><h3>Recommendation Summary</h3><p>Plain-English weekly summary</p></div></div>
        <p>${escapeHtml(recommendation.summary)}</p>
      </section>
    </div>
  `;
}

function renderCards(cards) {
  const normalized = cards.map((card) => Array.isArray(card) ? { label: card[0], value: card[1] } : card);
  return `<div class="cards">${normalized.map((card) => `
    <div class="card">
      <div class="label">${escapeHtml(card.label)}</div>
      <div class="value">${escapeHtml(String(card.value))}</div>
    </div>
  `).join("")}</div>`;
}

function renderRecommendationTable(rows) {
  return `
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Rank</th><th>Ticker</th><th>Name</th><th>Type</th><th>Action</th><th>Final score</th>
            <th>Allocation</th><th>Amount</th><th>Shares</th><th>Main reason</th><th>Key risk</th><th>Current holding</th><th>Actions</th>
          </tr>
        </thead>
        <tbody>
          ${rows.map((row) => `
            <tr>
              <td>${row.rank}</td>
              <td><strong>${escapeHtml(row.ticker)}</strong></td>
              <td>${escapeHtml(row.name)}</td>
              <td>${badge(row.type, "gray")}</td>
              <td>${badge(row.actionLabel, actionColors[row.actionLabel] || "gray")}</td>
              <td class="numeric">${num(row.finalScore)}</td>
              <td class="numeric">${num(row.suggestedAllocationPct)}%</td>
              <td class="numeric">${row.suggestedCurrency} ${money(row.suggestedAmount)}</td>
              <td class="numeric">${num(row.estimatedShares)}</td>
              <td>${escapeHtml(row.dashboardNote)}</td>
              <td>${escapeHtml(row.keyRisk)}</td>
              <td>${escapeHtml(row.holdingContext ? row.holdingContext.note : "Not currently held.")}</td>
              <td><button class="ghost-button" type="button" onclick="skipTicker('${escapeAttr(row.ticker)}')">${appState.skippedTickers.includes(row.ticker) ? "Skipped" : "Skip"}</button></td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function renderWarnings(warnings) {
  if (!warnings.length) return `<div class="empty-state">No recommended ticker is currently above its target allocation.</div>`;
  return `<div class="grid">${warnings.map((warning) => `
    <div class="warning-card">
      <h4>${escapeHtml(warning.ticker)}</h4>
      <p><strong>${num(warning.currentPortfolioWeight)}%</strong> current weight vs <strong>${num(warning.targetAllocation)}%</strong> target.</p>
      <p>Above target by <strong>${num(warning.aboveTargetPp)}</strong> percentage points. Unrealized G/L: <strong>${num(warning.unrealizedGainLossPct)}%</strong>.</p>
      <p>${escapeHtml(warning.warningMessage)}</p>
      <p class="muted">${escapeHtml(warning.whyItMatters)}</p>
    </div>
  `).join("")}</div>`;
}

function renderHoldingContext(contexts) {
  if (!contexts.length) return `<div class="empty-state">No recommended ticker is currently held.</div>`;
  return `<div class="grid">${contexts.map((context) => `
    <div class="plan-card">
      <h4>${escapeHtml(context.ticker)}</h4>
      <p>Shares: <strong>${num(context.currentShares)}</strong></p>
      <p>Portfolio weight: <strong>${num(context.currentPortfolioWeight)}%</strong></p>
      <p>Unrealized G/L: <strong>${num(context.unrealizedGainLossPct)}%</strong></p>
      <p class="muted">${escapeHtml(context.note)}</p>
    </div>
  `).join("")}</div>`;
}

function renderPlanB(planB) {
  if (!planB.length) return `<div class="empty-state">No Plan B needed for the current recommendation.</div>`;
  return `<div class="grid">${planB.map((row) => `
    <div class="plan-card">
      <h4>${escapeHtml(row.ticker)}</h4>
      <p><strong>${appState.data.settings.investmentCurrency} ${money(row.suggestedAmount)}</strong></p>
      <p>${escapeHtml(row.name || "")}</p>
      <p class="muted">${escapeHtml(row.reason || "")}</p>
    </div>
  `).join("")}</div>`;
}

function renderAllocationChart(recommendation) {
  const main = recommendation.mainRecommendations || [];
  const plan = recommendation.planB || [];
  if (!main.length) return `<div class="empty-state">No allocation to chart.</div>`;
  const maxAmount = Math.max(...main.map((row) => row.suggestedAmount), ...plan.map((row) => row.suggestedAmount || 0), 1);
  return `
    <div class="chart">
      ${main.map((row) => barRow(row.ticker, row.suggestedAmount, maxAmount, row.suggestedCurrency)).join("")}
      ${plan.length ? `<hr>${plan.map((row) => barRow(`Plan B ${row.ticker}`, row.suggestedAmount, maxAmount, appState.data.settings.investmentCurrency)).join("")}` : ""}
    </div>
  `;
}

function barRow(label, amount, maxAmount, currency) {
  const width = Math.max(3, Math.round((amount / maxAmount) * 100));
  return `
    <div class="bar-row">
      <strong>${escapeHtml(label)}</strong>
      <div class="bar-track"><div class="bar-fill" style="width: ${width}%"></div></div>
      <span class="numeric">${currency} ${money(amount)}</span>
    </div>
  `;
}

function bindDashboardEvents() {
  document.getElementById("calculate-recommendations")?.addEventListener("click", async () => {
    try {
      const overrides = recommendationInputs();
      appState.data.settings = { ...appState.data.settings, ...overrides };
      appState.data.recommendation = await api("/api/recommendations/calculate", {
        method: "POST",
        body: JSON.stringify(overrides),
      });
      showToast("Recommendation recalculated.");
      render();
    } catch (error) {
      showToast(error.message);
    }
  });
  document.getElementById("save-rec-settings")?.addEventListener("click", async () => {
    try {
      const updates = recommendationInputs();
      delete updates.skippedTickers;
      await api("/api/settings/update", { method: "POST", body: JSON.stringify(updates) });
      showToast("Defaults saved.");
      await loadState();
    } catch (error) {
      showToast(error.message);
    }
  });
  document.getElementById("copy-recommendation")?.addEventListener("click", () => copyExport("recommendation", "llm"));
}

function recommendationInputs() {
  return {
    investmentAmount: Number(document.getElementById("investmentAmount").value || 0),
    investmentCurrency: document.getElementById("investmentCurrency").value,
    riskMode: document.getElementById("riskMode").value,
    maxRecommendations: Number(document.getElementById("maxRecommendations").value || 5),
    preferCadEtfs: document.getElementById("preferCadEtfs").checked,
    allowUsdTickers: document.getElementById("allowUsdTickers").checked,
    allowFractionalShares: document.getElementById("allowFractionalShares").checked,
    skippedTickers: appState.skippedTickers,
  };
}

async function skipTicker(ticker) {
  if (appState.skippedTickers.includes(ticker)) {
    appState.skippedTickers = appState.skippedTickers.filter((item) => item !== ticker);
  } else {
    appState.skippedTickers = [...appState.skippedTickers, ticker];
  }
  try {
    appState.data.recommendation = await api("/api/recommendations/calculate", {
      method: "POST",
      body: JSON.stringify(recommendationInputs()),
    });
    showToast(appState.skippedTickers.includes(ticker) ? `${ticker} skipped for Plan B.` : `${ticker} restored.`);
    render();
  } catch (error) {
    showToast(error.message);
  }
}

function renderWeeklyPicks() {
  const picks = filteredWeeklyPicks();
  const allPicks = appState.data.weeklyPicks;
  return `
    <div class="stack">
      <section class="panel">
        <div class="panel-header"><div><h3>Discovery Filters</h3><p>Weekly picks are research candidates</p></div></div>
        <div class="toolbar">
          ${selectInline("Theme", "picksTheme", ["All", ...unique(allPicks.map((row) => row.theme))], appState.picksTheme)}
          ${selectInline("Type", "picksType", ["All", ...unique(allPicks.map((row) => row.type))], appState.picksType)}
          ${selectInline("Risk", "picksRisk", ["All", "Low", "Medium", "Medium-High", "High"], appState.picksRisk)}
          ${selectInline("Sort", "picksSort", ["score", "recentPerformance", "valuationRisk"], appState.picksSort)}
          <button class="ghost-button" type="button" id="copy-picks">Copy Visible Picks for LLM</button>
        </div>
      </section>
      <section class="panel">
        <div class="panel-header"><div><h3>Weekly Picks</h3><p>${picks.length} visible candidates</p></div></div>
        ${renderWeeklyTable(picks)}
      </section>
    </div>
  `;
}

function filteredWeeklyPicks() {
  const sortKey = appState.picksSort;
  return [...appState.data.weeklyPicks]
    .filter((row) => appState.picksTheme === "All" || row.theme === appState.picksTheme)
    .filter((row) => appState.picksType === "All" || row.type === appState.picksType)
    .filter((row) => appState.picksRisk === "All" || row.riskLevel === appState.picksRisk)
    .sort((a, b) => Number(b[sortKey] || 0) - Number(a[sortKey] || 0));
}

function renderWeeklyTable(rows) {
  if (!rows.length) return `<div class="empty-state">No weekly picks match the filters.</div>`;
  return `
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Ticker</th><th>Name</th><th>Type</th><th>Theme</th><th>Score</th><th>Risk</th>
            <th>Performance</th><th>News</th><th>Reason</th><th>Key risks</th><th>Suggested action</th><th>Actions</th>
          </tr>
        </thead>
        <tbody>
          ${rows.map((row) => `
            <tr>
              <td><strong>${escapeHtml(row.ticker)}</strong></td>
              <td>${escapeHtml(row.name)}</td>
              <td>${badge(row.type, "gray")}</td>
              <td>${escapeHtml(row.theme)}</td>
              <td class="numeric">${num(row.score)}</td>
              <td>${badge(row.riskLevel, riskColors[row.riskLevel] || "gray")}</td>
              <td>${escapeHtml(row.recentPerformanceSummary)}</td>
              <td>${escapeHtml(row.newsSummary)}</td>
              <td>${escapeHtml(row.reasonToResearch)}</td>
              <td>${escapeHtml(row.keyRisks)}</td>
              <td>${escapeHtml(row.suggestedAction)}</td>
              <td>
                <div class="button-row">
                  <button class="secondary-button" type="button" onclick="addWeeklyPick('${escapeAttr(row.ticker)}')">Add</button>
                  <button class="ghost-button" type="button" onclick="copyWeeklyPick('${escapeAttr(row.ticker)}')">Copy</button>
                  <button class="danger-button" type="button" onclick="dismissWeeklyPick('${escapeAttr(row.ticker)}')">Dismiss</button>
                </div>
              </td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function bindWeeklyEvents() {
  ["picksTheme", "picksType", "picksRisk", "picksSort"].forEach((id) => {
    document.getElementById(id)?.addEventListener("change", (event) => {
      appState[id] = event.target.value;
      render();
    });
  });
  document.getElementById("copy-picks")?.addEventListener("click", () => {
    const text = filteredWeeklyPicks().map((row) => `${row.ticker} - ${row.name} - Score ${row.score} - ${row.reasonToResearch} - Risk: ${row.keyRisks}`).join("\n");
    copyText(text, "Visible weekly picks copied.");
  });
}

async function addWeeklyPick(ticker) {
  try {
    await api("/api/weekly-picks/add-to-watchlist", { method: "POST", body: JSON.stringify({ ticker }) });
    showToast(`${ticker} added to watchlist.`);
    await loadState();
  } catch (error) {
    showToast(error.message);
  }
}

async function dismissWeeklyPick(ticker) {
  try {
    await api("/api/weekly-picks/dismiss", { method: "POST", body: JSON.stringify({ ticker }) });
    showToast(`${ticker} dismissed.`);
    await loadState();
  } catch (error) {
    showToast(error.message);
  }
}

async function copyWeeklyPick(ticker) {
  const text = await apiText(`/api/export/weekly-pick?format=${encodeURIComponent(ticker)}`);
  copyText(text, `${ticker} copied for LLM.`);
}

function renderWatchlist() {
  const rows = filteredWatchlist();
  const selected = appState.data.watchlistAnalysis.find((row) => row.ticker === appState.selectedTicker) || rows[0];
  if (selected) appState.selectedTicker = selected.ticker;
  return `
    <div class="stack">
      <section class="panel">
        <div class="panel-header"><div><h3>Watchlist Controls</h3><p>Personal watchlist only</p></div></div>
        <div class="toolbar">
          <form id="add-watchlist-form" class="toolbar">
            <div class="field"><label for="manualTicker">Ticker</label><input id="manualTicker" placeholder="VFV.TO" autocomplete="off"></div>
            <button class="primary-button" type="submit">Add Ticker</button>
          </form>
          <div class="field"><label for="watchQuery">Search</label><input id="watchQuery" value="${escapeAttr(appState.watchQuery)}" placeholder="Ticker, theme, note"></div>
          ${selectInline("Type", "watchType", ["All", "US Stock", "US ETF", "CAD ETF"], appState.watchType)}
          ${selectInline("Risk", "watchRisk", ["All", "Low", "Medium", "Medium-High", "High"], appState.watchRisk)}
          ${selectInline("Sort", "watchSort", ["finalScore", "riskLevel", "latestClose", "earningsDate", "return3m", "volatility"], appState.watchSort)}
          <button class="ghost-button" type="button" id="export-watch-csv">Export CSV</button>
          <button class="ghost-button" type="button" id="export-watch-json">Export JSON</button>
          <button class="ghost-button" type="button" id="copy-watchlist">Copy All for LLM</button>
        </div>
      </section>
      <section class="panel">
        <div class="panel-header"><div><h3>Stocks and ETFs</h3><p>${rows.length} visible watchlist rows</p></div></div>
        ${renderWatchlistTable(rows)}
      </section>
      <section class="panel">
        <div class="panel-header"><div><h3>Detail</h3><p>${selected ? selected.ticker : "No ticker selected"}</p></div></div>
        ${selected ? renderWatchDetail(selected) : `<div class="empty-state">Add a ticker to see watchlist details.</div>`}
      </section>
    </div>
  `;
}

function filteredWatchlist() {
  const query = appState.watchQuery.trim().toLowerCase();
  const rows = [...appState.data.watchlistAnalysis]
    .filter((row) => appState.watchType === "All" || row.type === appState.watchType)
    .filter((row) => appState.watchRisk === "All" || row.riskLevel === appState.watchRisk)
    .filter((row) => !query || [row.ticker, row.name, row.theme, row.personalNote].join(" ").toLowerCase().includes(query));
  const key = appState.watchSort;
  return rows.sort((a, b) => {
    if (key === "riskLevel") return String(a.riskLevel).localeCompare(String(b.riskLevel));
    if (key === "earningsDate") return String(a.earningsDate || "9999").localeCompare(String(b.earningsDate || "9999"));
    return Number(b[key] || 0) - Number(a[key] || 0);
  });
}

function renderWatchlistTable(rows) {
  if (!rows.length) return `<div class="empty-state">No watchlist rows match the filters.</div>`;
  const targetMode = Boolean(appState.data.settings.useTargetAllocationMode);
  return `
    <div class="table-wrap">
      <table class="compact-table">
        <thead>
          <tr>
            <th class="sticky-col">Ticker</th><th>Name</th><th>Type</th><th>Risk</th><th>Price</th><th>3M return</th>
            <th>Score</th><th>Action</th><th>Notes / Details</th>
          </tr>
        </thead>
        <tbody>
          ${rows.map((row) => `
            <tr class="${appState.selectedTicker === row.ticker ? "selected" : ""}">
              <td class="sticky-col"><button class="ghost-button" type="button" onclick="selectTicker('${escapeAttr(row.ticker)}')">${escapeHtml(row.ticker)}</button></td>
              <td>${escapeHtml(row.name)}</td>
              <td>${badge(row.type, "gray")}</td>
              <td>${badge(row.riskLevel, riskColors[row.riskLevel] || "gray")}</td>
              <td>${escapeHtml(row.currency || "")} ${num(row.latestClose)}</td>
              <td class="numeric">${num(row.return3m)}%</td>
              <td class="numeric">${num(row.finalScore)}</td>
              <td>${badge(row.actionLabel, actionColors[row.actionLabel] || "gray")}</td>
              <td>
                <div class="button-row">
                  <button class="ghost-button" type="button" onclick="toggleWatchDetails('${escapeAttr(row.ticker)}')">${appState.expandedWatchRows.includes(row.ticker) ? "Hide" : "Details"}</button>
                  <button class="ghost-button" type="button" onclick="toggleWatchDisabled('${escapeAttr(row.ticker)}', ${!row.manualDisabled})">${row.manualDisabled ? "Enable" : "Disable"}</button>
                  <button class="danger-button" type="button" onclick="removeWatchTicker('${escapeAttr(row.ticker)}')">Remove</button>
                </div>
              </td>
            </tr>
            ${appState.expandedWatchRows.includes(row.ticker) ? `
              <tr class="detail-row">
                <td colspan="9">
                  <div class="detail-grid">
                    ${metric("Theme", row.theme || "N/A")}
                    ${metric("Volatility", pct(row.volatility))}
                    ${metric("Earnings", row.earningsDate || "N/A")}
                    ${metric("Valuation / cost score", row.valuationScore || row.costScore || "N/A")}
                    ${metric("50-day MA", row.ma50 || "N/A")}
                    ${metric("200-day MA", row.ma200 || "N/A")}
                    ${targetMode ? `<div class="metric"><span>Target allocation</span><strong><input class="small-input" type="number" value="${num(row.targetAllocation)}" onchange="updateWatchTarget('${escapeAttr(row.ticker)}', this.value)">%</strong></div>` : ""}
                    <div class="metric wide-metric"><span>Personal note</span><strong><input class="note-input" value="${escapeAttr(row.personalNote || "")}" onchange="updateWatchNote('${escapeAttr(row.ticker)}', this.value)"></strong></div>
                  </div>
                </td>
              </tr>
            ` : ""}
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function renderWatchDetail(row) {
  const tabs = row.type === "US Stock"
    ? ["Overview", "Trend", "Risk", "Valuation", "Growth & Profitability", "Events / Earnings / News"]
    : ["Overview", "Exposure", "Cost", "Risk / Trend", "Tracking Quality"];
  if (!tabs.includes(appState.detailTab)) appState.detailTab = tabs[0];
  return `
    <div class="tabs">${tabs.map((tab) => `<button class="${appState.detailTab === tab ? "active" : ""}" type="button" onclick="setDetailTab('${escapeAttr(tab)}')">${escapeHtml(tab)}</button>`).join("")}</div>
    <div class="metric-grid">${metricRowsForTab(row, appState.detailTab).map(([label, value]) => metric(label, value)).join("")}</div>
  `;
}

function metricRowsForTab(row, tab) {
  const stock = {
    Overview: [["Latest close", `${row.currency} ${num(row.latestClose)}`], ["Market cap", row.marketCap], ["Sector", row.sector], ["Dividend yield", pct(row.dividendYield)], ["Final score", row.finalScore], ["Action", row.actionLabel], ["Dashboard note", row.dashboardNote], ["Personal note", row.personalNote || "N/A"]],
    Trend: [["1W return", pct(row.return1w)], ["1M return", pct(row.return1m)], ["3M return", pct(row.return3m)], ["6M return", pct(row.return6m)], ["1Y return", pct(row.return1y)], ["52W high", row.week52High], ["52W low", row.week52Low], ["Distance from high", pct(row.distanceFrom52WeekHigh)], ["Distance from low", pct(row.distanceFrom52WeekLow)], ["50-day MA", row.ma50], ["200-day MA", row.ma200], ["RSI", row.rsi]],
    Risk: [["Risk level", row.riskLevel], ["Volatility", pct(row.volatility)], ["Beta", row.beta], ["Risk score", row.riskScore], ["Key risk", row.keyRisk]],
    Valuation: [["P/E ratio", row.peRatio], ["Forward P/E", row.forwardPe], ["Valuation score", row.valuationScore]],
    "Growth & Profitability": [["Revenue growth", pct(row.revenueGrowth)], ["EPS growth", pct(row.epsGrowth)], ["Profit margin", pct(row.profitMargin)], ["Growth score", row.growthProfitabilityScore]],
    "Events / Earnings / News": [["Earnings date", row.earningsDate || "N/A"], ["News/event score", row.newsEventScore], ["Earnings risk score", row.earningsRiskScore], ["News summary", row.newsSummary || "news unavailable"]],
  };
  const etf = {
    Overview: [["Latest close", `${row.currency} ${num(row.latestClose)}`], ["Fund type", row.type], ["Dividend yield", pct(row.dividendYield)], ["Final score", row.finalScore], ["Action", row.actionLabel], ["Dashboard note", row.dashboardNote], ["Personal note", row.personalNote || "N/A"]],
    Exposure: [["Theme", row.theme], ["Top holdings", listText(row.topHoldings)], ["Sector exposure", listText(row.sectorExposure)], ["Exposure score", row.exposureScore]],
    Cost: [["MER / expense ratio", pct(row.expenseRatio)], ["AUM", row.aum || "N/A"], ["Cost score", row.costScore], ["Liquidity score", row.liquidityScore]],
    "Risk / Trend": [["1M return", pct(row.return1m)], ["3M return", pct(row.return3m)], ["6M return", pct(row.return6m)], ["1Y return", pct(row.return1y)], ["52W high", row.week52High], ["52W low", row.week52Low], ["50-day MA", row.ma50], ["200-day MA", row.ma200], ["RSI", row.rsi], ["Volatility", pct(row.volatility)], ["Risk/trend score", row.riskTrendScore]],
    "Tracking Quality": [["Tracking quality score", row.trackingQualityScore], ["Key risk", row.keyRisk], ["News summary", row.newsSummary || "news unavailable"]],
  };
  return (row.type === "US Stock" ? stock : etf)[tab] || [];
}

function bindWatchlistEvents() {
  document.getElementById("add-watchlist-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const ticker = document.getElementById("manualTicker").value;
    try {
      await api("/api/watchlist/add", { method: "POST", body: JSON.stringify({ ticker }) });
      showToast(`${ticker.toUpperCase()} added.`);
      await loadState();
    } catch (error) {
      showToast(error.message);
    }
  });
  document.getElementById("watchQuery")?.addEventListener("input", (event) => {
    appState.watchQuery = event.target.value;
    render();
  });
  ["watchType", "watchRisk", "watchSort"].forEach((id) => {
    document.getElementById(id)?.addEventListener("change", (event) => {
      appState[id] = event.target.value;
      render();
    });
  });
  document.getElementById("export-watch-csv")?.addEventListener("click", () => openExport("watchlist", "csv"));
  document.getElementById("export-watch-json")?.addEventListener("click", () => openExport("watchlist", "json"));
  document.getElementById("copy-watchlist")?.addEventListener("click", () => copyExport("watchlist", "llm"));
}

function selectTicker(ticker) {
  appState.selectedTicker = ticker;
  render();
}

function setDetailTab(tab) {
  appState.detailTab = tab;
  render();
}

function toggleWatchDetails(ticker) {
  if (appState.expandedWatchRows.includes(ticker)) {
    appState.expandedWatchRows = appState.expandedWatchRows.filter((item) => item !== ticker);
  } else {
    appState.expandedWatchRows = [...appState.expandedWatchRows, ticker];
  }
  render();
}

async function updateWatchTarget(ticker, value) {
  await updateWatch(ticker, { targetAllocation: Number(value || 0) });
}

async function updateWatchNote(ticker, value) {
  await updateWatch(ticker, { personalNote: value });
}

async function toggleWatchDisabled(ticker, value) {
  await updateWatch(ticker, { manualDisabled: value });
}

async function updateWatch(ticker, updates) {
  try {
    await api("/api/watchlist/update", { method: "POST", body: JSON.stringify({ ticker, ...updates }) });
    showToast(`${ticker} updated.`);
    await loadState();
  } catch (error) {
    showToast(error.message);
  }
}

async function removeWatchTicker(ticker) {
  try {
    await api("/api/watchlist/remove", { method: "POST", body: JSON.stringify({ ticker }) });
    showToast(`${ticker} removed.`);
    await loadState();
  } catch (error) {
    showToast(error.message);
  }
}

function renderPortfolio() {
  const { portfolioSummary, holdings, transactions } = appState.data;
  const cards = [
    ["Total portfolio value", `CAD ${money(portfolioSummary.totalPortfolioValueCad)}`],
    ["Total invested", `CAD ${money(portfolioSummary.totalInvestedCad)}`],
    ["Unrealized G/L", `CAD ${money(portfolioSummary.unrealizedGainLossCad)}`],
    ["Realized G/L", `CAD ${money(portfolioSummary.realizedGainLossCad)}`],
    ["Total return", `${num(portfolioSummary.totalReturnPct)}%`],
    ["Top holding", portfolioSummary.topHolding],
    ["Trim / sell alerts", portfolioSummary.trimSellAlertCount],
    ["Cash reserve", `CAD ${money(portfolioSummary.cashReserveCad)}`],
  ];
  if (appState.data.settings.useTargetAllocationMode) {
    cards.splice(6, 0, ["Above target positions", portfolioSummary.aboveTargetCount]);
  }
  return `
    <div class="stack">
      ${renderCards(cards)}
      <section class="panel">
        <div class="panel-header"><div><h3>Transaction Entry</h3><p>Manual brokerage records</p></div></div>
        ${renderTransactionForm()}
      </section>
      <section class="panel">
        <div class="panel-header">
          <div><h3>Current Holdings</h3><p>Calculated from transactions</p></div>
          <button class="ghost-button" type="button" id="copy-holdings">Copy Holdings Summary for LLM</button>
        </div>
        ${renderHoldingsTable(holdings)}
      </section>
      <section class="panel">
        <div class="panel-header"><div><h3>Transaction Ledger</h3><p>${transactions.length} transactions</p></div></div>
        ${renderTransactionsTable(transactions)}
      </section>
    </div>
  `;
}

function renderTransactionForm() {
  const editing = appState.data.transactions.find((txn) => txn.id === appState.editingTransactionId);
  const dateValue = editing ? editing.date.slice(0, 16) : new Date().toISOString().slice(0, 16);
  return `
    <form id="transaction-form" class="form-grid">
      <input type="hidden" id="txnId" value="${escapeAttr(editing?.id || "")}">
      ${field("Ticker", "text", "txnTicker", editing?.ticker || "")}
      ${selectField("Action", "txnAction", ["Buy", "Sell"], editing?.action || "Buy")}
      ${field("Shares", "number", "txnShares", editing?.shares || "", "0.0001")}
      ${field("Price", "number", "txnPrice", editing?.price || "", "0.01")}
      ${selectField("Currency", "txnCurrency", ["CAD", "USD"], editing?.currency || "USD")}
      ${field("Date", "datetime-local", "txnDate", dateValue)}
      <div class="field"><label for="txnNotes">Notes</label><input id="txnNotes" value="${escapeAttr(editing?.notes || "")}"></div>
      <div class="button-row">
        <button class="primary-button" type="submit">${editing ? "Update" : "Add"} Transaction</button>
        ${editing ? `<button class="ghost-button" type="button" id="cancel-txn-edit">Cancel</button>` : ""}
      </div>
    </form>
  `;
}

function renderHoldingsTable(rows) {
  if (!rows.length) return `<div class="empty-state">No holdings yet. Add buy transactions to populate this table.</div>`;
  const targetMode = Boolean(appState.data.settings.useTargetAllocationMode);
  return `
    <div class="table-wrap">
      <table class="compact-table">
        <thead>
          <tr>
            <th class="sticky-col">Ticker</th><th>Shares</th><th>Avg cost</th><th>Current price</th><th>Market value</th>
            <th>Weight %</th><th>Unrealized G/L %</th><th>Action</th><th>Details</th>
          </tr>
        </thead>
        <tbody>
          ${rows.map((row) => `
            <tr>
              <td class="sticky-col"><strong>${escapeHtml(row.ticker)}</strong></td>
              <td class="numeric">${num(row.shares)}</td>
              <td class="numeric">${row.currency} ${money(row.averageCost)}</td>
              <td class="numeric">${row.currency} ${money(row.currentPrice)}</td>
              <td class="numeric">CAD ${money(row.currentMarketValueCad)}</td>
              <td class="numeric">${num(row.portfolioWeight)}%</td>
              <td class="numeric">${num(row.unrealizedGainLossPct)}%</td>
              <td>${badge(row.currentActionLabel, actionColors[row.currentActionLabel] || "gray")}</td>
              <td><button class="ghost-button" type="button" onclick="toggleHoldingDetails('${escapeAttr(row.ticker)}')">${appState.expandedHoldingRows.includes(row.ticker) ? "Hide" : "Details"}</button></td>
            </tr>
            ${appState.expandedHoldingRows.includes(row.ticker) ? `
              <tr class="detail-row">
                <td colspan="9">
                  <div class="detail-grid">
                    ${metric("Name", row.name)}
                    ${metric("Type", row.type)}
                    ${metric("Invested amount", `CAD ${money(row.totalInvestedCad)}`)}
                    ${metric("Unrealized G/L", `CAD ${money(row.unrealizedGainLossCad)}`)}
                    ${metric("Realized G/L", `CAD ${money(row.realizedGainLossCad)}`)}
                    ${targetMode ? metric("Target allocation", `${num(row.targetAllocation)}%`) : ""}
                    ${targetMode ? metric("Difference from target", `${num(row.differenceFromTarget)} pp`) : ""}
                    ${metric("Risk flags", listText(row.riskFlags))}
                    ${metric("Notes", row.notes || "N/A")}
                  </div>
                  ${targetMode ? `<div class="button-row detail-actions"><label class="field inline-field"><span>Target allocation</span><input type="number" value="${num(row.targetAllocation)}" onchange="updateHoldingTarget('${escapeAttr(row.ticker)}', this.value)"></label></div>` : ""}
                </td>
              </tr>
            ` : ""}
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function renderTransactionsTable(rows) {
  if (!rows.length) return `<div class="empty-state">No transactions recorded.</div>`;
  return `
    <div class="table-wrap">
      <table>
        <thead>
          <tr><th>Date</th><th>Ticker</th><th>Action</th><th>Shares</th><th>Price</th><th>Currency</th><th>Total</th><th>Notes</th><th>Edit</th><th>Delete</th></tr>
        </thead>
        <tbody>
          ${rows.map((row) => `
            <tr>
              <td>${escapeHtml(row.date)}</td>
              <td><strong>${escapeHtml(row.ticker)}</strong></td>
              <td>${badge(row.action, row.action === "Buy" ? "green" : "orange")}</td>
              <td class="numeric">${num(row.shares)}</td>
              <td class="numeric">${money(row.price)}</td>
              <td>${escapeHtml(row.currency)}</td>
              <td class="numeric">${escapeHtml(row.currency)} ${money(Number(row.shares) * Number(row.price))}</td>
              <td>${escapeHtml(row.notes || "")}</td>
              <td><button class="ghost-button" type="button" onclick="editTransaction('${escapeAttr(row.id)}')">Edit</button></td>
              <td><button class="danger-button" type="button" onclick="deleteTransaction('${escapeAttr(row.id)}')">Delete</button></td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function bindPortfolioEvents() {
  document.getElementById("copy-holdings")?.addEventListener("click", () => copyExport("holdings", "llm"));
  document.getElementById("cancel-txn-edit")?.addEventListener("click", () => {
    appState.editingTransactionId = null;
    render();
  });
  document.getElementById("txnTicker")?.addEventListener("blur", autofillTransactionPrice);
  document.getElementById("transaction-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = {
      id: document.getElementById("txnId").value || undefined,
      ticker: document.getElementById("txnTicker").value,
      action: document.getElementById("txnAction").value,
      shares: Number(document.getElementById("txnShares").value || 0),
      price: Number(document.getElementById("txnPrice").value || 0),
      currency: document.getElementById("txnCurrency").value,
      date: document.getElementById("txnDate").value,
      notes: document.getElementById("txnNotes").value,
    };
    const path = payload.id ? "/api/transactions/update" : "/api/transactions/add";
    try {
      await api(path, { method: "POST", body: JSON.stringify(payload) });
      appState.editingTransactionId = null;
      showToast("Transaction saved.");
      await loadState();
    } catch (error) {
      showToast(error.message);
    }
  });
}

function autofillTransactionPrice() {
  const ticker = document.getElementById("txnTicker").value.trim().toUpperCase();
  const row = appState.data.watchlistAnalysis.find((item) => item.ticker === ticker) || appState.data.holdings.find((item) => item.ticker === ticker);
  if (ticker.endsWith(".TO")) document.getElementById("txnCurrency").value = "CAD";
  if (ticker && !ticker.endsWith(".TO")) document.getElementById("txnCurrency").value = "USD";
  if (row?.latestClose || row?.currentPrice) document.getElementById("txnPrice").value = row.latestClose || row.currentPrice;
}

function editTransaction(id) {
  appState.editingTransactionId = id;
  render();
}

function toggleHoldingDetails(ticker) {
  if (appState.expandedHoldingRows.includes(ticker)) {
    appState.expandedHoldingRows = appState.expandedHoldingRows.filter((item) => item !== ticker);
  } else {
    appState.expandedHoldingRows = [...appState.expandedHoldingRows, ticker];
  }
  render();
}

async function deleteTransaction(id) {
  try {
    await api("/api/transactions/delete", { method: "POST", body: JSON.stringify({ id }) });
    showToast("Transaction deleted.");
    await loadState();
  } catch (error) {
    showToast(error.message);
  }
}

async function updateHoldingTarget(ticker, targetAllocation) {
  try {
    await api("/api/holdings/target", { method: "POST", body: JSON.stringify({ ticker, targetAllocation: Number(targetAllocation || 0) }) });
    showToast(`${ticker} target updated.`);
    await loadState();
  } catch (error) {
    showToast(error.message);
  }
}

function renderSettings() {
  const settings = appState.data.settings;
  return `
    <div class="stack">
      <section class="panel">
        <div class="panel-header"><div><h3>Settings</h3><p>Stored in data/settings.json</p></div></div>
        <form id="settings-form" class="form-grid">
          ${checkboxField("Prefer CAD ETFs", "setPreferCadEtfs", settings.preferCadEtfs)}
          ${checkboxField("Allow USD tickers", "setAllowUsdTickers", settings.allowUsdTickers)}
          ${selectField("Investment currency", "setInvestmentCurrency", ["CAD", "USD"], settings.investmentCurrency)}
          ${selectField("Risk mode", "setRiskMode", ["Conservative", "Balanced", "Aggressive"], settings.riskMode)}
          ${field("Max recommendations", "number", "setMaxRecommendations", settings.maxRecommendations)}
          ${field("Max single stock allocation %", "number", "setMaxSingleStockAllocation", settings.maxSingleStockAllocation)}
          ${field("Max single ETF allocation %", "number", "setMaxSingleEtfAllocation", settings.maxSingleEtfAllocation)}
          ${field("Max high-risk stock allocation %", "number", "setMaxHighRiskStockAllocation", settings.maxHighRiskStockAllocation)}
          ${checkboxField("Use target allocation mode", "setUseTargetAllocationMode", settings.useTargetAllocationMode)}
          ${settings.useTargetAllocationMode ? checkboxField("Treat target allocation as advisory", "setTreatOverweightAdvisory", !settings.treatOverweightAsHardConstraint) : ""}
          ${selectField("Notification method", "setNotificationMethod", ["Email", "Telegram", "Slack", "Discord", "None"], settings.notificationMethod)}
          ${selectField("LLM mode", "setLlmMode", ["Manual copy-to-LLM", "API mode", "Disabled"], settings.llmMode)}
          ${selectField("Weekly run schedule", "setWeeklyRunSchedule", ["once per week"], settings.weeklyRunSchedule)}
          ${field("Mock USD/CAD FX", "number", "setFxUsdCad", settings.fxUsdCad, "0.01")}
          ${field("Cash reserve CAD", "number", "setCashReserveCad", settings.cashReserveCad, "0.01")}
          <div class="button-row"><button class="primary-button" type="submit">Save Settings</button></div>
        </form>
      </section>
      <section class="panel">
        <div class="panel-header"><div><h3>Candidate Universe Editor</h3><p>JSON array</p></div></div>
        <textarea id="candidateUniverseEditor" class="settings-editor">${escapeHtml(JSON.stringify(appState.data.candidateUniverse, null, 2))}</textarea>
        <div class="button-row" style="margin-top: 12px;">
          <button class="primary-button" type="button" id="save-universe">Save Universe</button>
        </div>
      </section>
      <section class="panel">
        <div class="panel-header"><div><h3>Optional Providers</h3><p>Configured later through environment variables</p></div></div>
        <div class="metric-grid">
          ${metric("TAVILY_API_KEY", "optional")}
          ${metric("BRAVE_SEARCH_API_KEY", "optional")}
          ${metric("SERPAPI_API_KEY", "optional")}
          ${metric("OPENAI_API_KEY", "optional")}
        </div>
      </section>
    </div>
  `;
}

function bindSettingsEvents() {
  document.getElementById("settings-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const updates = {
      preferCadEtfs: document.getElementById("setPreferCadEtfs").checked,
      allowUsdTickers: document.getElementById("setAllowUsdTickers").checked,
      investmentCurrency: document.getElementById("setInvestmentCurrency").value,
      riskMode: document.getElementById("setRiskMode").value,
      maxRecommendations: Number(document.getElementById("setMaxRecommendations").value || 5),
      maxSingleStockAllocation: Number(document.getElementById("setMaxSingleStockAllocation").value || 20),
      maxSingleEtfAllocation: Number(document.getElementById("setMaxSingleEtfAllocation").value || 50),
      maxHighRiskStockAllocation: Number(document.getElementById("setMaxHighRiskStockAllocation").value || 10),
      useTargetAllocationMode: document.getElementById("setUseTargetAllocationMode").checked,
      treatOverweightAsHardConstraint: document.getElementById("setTreatOverweightAdvisory") ? !document.getElementById("setTreatOverweightAdvisory").checked : false,
      notificationMethod: document.getElementById("setNotificationMethod").value,
      llmMode: document.getElementById("setLlmMode").value,
      weeklyRunSchedule: document.getElementById("setWeeklyRunSchedule").value,
      fxUsdCad: Number(document.getElementById("setFxUsdCad").value || 1.37),
      cashReserveCad: Number(document.getElementById("setCashReserveCad").value || 0),
    };
    try {
      await api("/api/settings/update", { method: "POST", body: JSON.stringify(updates) });
      showToast("Settings saved.");
      await loadState();
    } catch (error) {
      showToast(error.message);
    }
  });
  document.getElementById("save-universe")?.addEventListener("click", async () => {
    try {
      const items = JSON.parse(document.getElementById("candidateUniverseEditor").value);
      await api("/api/settings/update-universe", { method: "POST", body: JSON.stringify({ items }) });
      showToast("Candidate universe saved.");
      await loadState();
    } catch (error) {
      showToast(error.message);
    }
  });
}

function field(label, type, id, value = "", step = "1") {
  return `<div class="field"><label for="${id}">${label}</label><input id="${id}" type="${type}" step="${step}" value="${escapeAttr(value ?? "")}"></div>`;
}

function selectField(label, id, options, value) {
  return `<div class="field"><label for="${id}">${label}</label><select id="${id}">${options.map((option) => `<option value="${escapeAttr(option)}" ${option === value ? "selected" : ""}>${escapeHtml(option)}</option>`).join("")}</select></div>`;
}

function checkboxField(label, id, checked) {
  return `<label class="checkbox-field" for="${id}"><input id="${id}" type="checkbox" ${checked ? "checked" : ""}> ${label}</label>`;
}

function selectInline(label, id, options, value) {
  return `<div class="field"><label for="${id}">${label}</label><select id="${id}">${options.map((option) => `<option value="${escapeAttr(option)}" ${option === value ? "selected" : ""}>${escapeHtml(option)}</option>`).join("")}</select></div>`;
}

function metric(label, value) {
  return `<div class="metric"><span>${escapeHtml(label)}</span><strong>${escapeHtml(display(value))}</strong></div>`;
}

function badge(label, color) {
  return `<span class="badge ${color || "gray"}">${escapeHtml(label || "N/A")}</span>`;
}

function money(value) {
  const number = Number(value || 0);
  return number.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function num(value) {
  if (value === null || value === undefined || value === "") return "N/A";
  const number = Number(value);
  if (Number.isNaN(number)) return String(value);
  return Number.isInteger(number) ? String(number) : number.toFixed(1).replace(/\.0$/, "");
}

function pct(value) {
  if (value === null || value === undefined || value === "") return "N/A";
  return `${num(value)}%`;
}

function display(value) {
  if (value === null || value === undefined || value === "") return "N/A";
  if (Array.isArray(value)) return value.length ? value.join(", ") : "N/A";
  return String(value);
}

function listText(value) {
  if (!value) return "N/A";
  if (Array.isArray(value)) return value.join(", ");
  return String(value);
}

function unique(values) {
  return [...new Set(values.filter(Boolean))].sort();
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function escapeAttr(value) {
  return escapeHtml(value);
}

async function copyExport(kind, format) {
  try {
    const text = await apiText(`/api/export/${kind}?format=${encodeURIComponent(format)}`);
    copyText(text, "Copied for LLM.");
  } catch (error) {
    showToast(error.message);
  }
}

function openExport(kind, format) {
  window.open(`/api/export/${kind}?format=${encodeURIComponent(format)}`, "_blank");
}

async function copyText(text, message = "Copied.") {
  try {
    await navigator.clipboard.writeText(text);
    showToast(message);
  } catch {
    const area = document.createElement("textarea");
    area.value = text;
    document.body.appendChild(area);
    area.select();
    document.execCommand("copy");
    document.body.removeChild(area);
    showToast(message);
  }
}

function showToast(message) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.classList.add("visible");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => toast.classList.remove("visible"), 2400);
}

window.setView = setView;
window.skipTicker = skipTicker;
window.addWeeklyPick = addWeeklyPick;
window.dismissWeeklyPick = dismissWeeklyPick;
window.copyWeeklyPick = copyWeeklyPick;
window.selectTicker = selectTicker;
window.setDetailTab = setDetailTab;
window.toggleWatchDetails = toggleWatchDetails;
window.updateWatchTarget = updateWatchTarget;
window.updateWatchNote = updateWatchNote;
window.toggleWatchDisabled = toggleWatchDisabled;
window.removeWatchTicker = removeWatchTicker;
window.editTransaction = editTransaction;
window.toggleHoldingDetails = toggleHoldingDetails;
window.deleteTransaction = deleteTransaction;
window.updateHoldingTarget = updateHoldingTarget;
