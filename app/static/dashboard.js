let chartWeekly, chartFunnel, chartByType;

async function cargarKPIs() {
  const k = await (await fetch("/stats/kpis")).json();
  document.getElementById("kpis").innerHTML = `
    <div class="kpi"><span>${k.candidaturas_totales}</span>Total</div>
    <div class="kpi"><span>${k.esta_semana}</span>Esta semana</div>
    <div class="kpi"><span>${k.respuestas}</span>Respuestas</div>
    <div class="kpi"><span>${k.entrevistas}</span>Entrevistas</div>
    <div class="kpi"><span>${k.pruebas_tecnicas}</span>Pruebas</div>
    <div class="kpi"><span>${k.ofertas}</span>Ofertas</div>
    <div class="kpi rate"><span>${k.tasa_respuesta}%</span>Tasa respuesta</div>
    <div class="kpi rate"><span>${k.tasa_entrevista}%</span>Tasa entrevista</div>
  `;
}

async function cargarWeekly() {
  const data = await (await fetch("/stats/weekly")).json();
  if (chartWeekly) chartWeekly.destroy();
  chartWeekly = new Chart(document.getElementById("chartWeekly"), {
    type: "bar",
    data: {
      labels: data.map((d) => d.semana),
      datasets: [{ label: "Candidaturas por semana", data: data.map((d) => d.candidaturas), backgroundColor: "#38bdf8" }],
    },
    options: { plugins: { legend: { labels: { color: "#e2e8f0" } } } },
  });
}

async function cargarFunnel() {
  const data = await (await fetch("/stats/funnel")).json();
  if (chartFunnel) chartFunnel.destroy();
  chartFunnel = new Chart(document.getElementById("chartFunnel"), {
    type: "bar",
    data: {
      labels: data.map((d) => d.etapa),
      datasets: [{ label: "Embudo", data: data.map((d) => d.cantidad), backgroundColor: "#4ade80" }],
    },
    options: { indexAxis: "y", plugins: { legend: { labels: { color: "#e2e8f0" } } } },
  });
}

async function cargarByType() {
  const data = await (await fetch("/stats/by-type")).json();
  if (chartByType) chartByType.destroy();
  chartByType = new Chart(document.getElementById("chartByType"), {
    type: "bar",
    data: {
      labels: data.map((d) => `${d.job_type} / ${d.cv_version}`),
      datasets: [{ label: "Tasa de respuesta (%)", data: data.map((d) => d.tasa_respuesta), backgroundColor: "#facc15" }],
    },
    options: { plugins: { legend: { labels: { color: "#e2e8f0" } } } },
  });
}

async function cargarTabla(filtros = {}) {
  const params = new URLSearchParams(Object.fromEntries(Object.entries(filtros).filter(([, v]) => v)));
  const data = await (await fetch(`/applications?${params}`)).json();
  document.querySelector("#table tbody").innerHTML = data
    .map(
      (a) => `<tr>
        <td>${a.company}</td>
        <td>${a.position}</td>
        <td>${a.status}</td>
        <td>${a.cv_version ?? "-"}</td>
        <td>${new Date(a.last_update).toLocaleDateString()}</td>
      </tr>`
    )
    .join("");
}

function refrescarTodo() {
  cargarKPIs();
  cargarWeekly();
  cargarFunnel();
  cargarByType();
  cargarTabla();
}

document.getElementById("formApp").addEventListener("submit", async (e) => {
  e.preventDefault();
  const body = Object.fromEntries(new FormData(e.target).entries());
  Object.keys(body).forEach((k) => body[k] === "" && delete body[k]);
  const res = await fetch("/applications", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const msg = document.getElementById("formMsg");
  if (res.ok) {
    msg.textContent = "✅ Guardada";
    e.target.reset();
    refrescarTodo();
  } else {
    msg.textContent = "❌ " + JSON.stringify((await res.json()).detail);
  }
});

document.getElementById("fBtn").addEventListener("click", () => {
  cargarTabla({
    company: document.getElementById("fCompany").value,
    status: document.getElementById("fStatus").value,
  });
});

refrescarTodo();
