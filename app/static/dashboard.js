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

function obtenerClaseEstado(estado) {
  const mapa = {
    "Guardada": "status-badge-guardada",
    "Candidatura enviada": "status-badge-candidatura-enviada",
    "CV visto": "status-badge-cv-visto",
    "Entrevista": "status-badge-entrevista",
    "Prueba técnica": "status-badge-prueba-tecnica",
    "Oferta": "status-badge-oferta",
    "Rechazada": "status-badge-rechazada",
    "Sin respuesta": "status-badge-sin-respuesta",
  };
  return mapa[estado] || "status-badge-guardada";
}

function actualizarEstiloSelect(selectElem, estado) {
  if (!selectElem) return;
  selectElem.classList.remove(
    "status-badge-guardada",
    "status-badge-candidatura-enviada",
    "status-badge-cv-visto",
    "status-badge-entrevista",
    "status-badge-prueba-tecnica",
    "status-badge-oferta",
    "status-badge-rechazada",
    "status-badge-sin-respuesta"
  );
  selectElem.classList.add(obtenerClaseEstado(estado));
}

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
  }, 4500);
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
  const comp = document.getElementById("fCompany");
  const st = document.getElementById("fStatus");
  return {
    company: comp ? comp.value.trim() : "",
    status: st ? st.value : "",
  };
}

function actualizarBotonLimpiar() {
  const clearBtn = document.getElementById("fClearBtn");
  if (!clearBtn) return;
  const f = obtenerFiltrosActuales();
  if (f.company || f.status) {
    clearBtn.classList.remove("hidden");
  } else {
    clearBtn.classList.add("hidden");
  }
}

async function cargarKPIs() {
  try {
    const k = await (await fetch("/stats/kpis")).json();
    const kpisEl = document.getElementById("kpis");
    if (!kpisEl) return;
    kpisEl.innerHTML = `
      <div class="kpi">
        <div class="kpi-label"><span>Total</span><span class="kpi-icon">📋</span></div>
        <div class="kpi-val">${k.candidaturas_totales}</div>
      </div>
      <div class="kpi">
        <div class="kpi-label"><span>Esta semana</span><span class="kpi-icon">⚡</span></div>
        <div class="kpi-val">${k.esta_semana}</div>
      </div>
      <div class="kpi">
        <div class="kpi-label"><span>Respuestas</span><span class="kpi-icon">💬</span></div>
        <div class="kpi-val">${k.respuestas}</div>
      </div>
      <div class="kpi warning">
        <div class="kpi-label"><span>Entrevistas</span><span class="kpi-icon">🎯</span></div>
        <div class="kpi-val">${k.entrevistas}</div>
      </div>
      <div class="kpi">
        <div class="kpi-label"><span>Pruebas</span><span class="kpi-icon">💻</span></div>
        <div class="kpi-val">${k.pruebas_tecnicas}</div>
      </div>
      <div class="kpi rate">
        <div class="kpi-label"><span>Ofertas</span><span class="kpi-icon">🏆</span></div>
        <div class="kpi-val">${k.ofertas}</div>
      </div>
      <div class="kpi rate">
        <div class="kpi-label"><span>Tasa respuesta</span><span class="kpi-icon">📈</span></div>
        <div class="kpi-val">${k.tasa_respuesta}%</div>
      </div>
      <div class="kpi rate">
        <div class="kpi-label"><span>Tasa entrevista</span><span class="kpi-icon">🚀</span></div>
        <div class="kpi-val">${k.tasa_entrevista}%</div>
      </div>
    `;
  } catch (e) {
    console.error("Error al cargar KPIs:", e);
  }
}

const baseChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      labels: {
        color: "#94a3b8",
        font: { family: "'Plus Jakarta Sans', sans-serif", size: 12, weight: 600 },
      },
    },
    tooltip: {
      backgroundColor: "rgba(11, 16, 28, 0.95)",
      borderColor: "rgba(56, 189, 248, 0.35)",
      borderWidth: 1,
      titleColor: "#ffffff",
      bodyColor: "#94a3b8",
      padding: 10,
      cornerRadius: 8,
      titleFont: { family: "'Plus Jakarta Sans', sans-serif", weight: 700 },
      bodyFont: { family: "'Plus Jakarta Sans', sans-serif" },
    },
  },
  scales: {
    x: {
      ticks: { color: "#64748b", font: { family: "'Plus Jakarta Sans', sans-serif", size: 11 } },
      grid: { color: "rgba(255, 255, 255, 0.05)" },
    },
    y: {
      ticks: { color: "#64748b", font: { family: "'Plus Jakarta Sans', sans-serif", size: 11 }, precision: 0 },
      grid: { color: "rgba(255, 255, 255, 0.05)" },
    },
  },
};

async function cargarWeekly() {
  try {
    const data = await (await fetch("/stats/weekly")).json();
    const ctx = document.getElementById("chartWeekly");
    if (!ctx) return;
    if (chartWeekly) chartWeekly.destroy();
    chartWeekly = new Chart(ctx, {
      type: "bar",
      data: {
        labels: data.map((d) => d.semana),
        datasets: [
          {
            label: "Candidaturas",
            data: data.map((d) => d.candidaturas),
            backgroundColor: "#38bdf8",
            borderRadius: 6,
            hoverBackgroundColor: "#7dd3fc",
          },
        ],
      },
      options: baseChartOptions,
    });
  } catch (e) {
    console.error("Error al cargar gráfico semanal:", e);
  }
}

async function cargarFunnel() {
  try {
    const data = await (await fetch("/stats/funnel")).json();
    const ctx = document.getElementById("chartFunnel");
    if (!ctx) return;
    if (chartFunnel) chartFunnel.destroy();
    chartFunnel = new Chart(ctx, {
      type: "bar",
      data: {
        labels: data.map((d) => d.etapa),
        datasets: [
          {
            label: "Candidaturas",
            data: data.map((d) => d.cantidad),
            backgroundColor: [
              "#64748b",
              "#38bdf8",
              "#818cf8",
              "#fbbf24",
              "#c084fc",
              "#34d399",
            ],
            borderRadius: 6,
          },
        ],
      },
      options: {
        ...baseChartOptions,
        indexAxis: "y",
      },
    });
  } catch (e) {
    console.error("Error al cargar funnel:", e);
  }
}

async function cargarByType() {
  try {
    const data = await (await fetch("/stats/by-type")).json();
    const ctx = document.getElementById("chartByType");
    if (!ctx) return;
    if (chartByType) chartByType.destroy();
    chartByType = new Chart(ctx, {
      type: "bar",
      data: {
        labels: data.map((d) => `${d.job_type} / ${d.cv_version}`),
        datasets: [
          {
            label: "Tasa de respuesta (%)",
            data: data.map((d) => d.tasa_respuesta),
            backgroundColor: "#fbbf24",
            borderRadius: 6,
            hoverBackgroundColor: "#fde047",
          },
        ],
      },
      options: {
        ...baseChartOptions,
        scales: {
          ...baseChartOptions.scales,
          y: {
            ...baseChartOptions.scales.y,
            max: 100,
            ticks: { callback: (val) => val + "%", color: "#64748b" },
          },
        },
      },
    });
  } catch (e) {
    console.error("Error al cargar by-type:", e);
  }
}

async function cargarTabla(filtros = {}) {
  try {
    const params = new URLSearchParams(Object.fromEntries(Object.entries(filtros).filter(([, v]) => v)));
    const data = await (await fetch(`/applications?${params}`)).json();
    const tbody = document.querySelector("#table tbody");
    const countBadge = document.getElementById("tableCount");
    if (countBadge) countBadge.textContent = data ? data.length : 0;

    if (!data || !data.length) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 2.5rem;">
        🔍 No se encontraron candidaturas con los filtros aplicados.
      </td></tr>`;
      return;
    }

    tbody.innerHTML = data
      .map((a) => {
        const initial = (a.company || "?").trim().charAt(0).toUpperCase();
        const modalityClass = a.modality ? `modality-${a.modality.toLowerCase().replace(/í/g, "i")}` : "";
        const cvClass = a.cv_version === "CV General" ? "cv-pill cv-general-pill" : "cv-pill";
        const statusBadgeClass = obtenerClaseEstado(a.status);

        return `<tr>
          <td>
            <div class="company-cell">
              <span class="company-avatar">${escaparHtml(initial)}</span>
              <div class="company-meta">
                <strong>${escaparHtml(a.company)}</strong>
                ${a.location ? `<div class="sub-meta">📍 ${escaparHtml(a.location)}</div>` : ""}
              </div>
            </div>
          </td>
          <td>
            ${
              a.url
                ? `<a href="${escaparHtml(a.url)}" target="_blank" rel="noopener noreferrer" class="link-job">${escaparHtml(a.position)} ↗</a>`
                : `<strong>${escaparHtml(a.position)}</strong>`
            }
            <div class="sub-meta" style="margin-top: 4px; display: flex; gap: 4px; align-items: center; flex-wrap: wrap;">
              <span>${escaparHtml(a.job_type || "")}</span>
              ${a.modality ? `• <span class="badge-pill ${modalityClass}">${escaparHtml(a.modality)}</span>` : ""}
              ${a.source ? `<span style="opacity: 0.75;">(${escaparHtml(a.source)})</span>` : ""}
            </div>
          </td>
          <td>
            <select class="status-select ${statusBadgeClass}" data-id="${a.id}" onchange="cambiarEstado(${a.id}, this.value, this)">
              ${generarOpcionesEstado(a.status)}
            </select>
          </td>
          <td>
            <span class="${cvClass}">${escaparHtml(a.cv_version || "Sin especificar")}</span>
          </td>
          <td>
            <span style="font-size: 0.85rem; color: #cbd5e1;">${new Date(a.last_update).toLocaleDateString()}</span>
          </td>
          <td class="td-actions">
            <button class="btn-delete" title="Eliminar candidatura de ${escaparHtml(a.company)}" onclick="eliminarCandidatura(${a.id}, '${escaparHtml(a.company).replace(/'/g, "\\'")}')">
              🗑️
            </button>
          </td>
        </tr>`;
      })
      .join("");
  } catch (e) {
    console.error("Error al cargar tabla:", e);
  }
}

async function cambiarEstado(id, nuevoEstado, selectElem) {
  try {
    actualizarEstiloSelect(selectElem, nuevoEstado);
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

// Envío del formulario de nueva candidatura con sanitización
document.getElementById("formApp").addEventListener("submit", async (e) => {
  e.preventDefault();
  const formData = new FormData(e.target);
  const body = {};

  // Sanitización de strings en el cliente
  for (const [key, value] of formData.entries()) {
    if (typeof value === "string") {
      const trimmed = value.trim();
      if (trimmed !== "") {
        body[key] = trimmed;
      }
    }
  }

  body.found_date = body.fecha;
  body.applied_date = body.fecha;
  delete body.fecha;

  const msg = document.getElementById("formMsg");
  try {
    const res = await fetch("/applications", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (res.ok) {
      msg.textContent = "✅ Candidatura guardada con éxito";
      msg.style.color = "var(--success)";
      e.target.reset();
      document.getElementById("fecha").valueAsDate = new Date();
      const formStatus = document.getElementById("formStatus");
      if (formStatus) formStatus.value = "Candidatura enviada";
      setTimeout(() => {
        msg.textContent = "";
      }, 3500);
      refrescarTodo();
    } else {
      const err = await res.json();
      msg.textContent = "❌ " + JSON.stringify(err.detail);
      msg.style.color = "var(--danger)";
    }
  } catch (err) {
    msg.textContent = "❌ Error de conexión al guardar";
    msg.style.color = "var(--danger)";
  }
});

// Filtrado reactivo en tiempo real con debounce
let debounceTimer;
document.getElementById("fCompany").addEventListener("input", () => {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    actualizarBotonLimpiar();
    cargarTabla(obtenerFiltrosActuales());
  }, 220);
});

document.getElementById("fStatus").addEventListener("change", () => {
  actualizarBotonLimpiar();
  cargarTabla(obtenerFiltrosActuales());
});

const clearBtn = document.getElementById("fClearBtn");
if (clearBtn) {
  clearBtn.addEventListener("click", () => {
    document.getElementById("fCompany").value = "";
    document.getElementById("fStatus").value = "";
    actualizarBotonLimpiar();
    cargarTabla({});
  });
}

// Exportación TXT
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
    mostrarMensajeTabla("📄 Exportación TXT completada con éxito");
  } catch (e) {
    mostrarMensajeTabla("❌ Error al exportar archivo TXT", true);
  }
});

// Exportación CSV
document.getElementById("btnExportCsv").addEventListener("click", async () => {
  try {
    mostrarMensajeTabla("⏳ Generando archivo CSV para Excel/Sheets...");
    const filtros = obtenerFiltrosActuales();
    const params = new URLSearchParams(Object.fromEntries(Object.entries(filtros).filter(([, v]) => v)));
    const res = await fetch(`/applications/export/csv?${params}`);
    if (!res.ok) throw new Error("Error al descargar");
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    const hoy = new Date().toISOString().slice(0, 10);
    a.href = url;
    a.download = `candidaturas_${hoy}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
    mostrarMensajeTabla("📊 Exportación CSV completada con éxito");
  } catch (e) {
    mostrarMensajeTabla("❌ Error al exportar archivo CSV", true);
  }
});

// Inicialización de la vista
document.getElementById("fecha").valueAsDate = new Date();
const formStatus = document.getElementById("formStatus");
if (formStatus) formStatus.value = "Candidatura enviada";

refrescarTodo();
