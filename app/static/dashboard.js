let chartWeekly, chartFunnel, chartByType;

const ESTADOS_EDITABLES = [
  "Guardada",
  "Candidatura enviada",
  "CV visto",
  "Entrevista",
  "Prueba técnica",
  "Oferta",
  "Rechazada",
];

function escaparHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

let feedbackTimer;
function mostrarMensajeTabla(texto, esError = false) {
  const msg = document.getElementById("tableMsg");
  if (!msg) return;
  msg.textContent = texto;
  msg.className = "table-msg" + (esError ? " error" : "");
  clearTimeout(feedbackTimer);
  feedbackTimer = setTimeout(() => {
    msg.textContent = "";
  }, 4000);
}

function generarOpcionesEstado(estadoActual) {
  let html = "";
  if (estadoActual === "Sin respuesta") {
    html += `<option value="Sin respuesta" selected disabled>Sin respuesta</option>`;
  }
  html += ESTADOS_EDITABLES.map(
    (st) => `<option value="${st}" ${st === estadoActual ? "selected" : ""}>${st}</option>`
  ).join("");
  return html;
}

function obtenerFiltrosActuales() {
  return {
    company: document.getElementById("fCompany").value,
    status: document.getElementById("fStatus").value,
  };
}

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
  const tbody = document.querySelector("#table tbody");
  if (!data || !data.length) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--muted); padding: 1.5rem;">No hay candidaturas registradas</td></tr>`;
    return;
  }
  tbody.innerHTML = data
    .map(
      (a) => `<tr>
        <td>
          <strong>${escaparHtml(a.company)}</strong>
          ${a.location ? `<div class="sub-cell">${escaparHtml(a.location)}</div>` : ""}
        </td>
        <td>
          ${a.url ? `<a href="${escaparHtml(a.url)}" target="_blank" rel="noopener noreferrer" class="link-job">${escaparHtml(a.position)} ↗</a>` : `<span>${escaparHtml(a.position)}</span>`}
          <div class="sub-cell">${escaparHtml(a.job_type || "")}${a.modality ? ` • ${escaparHtml(a.modality)}` : ""}</div>
        </td>
        <td>
          <select class="status-select" data-id="${a.id}" onchange="cambiarEstado(${a.id}, this.value, this)">
            ${generarOpcionesEstado(a.status)}
          </select>
        </td>
        <td>${escaparHtml(a.cv_version ?? "-")}</td>
        <td>${new Date(a.last_update).toLocaleDateString()}</td>
        <td class="td-actions">
          <button class="btn-delete" title="Eliminar candidatura" onclick="eliminarCandidatura(${a.id}, '${escaparHtml(a.company).replace(/'/g, "\\'")}')">
            🗑️
          </button>
        </td>
      </tr>`
    )
    .join("");
}

async function cambiarEstado(id, nuevoEstado, selectElem) {
  try {
    const res = await fetch(`/applications/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: nuevoEstado }),
    });
    if (res.ok) {
      mostrarMensajeTabla(`✅ Estado actualizado a "${nuevoEstado}"`);
      cargarKPIs();
      cargarWeekly();
      cargarFunnel();
      cargarByType();
    } else {
      const err = await res.json();
      mostrarMensajeTabla("❌ Error al cambiar estado: " + JSON.stringify(err.detail), true);
      cargarTabla(obtenerFiltrosActuales());
    }
  } catch (e) {
    mostrarMensajeTabla("❌ Error de conexión al actualizar", true);
    cargarTabla(obtenerFiltrosActuales());
  }
}
window.cambiarEstado = cambiarEstado;

async function eliminarCandidatura(id, empresa) {
  const confirmacion = confirm(`¿Estás seguro de que deseas eliminar la candidatura de "${empresa}"?`);
  if (!confirmacion) return;
  try {
    const res = await fetch(`/applications/${id}`, { method: "DELETE" });
    if (res.ok) {
      mostrarMensajeTabla(`🗑️ Candidatura de "${empresa}" eliminada.`);
      refrescarTodo();
    } else {
      mostrarMensajeTabla("❌ Error al eliminar la candidatura", true);
    }
  } catch (e) {
    mostrarMensajeTabla("❌ Error de conexión al eliminar", true);
  }
}
window.eliminarCandidatura = eliminarCandidatura;

function refrescarTodo() {
  cargarKPIs();
  cargarWeekly();
  cargarFunnel();
  cargarByType();
  cargarTabla(obtenerFiltrosActuales());
}

document.getElementById("formApp").addEventListener("submit", async (e) => {
  e.preventDefault();
  const body = Object.fromEntries(new FormData(e.target).entries());
  Object.keys(body).forEach((k) => body[k] === "" && delete body[k]);
  body.found_date = body.fecha;
  body.applied_date = body.fecha;
  delete body.fecha;
  const res = await fetch("/applications", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const msg = document.getElementById("formMsg");
  if (res.ok) {
    msg.textContent = "✅ Guardada";
    e.target.reset();
    document.getElementById("fecha").valueAsDate = new Date();
    const formStatus = document.getElementById("formStatus");
    if (formStatus) formStatus.value = "Candidatura enviada";
    refrescarTodo();
  } else {
    msg.textContent = "❌ " + JSON.stringify((await res.json()).detail);
  }
});

document.getElementById("fBtn").addEventListener("click", () => {
  cargarTabla(obtenerFiltrosActuales());
});

document.getElementById("btnExport").addEventListener("click", async () => {
  try {
    mostrarMensajeTabla("⏳ Generando archivo de texto plano...");
    const filtros = obtenerFiltrosActuales();
    const params = new URLSearchParams(Object.fromEntries(Object.entries(filtros).filter(([, v]) => v)));
    const res = await fetch(`/applications/export/txt?${params}`);
    if (!res.ok) throw new Error("Error al descargar");
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    const hoy = new Date().toISOString().slice(0, 10);
    a.href = url;
    a.download = `candidaturas_${hoy}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
    mostrarMensajeTabla("📄 Exportación completada con éxito");
  } catch (e) {
    mostrarMensajeTabla("❌ Error al exportar archivo", true);
  }
});

document.getElementById("fecha").valueAsDate = new Date();
const formStatus = document.getElementById("formStatus");
if (formStatus) formStatus.value = "Candidatura enviada";

refrescarTodo();
