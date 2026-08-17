const $ = (selector) => document.querySelector(selector);
let dashboard = null;

const number = (value, digits = 2) => Number(value || 0).toLocaleString("ko-KR", { maximumFractionDigits: digits });
const money = (value, currency = "KRW") => {
  try { return new Intl.NumberFormat("ko-KR", { style: "currency", currency, maximumFractionDigits: currency === "KRW" ? 0 : 2 }).format(Number(value || 0)); }
  catch { return number(value); }
};
const html = (value) => String(value ?? "").replace(/[&<>'"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[character]));
const signClass = (value) => Number(value) < 0 ? "down" : "up";
function sparkline(points, change) {
  if (!points || points.length < 2) return "<span class=\"spark-empty\">—</span>";
  const min = Math.min(...points), max = Math.max(...points), span = max - min || 1;
  const coords = points.map((point, index) => `${(index / (points.length - 1)) * 100},${34 - ((point - min) / span) * 28}`).join(" ");
  const color = Number(change) < 0 ? "#ff718c" : "#4f9dff";
  return `<svg class="sparkline" viewBox="0 0 100 38" preserveAspectRatio="none" aria-hidden="true"><polyline points="${coords}" fill="none" stroke="${color}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/><polyline points="0,37 ${coords} 100,37" fill="${color}18" stroke="none"/></svg>`;
}

async function api(url, options = {}) {
  const response = await fetch(url, options);
  const result = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(result.detail || result.message || "요청을 처리하지 못했습니다.");
  return result;
}

let toastTimer;
let assetRecords = [];
function toast(message, isError = false) {
  const element = $("#toast"); element.textContent = message; element.className = `toast show${isError ? " error" : ""}`;
  clearTimeout(toastTimer); toastTimer = setTimeout(() => { element.className = "toast"; }, 3600);
}
function busy(button, enabled) {
  if (!button) return;
  button.dataset.label ??= button.textContent;
  button.disabled = enabled; button.textContent = enabled ? "처리 중…" : button.dataset.label;
}
async function action(button, request, after = loadDashboard) {
  busy(button, true);
  try { const result = await request(); toast(result.message || "반영했습니다."); if (after) await after(); }
  catch (error) { toast(error.message, true); }
  finally { busy(button, false); }
}

function chartPath(points, width = 900, height = 260, pad = 24) {
  if (!points.length) return "";
  const values = points.map((point) => Number(point.total_value_krw ?? point.value_krw ?? 0));
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  return points.map((point, index) => {
    const x = pad + ((width - pad * 2) * index) / Math.max(points.length - 1, 1);
    const y = height - pad - ((Number(point.total_value_krw ?? point.value_krw ?? 0) - min) / span) * (height - pad * 2);
    return `${x},${y}`;
  }).join(" ");
}

function renderAssetRecords(records) {
  assetRecords = [...records].sort((a, b) => String(b.date || "").localeCompare(String(a.date || "")));
  const wrap = $("#assetChart");
  if (!assetRecords.length) {
    wrap.innerHTML = '<div class="empty">아직 자산기록이 없습니다. 오늘 기록을 저장해 보세요.</div>';
    $("#assetRecordList").innerHTML = "";
    $("#recordCount").textContent = "0개 기록";
    return;
  }
  const chartRecords = [...assetRecords].sort((a, b) => String(a.date || "").localeCompare(String(b.date || "")));
  const values = chartRecords.map((item) => Number(item.total_value_krw || 0));
  const min = Math.min(...values);
  const max = Math.max(...values);
  const path = chartPath(chartRecords);
  const baseline = `${24},${236} ${876},${236}`;
  const first = chartRecords[0];
  const last = chartRecords.at(-1);
  wrap.innerHTML = `
    <svg class="record-chart" viewBox="0 0 900 260" preserveAspectRatio="none" aria-label="자산 기록 차트">
      <defs>
        <linearGradient id="recordFill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#8e70fa" stop-opacity="0.35" />
          <stop offset="100%" stop-color="#8e70fa" stop-opacity="0" />
        </linearGradient>
      </defs>
      <line x1="24" y1="236" x2="876" y2="236" stroke="#2a3557" stroke-width="1" />
      <polyline points="${path}" fill="none" stroke="#8e70fa" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round" />
      <polyline points="${path} ${baseline}" fill="url(#recordFill)" stroke="none" />
    </svg>
    <div class="record-chart-meta">
      <div><span>최초 기록</span><strong>${html(first.date)}</strong><small>${money(first.total_value_krw)}</small></div>
      <div><span>최근 기록</span><strong>${html(last.date)}</strong><small>${money(last.total_value_krw)}</small></div>
      <div><span>최저 / 최고</span><strong>${money(min)} / ${money(max)}</strong><small>총 ${number(assetRecords.length, 0)}개</small></div>
    </div>`;
  const delta = Number(last.total_value_krw || 0) - Number(first.total_value_krw || 0);
  const deltaRate = Number(first.total_value_krw || 0) ? delta / Number(first.total_value_krw || 0) * 100 : 0;
  $("#recordSummary").textContent = `${money(delta)} (${deltaRate >= 0 ? "+" : ""}${number(deltaRate)}%)`;
  $("#recordSummary").className = signClass(delta);
  $("#recordCount").textContent = `${number(assetRecords.length, 0)}개 기록`;
  $("#assetRecordList").innerHTML = assetRecords.map((item) => `
    <div class="record-row">
      <div class="record-row-main">
        <strong>${html(item.date)}</strong>
        <span>${money(item.total_value_krw)} · ${number(item.holding_count, 0)}종목</span>
      </div>
      <div class="record-row-values">
        <b>${money(item.day_profit_krw || 0)}</b>
        <small>${html(item.memo || item.source || "")}</small>
      </div>
      <div class="record-row-actions">
        <button class="button secondary tiny" data-record-edit="${item.id}" type="button">수정</button>
        <button class="button text danger tiny" data-record-delete="${item.id}" type="button">삭제</button>
      </div>
    </div>
  `).join("");
}

function renderMarkets(result) {
  const rows = [...result.markets, {
    symbol: "USD/KRW", label: "달러/원", note: "토스 실시간 환율", price: result.exchange_rate.rate,
    currency: "KRW", change_rate: null, updated_at: result.exchange_rate.valid_until,
  }];
  $("#marketGrid").innerHTML = rows.map((item) => {
    const currency = item.symbol === "KOSPI" || item.symbol === "USD/KRW" ? null : item.currency;
    const price = currency ? money(item.price, currency) : number(item.price);
    const change = item.change_rate == null ? "실시간 기준가" : `${item.change_rate >= 0 ? "+" : ""}${number(item.change_rate)}%`;
    return `<article class="market-card"><div class="market-copy"><span class="symbol">${html(item.symbol)}</span><p>${html(item.label)}</p><strong>${price}</strong><small class="${item.change_rate == null ? "" : signClass(item.change_rate)}">${change} · ${html(item.note)}</small></div><div class="spark-wrap">${sparkline(item.series, item.change_rate)}</div></article>`;
  }).join("");
}
async function loadMarkets() {
  try { renderMarkets(await api("/api/market-overview")); }
  catch (error) { $("#marketGrid").innerHTML = `<article class="market-card"><p>시장 스냅샷을 불러오지 못했습니다.</p><small>${html(error.message)}</small></article>`; }
}

function renderSummary(data) {
  const s = data.summary, currencies = data.currency_summary || {};
  const krw = currencies.KRW || {}, usd = currencies.USD || {};
  $("#totalValue").textContent = money(s.total_value_krw);
  $("#totalProfit").textContent = money(s.profit_krw);
  $("#totalProfit").className = signClass(s.profit_krw);
  $("#holdingCaption").textContent = `보유 종목 ${number(s.holding_count, 0)}개 · ${number(s.account_count, 0)}개 계좌`;
  $("#profitCaption").innerHTML = `수익률 ${s.return_rate >= 0 ? "+" : ""}${number(s.return_rate)}%<br>총 매입 ${money(s.total_cost_krw)}`;
  $("#krwValue").textContent = money(krw.market_value_krw);
  $("#krwCaption").textContent = `${number(krw.market_value || 0, 0)}원 보유`;
  $("#usdValue").textContent = money(usd.market_value, "USD");
  const rate = data.fx_rates?.USD;
  $("#usdCaption").innerHTML = rate ? `원화 환산 ${money(usd.market_value_krw)}<br>$1 = ${number(rate)}원` : "환율 갱신이 필요합니다";
  $("#updatedAt").textContent = data.updated_at ? `마지막 자산 반영 ${new Date(data.updated_at).toLocaleString("ko-KR")}` : "아직 보유종목이 없습니다.";
  const day = data.day_change || {};
  const dayText = day.change_krw == null ? "전일 기준을 수집하는 중" : `${day.change_krw >= 0 ? "+" : ""}${money(day.change_krw)} (${day.change_rate >= 0 ? "+" : ""}${number(day.change_rate)}%)`;
  $("#dayProfit").textContent = day.change_krw == null ? "—" : `${day.change_krw >= 0 ? "+" : ""}${money(day.change_krw)}`;
  $("#dayProfit").className = day.change_krw == null ? "" : signClass(day.change_krw);
  $("#dayCaption").textContent = day.change_krw == null ? "전일 기준 데이터 수집 중" : `${day.date} 대비 ${day.change_rate >= 0 ? "+" : ""}${number(day.change_rate)}%`;
  $("#accountCaption").textContent = `전체 ${number(s.account_count, 0)}개 계좌 통합`;
  $("#accountCount").textContent = `${number(s.account_count, 0)}개 계좌`;
}

function renderClassifications(items) {
  const list = $("#classificationList");
  list.innerHTML = items.length ? items.map((item) => `<div class="classification-row"><div class="classification-title"><strong>${html(item.name)}</strong><span>${number(item.holding_count, 0)}종목 · ${number(item.weight)}%</span></div><div class="classification-value"><span>${money(item.market_value_krw)}</span><b class="${signClass(item.profit_krw)}">${item.return_rate >= 0 ? "+" : ""}${number(item.return_rate)}%</b></div><div class="bar"><i style="width:${Math.min(item.weight, 100)}%"></i></div></div>`).join("") : '<div class="empty">자산을 불러오면 분류별 수익률을 표시합니다.</div>';
}
function renderAccounts(items) {
  if (!items.length) { $("#accountList").innerHTML = '<div class="empty">동기화된 계좌가 없습니다.</div>'; return; }
  const groups = new Map();
  items.forEach((item) => { const group = groups.get(item.broker) || { broker: item.broker, accounts: [], market_value_krw: 0, profit_krw: 0, holding_count: 0 }; group.accounts.push(item); group.market_value_krw += Number(item.market_value_krw || 0); group.profit_krw += Number(item.profit_krw || 0); group.holding_count += Number(item.holding_count || 0); groups.set(item.broker, group); });
  $("#accountList").innerHTML = [...groups.values()].map((group) => `<div class="account-group"><div class="account-group-title"><span>${html(group.broker)} <small>${number(group.holding_count, 0)}종목</small></span><span>${money(group.market_value_krw)}</span></div>${group.accounts.map((item) => `<div class="account-subrow"><span>${html(item.name)} · ${number(item.holding_count, 0)}종목</span><strong>${money(item.market_value_krw)}</strong><button class="icon-button account-edit-button" data-account-id="${item.id}" title="계좌 이름 수정" type="button">✎</button><button class="icon-button account-delete-button" data-account-id="${item.id}" title="계좌 삭제" type="button">×</button></div>`).join("")}</div>`).join("");
}
function renderHoldings(data) {
  const query = $("#searchInput").value.trim().toLowerCase();
  const rows = data.holdings.filter((item) => [item.name, item.code, item.broker, item.account_name].join(" ").toLowerCase().includes(query));
  const groups = new Map();
  rows.forEach((item) => {
    const key = `${item.code}|${item.currency}|${item.name}`;
    const group = groups.get(key) || { ...item, quantity: 0, market_value_krw: 0, cost_value_krw: 0, profit_krw: 0, items: [] };
    group.quantity += Number(item.quantity || 0); group.market_value_krw += Number(item.market_value_krw || 0);
    group.cost_value_krw += Number(item.cost_value_krw || 0); group.profit_krw += Number(item.profit_krw || 0); group.items.push(item); groups.set(key, group);
  });
  $("#holdingsBody").innerHTML = [...groups.values()].map((item) => {
    const rate = item.cost_value_krw ? item.profit_krw / item.cost_value_krw * 100 : 0;
    const accounts = item.items.map((detail) => `<span class="holding-account-detail">${html(detail.broker)} ${html(detail.account_name)} ${number(detail.quantity, 4)}주 <button class="mini-edit-button edit-button" data-id="${detail.id}" title="수정" type="button">✎</button><button class="mini-edit-button delete-button" data-id="${detail.id}" title="삭제" type="button">×</button></span>`).join("");
    return `<tr><td><strong>${html(item.name)}</strong><small>${html(item.code)} · ${html(item.market || item.currency)}</small></td><td>${html(item.currency === "KRW" ? "국내 자산" : "해외 자산")}</td><td class="holding-accounts">${accounts}</td><td>${number(item.quantity, 4)}</td><td>${money(item.market_value_krw)}</td><td class="${signClass(item.profit_krw)}">${item.profit_krw >= 0 ? "+" : ""}${money(item.profit_krw)}</td><td class="${signClass(rate)}">${rate >= 0 ? "+" : ""}${number(rate)}%</td><td></td></tr>`;
  }).join("");
  $("#emptyHoldings").hidden = data.holdings.length > 0; $(".table-wrap").hidden = data.holdings.length === 0;
}
function render(data) { dashboard = data; renderSummary(data); renderClassifications(data.classifications || []); renderAccounts(data.accounts); renderHoldings(data); }
async function loadDashboard() { render(await api("/api/dashboard")); }
async function loadAssetRecords() { renderAssetRecords((await api("/api/asset-records")).records || []); }

function openImport() { $("#importDialog").showModal(); }
function openHoldingDialog(record = null) {
  const form = $("#holdingForm"); form.reset(); form.dataset.recordId = record ? String(record.id) : "";
  form.broker.value = record?.broker || "기타 증권사"; form.account_name.value = record?.account_name || "내 주식 계좌";
  form.code.value = record?.code || ""; form.name.value = record?.name || ""; form.quantity.value = record?.quantity ?? "";
  form.avg_price.value = record?.avg_price ?? ""; form.current_price.value = record?.current_price ?? "";
  form.currency.value = record?.currency || "KRW"; form.market.value = record?.market || "";
  $("#holdingDialog").showModal();
}
function openAssetRecordDialog(record = null) {
  const form = $("#assetRecordForm");
  form.reset();
  form.dataset.recordId = record?.id || "";
  $("#assetRecordDialogTitle").textContent = record ? "자산기록 수정" : "자산기록 추가";
  form.date.value = record?.date || new Date().toISOString().slice(0, 10);
  form.total_value_krw.value = record?.total_value_krw ?? "";
  form.total_cost_krw.value = record?.total_cost_krw ?? "";
  form.profit_krw.value = record?.profit_krw ?? "";
  form.return_rate.value = record?.return_rate ?? "";
  form.day_profit_krw.value = record?.day_profit_krw ?? "";
  form.krw_value_krw.value = record?.krw_value_krw ?? "";
  form.usd_value_krw.value = record?.usd_value_krw ?? "";
  form.holding_count.value = record?.holding_count ?? "";
  form.memo.value = record?.memo ?? "";
  $("#assetRecordDialog").showModal();
}
$("#syncKbButton").addEventListener("click", (e) => action(e.currentTarget, () => api("/api/sync/kb", { method: "POST" })));
$("#syncTossButton").addEventListener("click", (e) => action(e.currentTarget, () => api("/api/sync/toss", { method: "POST" })));
$("#syncNamooButton").addEventListener("click", (e) => action(e.currentTarget, () => api("/api/sync/namoo", { method: "POST" })));
$("#refreshButton").addEventListener("click", (e) => action(e.currentTarget, () => api("/api/refresh-prices", { method: "POST" })));
$("#refreshFxButton").addEventListener("click", (e) => action(e.currentTarget, () => api("/api/fx/refresh", { method: "POST" }), async () => { await loadDashboard(); await loadMarkets(); }));
$("#refreshMarketButton").addEventListener("click", (e) => action(e.currentTarget, () => api("/api/market-overview"), async () => { await loadMarkets(); }));
$("#demoButton").addEventListener("click", (e) => action(e.currentTarget, () => api("/api/demo", { method: "POST" })));
$("#addButton").addEventListener("click", () => openHoldingDialog()); $("#importButton").addEventListener("click", openImport);
$("#addRecordButton").addEventListener("click", () => openAssetRecordDialog());
$("#snapshotButton").addEventListener("click", (e) => action(e.currentTarget, async () => {
  // 화면의 최신 보유자산을 먼저 반영한 뒤 스냅샷을 저장합니다.
  await loadDashboard();
  try {
    return await api("/api/asset-records/snapshot", { method: "POST" });
  } catch (error) {
    // 이전 서버가 실행 중인 경우에도 기본 저장 API로 기록할 수 있게 합니다.
    if (!/Not Found|찾지 못|404/i.test(error.message || "")) throw error;
    const s = dashboard.summary || {};
    const day = dashboard.day_change || {};
    const currency = dashboard.currency_summary || {};
    return api("/api/asset-records", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({
      date: new Date().toISOString().slice(0, 10), total_value_krw: s.total_value_krw, total_cost_krw: s.total_cost_krw,
      profit_krw: s.profit_krw, return_rate: s.return_rate, day_profit_krw: day.change_krw || 0,
      krw_value_krw: currency.KRW?.market_value_krw || 0, usd_value_krw: currency.USD?.market_value_krw || 0,
      holding_count: s.holding_count, source: "snapshot", memo: "수동 스냅샷"
    }) });
  }
}, async () => { await loadDashboard(); await loadAssetRecords(); }));
$("#searchInput").addEventListener("input", () => dashboard && renderHoldings(dashboard));
$("#clearButton").addEventListener("click", () => { if (confirm("저장된 보유내역을 모두 지울까요?")) action($("#clearButton"), () => api("/api/clear", { method: "POST" })); });
$("#holdingsBody").addEventListener("click", (e) => { const edit = e.target.closest(".edit-button"); const button = e.target.closest(".delete-button"); if (edit) { const item = dashboard?.holdings.find((row) => row.id === edit.dataset.id); if (item) openHoldingDialog(item); return; } if (button && confirm("이 보유종목을 삭제할까요?")) action(button, () => api(`/api/holdings/${button.dataset.id}`, { method: "DELETE" })); });
$("#accountList").addEventListener("click", (e) => { const button = e.target.closest(".account-delete-button"); if (button && confirm("이 계좌와 연결된 보유종목을 모두 삭제할까요?")) action(button, () => api(`/api/accounts/${button.dataset.accountId}`, { method: "DELETE" })); });
$("#accountList").addEventListener("click", async (e) => { const button = e.target.closest(".account-edit-button"); if (!button) return; const account = dashboard?.accounts.find((item) => item.id === button.dataset.accountId); if (!account) return; const name = prompt("계좌 이름을 입력하세요.", account.name); if (name && name.trim() && name.trim() !== account.name) await action(button, () => api(`/api/accounts/${account.id}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: name.trim() }) })); });
$("#assetRecordList").addEventListener("click", async (e) => {
  const editButton = e.target.closest("[data-record-edit]");
  const deleteButton = e.target.closest("[data-record-delete]");
  if (editButton) {
    const record = assetRecords.find((item) => item.id === editButton.dataset.recordEdit);
    if (record) openAssetRecordDialog(record);
  }
  if (deleteButton && confirm("이 자산기록을 삭제할까요?")) {
    await action(deleteButton, () => api(`/api/asset-records/${deleteButton.dataset.recordDelete}`, { method: "DELETE" }), loadAssetRecords);
  }
});
$("#holdingForm").addEventListener("submit", async (e) => { e.preventDefault(); const form = e.currentTarget, payload = Object.fromEntries(new FormData(form)); ["quantity", "avg_price", "current_price"].forEach((key) => { payload[key] = Number(payload[key]); }); try { const id = form.dataset.recordId; const result = await api(id ? `/api/holdings/${id}` : "/api/holdings", { method: id ? "PUT" : "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }); form.closest("dialog").close(); toast(result.message); await loadDashboard(); } catch (error) { toast(error.message, true); } });
$("#importForm").addEventListener("submit", async (e) => { e.preventDefault(); const file = $("#importFile").files[0]; if (!file) return; const formData = new FormData(); formData.append("file", file); try { const result = await api(`/api/import?broker=${encodeURIComponent($("#importBroker").value || "기타 증권사")}`, { method: "POST", body: formData }); e.currentTarget.closest("dialog").close(); toast(result.message); await loadDashboard(); } catch (error) { toast(error.message, true); } });
$("#assetRecordForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.currentTarget;
  const payload = Object.fromEntries(new FormData(form));
  ["total_value_krw", "total_cost_krw", "profit_krw", "return_rate", "day_profit_krw", "krw_value_krw", "usd_value_krw", "holding_count"].forEach((key) => {
    payload[key] = Number(payload[key] || 0);
  });
  payload.memo = payload.memo || "";
  try {
    const method = form.dataset.recordId ? "PUT" : "POST";
    const url = form.dataset.recordId ? `/api/asset-records/${form.dataset.recordId}` : "/api/asset-records";
    const result = await api(url, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    form.closest("dialog").close();
    toast(result.message);
    await loadAssetRecords();
  } catch (error) {
    toast(error.message, true);
  }
});
async function bootstrap() { await loadDashboard().catch((error) => toast(error.message, true)); await loadMarkets(); await loadAssetRecords(); }
bootstrap();
