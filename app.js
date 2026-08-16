const stocks = [
  { name: "삼성전자", code: "005930", price: 72400, change: 800, watched: true },
  { name: "SK하이닉스", code: "000660", price: 198700, change: -2100, watched: true },
  { name: "NAVER", code: "035420", price: 183500, change: 1200, watched: true },
  { name: "현대차", code: "005380", price: 247000, change: 3500, watched: true },
  { name: "LG에너지솔루션", code: "373220", price: 355500, change: -1500, watched: false }
];

const won = new Intl.NumberFormat("ko-KR");
const table = document.querySelector("#stockTable");
const search = document.querySelector("#searchInput");

function render() {
  const term = search.value.trim().toLowerCase();
  const visible = stocks.filter(s => s.name.toLowerCase().includes(term) || s.code.includes(term));
  table.innerHTML = visible.map(s => {
    const rate = (s.change / (s.price - s.change) * 100).toFixed(2);
    const positive = s.change >= 0;
    return `<tr><td><strong>${s.name}</strong><small>${s.code}</small></td><td>${won.format(s.price)}원</td><td class="${positive ? "up" : "down"}">${positive ? "+" : ""}${won.format(s.change)}원</td><td class="${positive ? "up" : "down"}">${positive ? "+" : ""}${rate}%</td><td><button class="star ${s.watched ? "active" : ""}" data-code="${s.code}" aria-label="관심 종목 전환">★</button></td></tr>`;
  }).join("") || `<tr><td colspan="5">검색 결과가 없습니다.</td></tr>`;
  document.querySelector("#stockCount").textContent = stocks.filter(s => s.watched).length;
}

search.addEventListener("input", render);
table.addEventListener("click", e => {
  const code = e.target.dataset.code;
  if (!code) return;
  stocks.find(s => s.code === code).watched = !stocks.find(s => s.code === code).watched;
  render();
});
document.querySelector("#refreshButton").addEventListener("click", () => {
  stocks.forEach(s => { const delta = Math.round((Math.random() - .5) * 800 / 100) * 100; s.price += delta; s.change += delta; });
  document.querySelector("#updatedAt").textContent = `예시 데이터 · ${new Date().toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" })} 업데이트됨`;
  render();
});
render();
