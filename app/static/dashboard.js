/* Job Tracker — captura rápida, chips, kanban, detalle y deshacer. */

const ESTADOS = ["Enviada", "Contactado", "Entrevista", "Rechazada"];

// Etiqueta para max_stage_reached histórico (0-5). Los valores 4 y 5
// vienen de la versión anterior (prueba técnica / oferta).
const ETAPAS = ["Enviada", "Enviada", "Contactado", "Entrevista", "Entrevista", "Entrevista"];

const SIGUIENTE = {
  "Enviada": "Contactado",
  "Contactado": "Entrevista",
  "Entrevista": null,
  "Rechazada": "Enviada",
};

const RANGO = {
  "Enviada": 1,
  "Contactado": 2,
  "Entrevista": 3,
};

const ALIAS_ESTADO = {
  "enviada": "Enviada",
  "enviado": "Enviada",
  "aplicada": "Enviada",
  "aplicado": "Enviada",
  "guardada": "Enviada",
  "candidatura enviada": "Enviada",
  "sin respuesta": "Enviada",
  "ghosting": "Enviada",
  "ghosted": "Enviada",
  "contactado": "Contactado",
  "contacto": "Contactado",
  "contactada": "Contactado",
  "cv visto": "Contactado",
  "cv": "Contactado",
  "entrevista": "Entrevista",
  "prueba": "Entrevista",
  "prueba tecnica": "Entrevista",
  "tecnica": "Entrevista",
  "oferta": "Entrevista",
  "rechazada": "Rechazada",
  "rechazo": "Rechazada",
  "rechazado": "Rechazada",
};

const VIEW_KEY = "jobtracker-view";
const GOALS_KEY = "jobtracker-goals";

let apps = [];
let atencion = [];
let kpis = {};
let vista = localStorage.getItem(VIEW_KEY) || "kanban";
let fechaModo = "hoy";
let estadoCaptura = "Enviada";
let estadoDetalle = "Enviada";
let drawerId = null;
let menuCtx = null;
let dragging = false;

let sugerenciasCache = { companies: [], positions: [] };
let suggestionTimer = null;
let duplicateTimer = null;
let toastTimer = null;

let chartWeekly = null;
let chartFunnel = null;
let chartByType = null;

/* ============================ Utilidades ============================ */

function normalizarTexto(valor) {
  return String(valor || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
}

function slugEstado(estado) {
  return normalizarTexto(estado).replace(/\s+/g, "-");
}

function claseEstado(estado) {
  return "chip-" + slugEstado(estado);
}

function escaparHtml(valor) {
  if (valor === null || valor === undefined) return "";
  return String(valor)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function urlSegura(valor) {
  if (!valor) return null;
  const limpia = String(valor).trim();
  return /^https?:\/\//i.test(limpia) ? limpia : null;
}

function isoLocal(fecha = new Date()) {
  const copia = new Date(fecha.getTime() - fecha.getTimezoneOffset() * 60000);
  return copia.toISOString().slice(0, 10);
}

function ayerISO() {
  const fecha = new Date();
  fecha.setDate(fecha.getDate() - 1);
  return isoLocal(fecha);
}

function fechaCaptura() {
  return fechaModo === "ayer" ? ayerISO() : isoLocal();
}

function fechaCorta(iso) {
  if (!iso) return "—";
  const fecha = new Date(iso + "T00:00:00");
  if (Number.isNaN(fecha.getTime())) return iso;
  return new Intl.DateTimeFormat("es-ES", { day: "numeric", month: "short" }).format(fecha);
}

function fechaHora(iso) {
  if (!iso) return "—";
  const fecha = new Date(iso);
  if (Number.isNaN(fecha.getTime())) return iso;
  return new Intl.DateTimeFormat("es-ES", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(fecha);
}

function inicial(empresa) {
  return (empresa || "?").trim().charAt(0).toUpperCase();
}

async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  const res = await fetch(path, { ...options, headers });
  const texto = await res.text();
  let datos = null;
  if (texto) {
    try {
      datos = JSON.parse(texto);
    } catch {
      datos = texto;
    }
  }
  if (!res.ok) {
    let detalle = datos && datos.detail ? datos.detail : `Error ${res.status}`;
    if (Array.isArray(detalle)) {
      detalle = detalle.map((e) => e.msg || JSON.stringify(e)).join("; ");
    } else if (typeof detalle === "object") {
      detalle = JSON.stringify(detalle);
    }
    throw new Error(detalle);
  }
  return datos;
}

/* ============================ Toast / deshacer ============================ */

function ocultarToast() {
  const toast = document.getElementById("toast");
  if (toast) toast.classList.add("hidden");
}

function mostrarToast(mensaje, opciones = {}) {
  const { accion = null, onAccion = null, tipo = "", duracion = 8000 } = opciones;
  const toast = document.getElementById("toast");
  const texto = document.getElementById("toastMsg");
  const boton = document.getElementById("toastAction");
  if (!toast || !texto || !boton) return;

  clearTimeout(toastTimer);
  texto.textContent = mensaje;
  toast.className = "toast" + (tipo ? " " + tipo : "");

  if (accion && onAccion) {
    boton.textContent = accion;
    boton.classList.remove("hidden");
    boton.onclick = async () => {
      ocultarToast();
      try {
        await onAccion();
      } catch (error) {
        mostrarToast("No se pudo deshacer: " + error.message, { tipo: "error", duracion: 6000 });
      }
    };
  } else {
    boton.classList.add("hidden");
    boton.onclick = null;
  }

  toast.classList.remove("hidden");
  toastTimer = setTimeout(ocultarToast, duracion);
}

/* ============================ Carga de datos ============================ */

async function cargarAplicaciones() {
  try {
    apps = await api("/applications?limit=1000");
    renderLista();
  } catch (error) {
    mostrarMensajeTabla("No se pudieron cargar las candidaturas: " + error.message, true);
  }
}

async function cargarAtencion() {
  try {
    atencion = await api("/applications/attention");
    renderAtencion();
  } catch (error) {
    console.error("Error al cargar atención:", error);
  }
}

async function cargarKPIs() {
  try {
    kpis = await api("/stats/kpis");
    renderKPIs();
    renderRitmo();
  } catch (error) {
    console.error("Error al cargar KPIs:", error);
  }
}

async function refrescarTodo() {
  await Promise.allSettled([cargarAplicaciones(), cargarAtencion(), cargarKPIs()]);
  cargarGraficos();
}

/* ============================ Filtros y vistas ============================ */

function filtrosActuales() {
  const buscador = document.getElementById("fCompany");
  const estado = document.getElementById("fStatus");
  return {
    q: normalizarTexto(buscador ? buscador.value : ""),
    status: estado ? estado.value : "",
  };
}

function aplicacionesFiltradas() {
  const filtros = filtrosActuales();
  return apps.filter((app) => {
    if (filtros.status && app.status !== filtros.status) return false;
    if (!filtros.q) return true;
    const texto = normalizarTexto(
      [app.company, app.position, app.location, app.notes, app.job_type, app.source].join(" ")
    );
    return texto.includes(filtros.q);
  });
}

function actualizarBotonLimpiar() {
  const boton = document.getElementById("fClearBtn");
  if (!boton) return;
  const filtros = filtrosActuales();
  boton.classList.toggle("hidden", !filtros.q && !filtros.status);
}

function aplicarVista(nuevaVista) {
  vista = nuevaVista === "tabla" ? "tabla" : "kanban";
  localStorage.setItem(VIEW_KEY, vista);

  const tabla = document.getElementById("tableSection");
  const kanban = document.getElementById("kanbanSection");
  const btnTabla = document.getElementById("viewTableBtn");
  const btnKanban = document.getElementById("viewKanbanBtn");

  tabla.classList.toggle("hidden", vista !== "tabla");
  kanban.classList.toggle("hidden", vista !== "kanban");
  btnTabla.classList.toggle("active", vista === "tabla");
  btnKanban.classList.toggle("active", vista === "kanban");
}

function renderLista() {
  const filtradas = aplicacionesFiltradas();
  const contador = document.getElementById("tableCount");
  if (contador) contador.textContent = filtradas.length;
  renderTabla(filtradas);
  renderKanban(filtradas);
}

/* ============================ Tabla ============================ */

function renderTabla(lista) {
  const tbody = document.querySelector("#table tbody");
  if (!tbody) return;

  if (!lista.length) {
    tbody.innerHTML = `<tr><td colspan="5" class="empty-state">
      No hay candidaturas con estos filtros. Prueba a limpiar la búsqueda.
    </td></tr>`;
    return;
  }

  tbody.innerHTML = lista
    .map((app) => {
      const siguiente = SIGUIENTE[app.status];
      const enlace = urlSegura(app.url);
      const puesto = enlace
        ? `<a class="link-job" href="${escaparHtml(enlace)}" target="_blank" rel="noopener noreferrer" onclick="event.stopPropagation()">${escaparHtml(app.position)} ↗</a>`
        : `<strong>${escaparHtml(app.position)}</strong>`;
      const modalidad = app.modality
        ? `<span class="badge-pill modality-${slugEstado(app.modality)}">${escaparHtml(app.modality)}</span>`
        : "";
      const extras = [app.job_type, app.source].filter(Boolean).map(escaparHtml).join(" · ");

      return `<tr onclick="abrirDetalle(${app.id})">
        <td>
          <div class="company-cell">
            <span class="company-avatar">${escaparHtml(inicial(app.company))}</span>
            <div class="company-meta">
              <strong>${escaparHtml(app.company)}</strong>
              ${app.location ? `<div class="sub-meta">📍 ${escaparHtml(app.location)}</div>` : ""}
            </div>
          </div>
        </td>
        <td>
          ${puesto}
          <div class="sub-meta" style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;">
            ${extras ? `<span>${extras}</span>` : ""} ${modalidad}
          </div>
        </td>
        <td>
          <div class="status-cell">
            <button class="chip ${claseEstado(app.status)}" onclick="event.stopPropagation(); abrirMenuEstado(event, ${app.id})" title="Cambiar estado">
              ${escaparHtml(app.status)}
            </button>
            ${
              siguiente
                ? `<button class="chip-next" onclick="event.stopPropagation(); avanzarEstado(${app.id})" title="Avanzar a ${escaparHtml(siguiente)}">→ ${escaparHtml(siguiente)}</button>`
                : ""
            }
          </div>
        </td>
        <td>${fechaCorta(app.applied_date || app.found_date)}</td>
        <td class="td-actions">
          <button class="btn-delete" title="Eliminar candidatura" onclick="event.stopPropagation(); eliminarCandidatura(${app.id})">🗑️</button>
        </td>
      </tr>`;
    })
    .join("");
}

/* ============================ Kanban ============================ */

function renderKanban(lista) {
  const board = document.getElementById("kanbanBoard");
  if (!board) return;

  board.innerHTML = ESTADOS.map((estado) => {
    const tarjetas = lista.filter((app) => app.status === estado);
    return `<section class="kanban-column kanban-column-${slugEstado(estado)}" data-estado="${escaparHtml(estado)}"
        ondragover="dragOver(event)" ondragleave="dragLeave(event)"
        ondrop="dropEnColumna(event, this.dataset.estado)">
      <div class="kanban-column-head">
        <span class="chip ${claseEstado(estado)}">${escaparHtml(estado)}</span>
        <span class="kanban-count">${tarjetas.length}</span>
      </div>
      <div class="kanban-list">
        ${
          tarjetas.length
            ? tarjetas.map(renderTarjetaKanban).join("")
            : `<div class="kanban-empty">Arrastra una tarjeta aquí</div>`
        }
      </div>
    </section>`;
  }).join("");
}

function renderTarjetaKanban(app) {
  const modalidad = app.modality
    ? `<span class="badge-pill modality-${slugEstado(app.modality)}">${escaparHtml(app.modality)}</span>`
    : "";
  return `<article class="kanban-card" draggable="true"
      ondragstart="dragStart(event, ${app.id})" ondragend="dragEnd(event)"
      onclick="abrirDetalle(${app.id})">
    <div class="kanban-card-top">
      <span class="company-avatar sm">${escaparHtml(inicial(app.company))}</span>
      <strong>${escaparHtml(app.company)}</strong>
    </div>
    <p class="kanban-position">${escaparHtml(app.position)}</p>
    <div class="kanban-meta">
      ${app.job_type ? `<span>${escaparHtml(app.job_type)}</span>` : ""}
      ${modalidad}
      <span class="kanban-date">${fechaCorta(app.applied_date || app.found_date)}</span>
    </div>
  </article>`;
}

function dragStart(event, id) {
  dragging = true;
  event.dataTransfer.effectAllowed = "move";
  event.dataTransfer.setData("text/plain", String(id));
  event.currentTarget.classList.add("dragging");
}

function dragEnd(event) {
  event.currentTarget.classList.remove("dragging");
  setTimeout(() => {
    dragging = false;
  }, 80);
}

function dragOver(event) {
  event.preventDefault();
  event.dataTransfer.dropEffect = "move";
  event.currentTarget.classList.add("drag-over");
}

function dragLeave(event) {
  if (!event.currentTarget.contains(event.relatedTarget)) {
    event.currentTarget.classList.remove("drag-over");
  }
}

function dropEnColumna(event, estado) {
  event.preventDefault();
  event.currentTarget.classList.remove("drag-over");
  const id = Number(event.dataTransfer.getData("text/plain"));
  if (id) cambiarEstado(id, estado);
}

/* ============================ Estados ============================ */

function buscarApp(id) {
  return apps.find((app) => app.id === id) || atencion.find((app) => app.id === id) || null;
}

function actualizarLocal(app, campos) {
  Object.assign(app, campos);
  renderLista();
}

async function cambiarEstado(id, nuevoEstado, opciones = {}) {
  const { undoable = true } = opciones;
  const app = buscarApp(id);
  if (!app || app.status === nuevoEstado) return;

  const anterior = app.status;
  actualizarLocal(app, {
    status: nuevoEstado,
    max_stage_reached: Math.max(app.max_stage_reached || 0, RANGO[nuevoEstado] || 0),
  });

  try {
    const actualizada = await api(`/applications/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ status: nuevoEstado }),
    });
    actualizarLocal(app, actualizada);
    await Promise.allSettled([cargarAtencion(), cargarKPIs()]);
    cargarGraficos();

    if (undoable) {
      mostrarToast(`${actualizada.company}: ${nuevoEstado}`, {
        accion: "Deshacer",
        onAccion: () => cambiarEstado(id, anterior, { undoable: false }),
      });
    }
  } catch (error) {
    actualizarLocal(app, { status: anterior });
    mostrarToast("No se pudo cambiar el estado: " + error.message, { tipo: "error" });
  }
}

function avanzarEstado(id) {
  const app = buscarApp(id);
  if (!app) return;
  const siguiente = SIGUIENTE[app.status];
  if (siguiente) cambiarEstado(id, siguiente);
}

function abrirMenuEstado(event, id) {
  event.preventDefault();
  event.stopPropagation();
  const menu = document.getElementById("statusMenu");
  if (!menu) return;

  menuCtx = id === null || id === undefined ? { captura: true } : { id };
  const app = id === null || id === undefined ? null : buscarApp(id);
  const activo = menuCtx.captura ? estadoCaptura : app ? app.status : null;

  menu.innerHTML = ESTADOS.map(
    (estado) => `<button type="button" class="${estado === activo ? "active" : ""}" onclick="seleccionarEstadoMenu('${escaparHtml(estado)}')">
      <span class="chip ${claseEstado(estado)}">${escaparHtml(estado)}</span>
    </button>`
  ).join("");

  const rect = event.currentTarget.getBoundingClientRect();
  const ancho = 220;
  let left = Math.min(rect.left, window.innerWidth - ancho - 12);
  left = Math.max(12, left);
  let top = rect.bottom + 6;
  if (top + 330 > window.innerHeight) top = Math.max(12, rect.top - 336);
  menu.style.left = left + "px";
  menu.style.top = top + "px";
  menu.classList.remove("hidden");
}

function cerrarMenuEstado() {
  const menu = document.getElementById("statusMenu");
  if (menu) menu.classList.add("hidden");
  menuCtx = null;
}

function seleccionarEstadoMenu(estado) {
  const ctx = menuCtx;
  cerrarMenuEstado();
  if (!ctx) return;
  if (ctx.captura) {
    estadoCaptura = estado;
    actualizarChipCaptura();
    actualizarPreview();
    return;
  }
  cambiarEstado(ctx.id, estado);
}

function actualizarChipCaptura() {
  const boton = document.getElementById("captureStatusBtn");
  if (!boton) return;
  boton.className = "chip capture-status " + claseEstado(estadoCaptura);
  boton.textContent = estadoCaptura;
}

function etiquetaEtapa(numero) {
  if (numero === null || numero === undefined) return "—";
  return `${numero} · ${ETAPAS[numero] || "?"}`;
}

/* ============================ Captura ============================ */

function normalizarEstado(texto) {
  const clave = normalizarTexto(texto);
  return ALIAS_ESTADO[clave] || ESTADOS.find((estado) => normalizarTexto(estado) === clave) || null;
}

function parsearCaptura(raw) {
  let texto = String(raw || "").trim();
  if (!texto) return { error: "Escribe Empresa · Puesto" };

  let estado = null;
  const coincidenciaEstado = texto.match(/\s+@([^@]+)$/);
  if (coincidenciaEstado) {
    estado = normalizarEstado(coincidenciaEstado[1]);
    if (!estado) return { error: `Estado no reconocido: @${coincidenciaEstado[1].trim()}` };
    texto = texto.slice(0, coincidenciaEstado.index).trim();
  }

  let partes = texto.split(/\s+[·|]\s+/);
  if (partes.length < 2) partes = texto.split(/\s+-\s+/);
  if (partes.length < 2) {
    const indice = texto.indexOf(":");
    if (indice > 0) partes = [texto.slice(0, indice), texto.slice(indice + 1)];
  }

  if (partes.length < 2 || !partes[0].trim() || !partes[1].trim()) {
    return { error: "Formato: Empresa · Puesto (también vale Empresa - Puesto)" };
  }

  return {
    company: partes[0].trim(),
    position: partes.slice(1).join(" - ").trim(),
    status: estado,
  };
}

function actualizarPreview() {
  const preview = document.getElementById("capturePreview");
  if (!preview) return;
  const parsed = parsearCaptura(document.getElementById("captureInput").value);
  if (parsed.error) {
    preview.textContent = "";
    return;
  }
  const estado = parsed.status || estadoCaptura;
  preview.innerHTML = `<b>${escaparHtml(parsed.company)}</b> · <b>${escaparHtml(parsed.position)}</b> → ${escaparHtml(estado)}`;
}

function mostrarMensajeCaptura(mensaje, esError = false) {
  const preview = document.getElementById("capturePreview");
  if (!preview) return;
  preview.textContent = mensaje;
  preview.style.color = esError ? "var(--danger)" : "var(--text-muted)";
  if (!esError) {
    setTimeout(() => {
      preview.style.color = "";
    }, 2500);
  }
}

function enfocarCaptura() {
  const input = document.getElementById("captureInput");
  if (!input) return;
  input.scrollIntoView({ behavior: "smooth", block: "center" });
  input.focus();
  input.select();
}

function toggleFecha() {
  fechaModo = fechaModo === "hoy" ? "ayer" : "hoy";
  const boton = document.getElementById("dateToggle");
  const etiqueta = document.getElementById("dateToggleLabel");
  if (etiqueta) etiqueta.textContent = fechaModo === "hoy" ? "Hoy" : "Ayer";
  if (boton) boton.classList.toggle("is-yesterday", fechaModo === "ayer");
  actualizarPreview();
}

async function cargarSugerencias(query) {
  const box = document.getElementById("suggestBox");
  if (!box) return;
  const q = String(query || "").trim();
  if (q.length < 2) {
    ocultarSugerencias();
    return;
  }

  try {
    const datos = await api("/applications/suggestions?q=" + encodeURIComponent(q));
    sugerenciasCache = datos;
    if (!datos.companies.length && !datos.positions.length) {
      ocultarSugerencias();
      return;
    }

    let html = "";
    if (datos.companies.length) {
      html += `<div class="suggest-group-title">Empresas</div>`;
      html += datos.companies
        .map(
          (empresa, indice) => `<button type="button" class="suggest-item" onmousedown="event.preventDefault()" onclick="aplicarSugerencia('company', ${indice})">
            🏢 <span>${escaparHtml(empresa)}</span><span class="suggest-kind">empresa</span>
          </button>`
        )
        .join("");
    }
    if (datos.positions.length) {
      html += `<div class="suggest-group-title">Puestos</div>`;
      html += datos.positions
        .map(
          (puesto, indice) => `<button type="button" class="suggest-item" onmousedown="event.preventDefault()" onclick="aplicarSugerencia('position', ${indice})">
            💼 <span>${escaparHtml(puesto)}</span><span class="suggest-kind">puesto</span>
          </button>`
        )
        .join("");
    }
    box.innerHTML = html;
    box.classList.remove("hidden");
  } catch (error) {
    console.error("Error en sugerencias:", error);
  }
}

function ocultarSugerencias() {
  const box = document.getElementById("suggestBox");
  if (box) box.classList.add("hidden");
}

function aplicarSugerencia(tipo, indice) {
  const input = document.getElementById("captureInput");
  if (!input) return;
  const parsed = parsearCaptura(input.value);

  if (tipo === "company") {
    const empresa = sugerenciasCache.companies[indice];
    input.value = empresa + " · ";
  } else {
    const puesto = sugerenciasCache.positions[indice];
    input.value = parsed.error ? puesto : `${parsed.company} · ${puesto}`;
  }

  ocultarSugerencias();
  actualizarPreview();
  input.focus();
  input.setSelectionRange(input.value.length, input.value.length);
}

async function comprobarDuplicado(company, position, mostrar = true) {
  const aviso = document.getElementById("duplicateWarning");
  if (!aviso) return null;
  if (!company || company.length < 2) {
    aviso.classList.add("hidden");
    return null;
  }

  try {
    const params = new URLSearchParams({ company });
    if (position) params.set("position", position);
    const datos = await api("/applications/check?" + params.toString());
    if (datos.duplicate) {
      aviso.textContent = "⚠ " + datos.message;
      aviso.classList.remove("hidden");
    } else {
      aviso.classList.add("hidden");
    }
    return datos;
  } catch (error) {
    if (mostrar) console.error("Error al comprobar duplicados:", error);
    return null;
  }
}

function programarComprobaciones() {
  const input = document.getElementById("captureInput");
  if (!input) return;
  const parsed = parsearCaptura(input.value);

  clearTimeout(suggestionTimer);
  suggestionTimer = setTimeout(() => {
    const partes = input.value.split(/[·|]|\s-\s/);
    const ultimo = partes[partes.length - 1].trim();
    cargarSugerencias(ultimo);
  }, 220);

  clearTimeout(duplicateTimer);
  if (parsed.error) {
    const aviso = document.getElementById("duplicateWarning");
    if (aviso) aviso.classList.add("hidden");
    return;
  }
  duplicateTimer = setTimeout(() => {
    comprobarDuplicado(parsed.company, parsed.position);
  }, 320);
}

async function guardarCaptura(event) {
  event.preventDefault();
  const input = document.getElementById("captureInput");
  const boton = document.querySelector(".capture-submit");
  if (!input) return;

  const parsed = parsearCaptura(input.value);
  if (parsed.error) {
    mostrarMensajeCaptura(parsed.error, true);
    input.focus();
    return;
  }

  const estado = parsed.status || estadoCaptura;
  const duplicado = await comprobarDuplicado(parsed.company, parsed.position);
  const fecha = fechaCaptura();

  const payload = {
    company: parsed.company,
    position: parsed.position,
    status: estado,
    found_date: fecha,
    applied_date: fecha,
  };

  if (boton) boton.disabled = true;
  try {
    const creada = await api("/applications", {
      method: "POST",
      body: JSON.stringify(payload),
    });

    input.value = "";
    ocultarSugerencias();
    const aviso = document.getElementById("duplicateWarning");
    if (aviso) aviso.classList.add("hidden");
    actualizarPreview();
    input.focus();

    await refrescarTodo();

    const extra = duplicado && duplicado.duplicate ? " " + duplicado.message : "";
    mostrarToast(`Añadida ${creada.company} · ${creada.position}.${extra}`, {
      accion: "Deshacer",
      tipo: duplicado && duplicado.duplicate ? "warn" : "",
      onAccion: async () => {
        await api(`/applications/${creada.id}`, { method: "DELETE" });
        await refrescarTodo();
        mostrarToast("Registro deshecho");
      },
    });
  } catch (error) {
    mostrarMensajeCaptura("No se pudo guardar: " + error.message, true);
  } finally {
    if (boton) boton.disabled = false;
  }
}

/* ============================ Atención ============================ */

function renderAtencion() {
  const seccion = document.getElementById("attentionSection");
  const lista = document.getElementById("attentionList");
  const contador = document.getElementById("attentionCount");
  if (!seccion || !lista || !contador) return;

  contador.textContent = atencion.length;
  if (!atencion.length) {
    seccion.classList.add("hidden");
    lista.innerHTML = "";
    return;
  }

  seccion.classList.remove("hidden");
  lista.innerHTML = atencion
    .map((app) => {
      const fecha = app.follow_up_date || app.applied_date || app.found_date;
      return `<div class="attention-item">
        <span class="company-avatar">${escaparHtml(inicial(app.company))}</span>
        <div class="attention-main">
          <strong>${escaparHtml(app.company)}</strong>
          <p>${escaparHtml(app.position)} · ${escaparHtml(app.status)} · ${fechaCorta(fecha)}</p>
        </div>
        <span class="attention-days">${app.days_waiting} días</span>
        <div class="attention-actions">
          <button class="btn-mini" onclick="hacerSeguimiento(${app.id})">Hacer seguimiento</button>
          <button class="btn-mini warn" onclick="marcarRechazada(${app.id})">Rechazar</button>
          <button class="btn-mini" onclick="abrirDetalle(${app.id})">Detalle</button>
        </div>
      </div>`;
    })
    .join("");
}

async function hacerSeguimiento(id) {
  const app = buscarApp(id);
  if (!app) return;
  const anterior = app.follow_up_date || null;
  try {
    await api(`/applications/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ follow_up_date: isoLocal() }),
    });
    await Promise.allSettled([cargarAtencion(), cargarAplicaciones(), cargarKPIs()]);
    mostrarToast(`Seguimiento registrado en ${app.company}`, {
      accion: "Deshacer",
      onAccion: async () => {
        await api(`/applications/${id}`, {
          method: "PATCH",
          body: JSON.stringify({ follow_up_date: anterior }),
        });
        await Promise.allSettled([cargarAtencion(), cargarAplicaciones()]);
      },
    });
  } catch (error) {
    mostrarToast("No se pudo registrar el seguimiento: " + error.message, { tipo: "error" });
  }
}

async function marcarRechazada(id) {
  const app = buscarApp(id);
  if (!app) return;
  const anterior = app.status;
  await cambiarEstado(id, "Rechazada", { undoable: false });
  mostrarToast(`${app.company}: marcada como rechazada`, {
    accion: "Deshacer",
    onAccion: () => cambiarEstado(id, anterior, { undoable: false }),
  });
}

/* ============================ KPIs y ritmo ============================ */

function renderKPIs() {
  const contenedor = document.getElementById("kpis");
  if (!contenedor) return;
  const k = kpis || {};
  const tarjetas = [
    ["Total", k.candidaturas_totales ?? 0, "📋", ""],
    ["Hoy", k.hoy ?? 0, "⚡", "today"],
    ["Esta semana", k.esta_semana ?? 0, "🗓️", ""],
    ["Respuestas", k.respuestas ?? 0, "💬", ""],
    ["Contactadas", k.contactadas ?? 0, "🤝", ""],
    ["Entrevistas", k.entrevistas ?? 0, "🎯", "warning"],
    ["Rechazadas", k.rechazadas ?? 0, "🚫", ""],
    ["Tasa respuesta", (k.tasa_respuesta ?? 0) + "%", "📈", "rate"],
    ["Tasa entrevista", (k.tasa_entrevista ?? 0) + "%", "🚀", "rate"],
  ];

  contenedor.innerHTML = tarjetas
    .map(
      ([etiqueta, valor, icono, clase]) => `<div class="kpi ${clase}">
        <div class="kpi-label"><span>${etiqueta}</span><span class="kpi-icon">${icono}</span></div>
        <div class="kpi-val">${valor}</div>
      </div>`
    )
    .join("");
}

function leerMetas() {
  try {
    const metas = JSON.parse(localStorage.getItem(GOALS_KEY) || "{}");
    return {
      dia: Math.max(1, Number(metas.dia) || 5),
      semana: Math.max(1, Number(metas.semana) || 25),
    };
  } catch {
    return { dia: 5, semana: 25 };
  }
}

function guardarMetas(metas) {
  localStorage.setItem(GOALS_KEY, JSON.stringify(metas));
}

function renderRitmo() {
  const metas = leerMetas();
  const diaInput = document.getElementById("goalDay");
  const semanaInput = document.getElementById("goalWeek");
  if (diaInput) diaInput.value = metas.dia;
  if (semanaInput) semanaInput.value = metas.semana;

  const hoy = kpis.hoy ?? 0;
  const semana = kpis.esta_semana ?? 0;

  const textoHoy = document.getElementById("rhythmToday");
  const textoSemana = document.getElementById("rhythmWeek");
  if (textoHoy) textoHoy.textContent = hoy;
  if (textoSemana) textoSemana.textContent = semana;

  const progresoHoy = document.getElementById("progressToday");
  const progresoSemana = document.getElementById("progressWeek");
  if (progresoHoy) progresoHoy.style.width = Math.min(100, Math.round((hoy / metas.dia) * 100)) + "%";
  if (progresoSemana) progresoSemana.style.width = Math.min(100, Math.round((semana / metas.semana) * 100)) + "%";
}

/* ============================ Detalle ============================ */

function rellenarDetalle(app) {
  if (!app) return;
  estadoDetalle = app.status;

  document.getElementById("drawerTitle").textContent = app.company;
  document.getElementById("drawerSubtitle").textContent = app.position;

  document.getElementById("dCompany").value = app.company || "";
  document.getElementById("dPosition").value = app.position || "";
  document.getElementById("dFound").value = app.found_date || "";
  document.getElementById("dApplied").value = app.applied_date || "";
  document.getElementById("dResponse").value = app.response_date || "";
  document.getElementById("dFollowUp").value = app.follow_up_date || "";
  document.getElementById("dSource").value = app.source || "";
  document.getElementById("dModality").value = app.modality || "";
  document.getElementById("dJobType").value = app.job_type || "";
  document.getElementById("dCv").value = app.cv_version || "";
  document.getElementById("dLocation").value = app.location || "";
  document.getElementById("dUrl").value = app.url || "";
  document.getElementById("dNotes").value = app.notes || "";
  document.getElementById("dId").textContent = app.id;
  document.getElementById("dStage").textContent = etiquetaEtapa(app.max_stage_reached);
  document.getElementById("dUpdated").textContent = fechaHora(app.last_update);

  renderChipsDetalle();
  const mensaje = document.getElementById("detailMsg");
  if (mensaje) mensaje.textContent = "";
}

function renderChipsDetalle() {
  const contenedor = document.getElementById("detailStatusChips");
  if (!contenedor) return;
  contenedor.innerHTML = ESTADOS.map(
    (estado) => `<button type="button" class="chip ${claseEstado(estado)} ${estado === estadoDetalle ? "active" : ""}"
      onclick="seleccionarEstadoDetalle('${escaparHtml(estado)}')">${escaparHtml(estado)}</button>`
  ).join("");
}

function seleccionarEstadoDetalle(estado) {
  estadoDetalle = estado;
  renderChipsDetalle();
}

function abrirDetalle(id) {
  if (dragging) return;
  const app = buscarApp(id);
  if (!app) return;

  drawerId = id;
  rellenarDetalle(app);

  const backdrop = document.getElementById("drawerBackdrop");
  const drawer = document.getElementById("detailDrawer");
  backdrop.classList.remove("hidden");
  drawer.classList.remove("hidden");
  drawer.setAttribute("aria-hidden", "false");
  requestAnimationFrame(() => {
    backdrop.classList.add("open");
    drawer.classList.add("open");
  });
  document.body.style.overflow = "hidden";
}

function cerrarDrawer() {
  const backdrop = document.getElementById("drawerBackdrop");
  const drawer = document.getElementById("detailDrawer");
  if (!drawer || drawer.classList.contains("hidden")) return;

  backdrop.classList.remove("open");
  drawer.classList.remove("open");
  drawer.setAttribute("aria-hidden", "true");
  document.body.style.overflow = "";
  drawerId = null;

  setTimeout(() => {
    backdrop.classList.add("hidden");
    drawer.classList.add("hidden");
  }, 240);
}

function payloadDetalle() {
  const valor = (id) => {
    const elemento = document.getElementById(id);
    return elemento ? elemento.value.trim() : "";
  };
  return {
    company: valor("dCompany"),
    position: valor("dPosition"),
    status: estadoDetalle,
    found_date: valor("dFound") || null,
    applied_date: valor("dApplied") || null,
    response_date: valor("dResponse") || null,
    follow_up_date: valor("dFollowUp") || null,
    source: valor("dSource") || null,
    modality: valor("dModality") || null,
    job_type: valor("dJobType") || null,
    cv_version: valor("dCv") || null,
    location: valor("dLocation") || null,
    url: valor("dUrl") || null,
    notes: valor("dNotes") || null,
  };
}

async function guardarDetalle(event) {
  event.preventDefault();
  if (!drawerId) return;
  const app = buscarApp(drawerId);
  if (!app) return;

  const anterior = {
    company: app.company,
    position: app.position,
    status: app.status,
    found_date: app.found_date,
    applied_date: app.applied_date,
    response_date: app.response_date,
    follow_up_date: app.follow_up_date,
    source: app.source,
    modality: app.modality,
    job_type: app.job_type,
    cv_version: app.cv_version,
    location: app.location,
    url: app.url,
    notes: app.notes,
  };

  const mensaje = document.getElementById("detailMsg");
  try {
    const actualizada = await api(`/applications/${drawerId}`, {
      method: "PATCH",
      body: JSON.stringify(payloadDetalle()),
    });
    actualizarLocal(app, actualizada);
    cerrarDrawer();
    await refrescarTodo();
    mostrarToast(`Cambios guardados en ${actualizada.company}`, {
      accion: "Deshacer",
      onAccion: async () => {
        await api(`/applications/${actualizada.id}`, {
          method: "PATCH",
          body: JSON.stringify(anterior),
        });
        await refrescarTodo();
      },
    });
  } catch (error) {
    if (mensaje) {
      mensaje.textContent = "No se pudo guardar: " + error.message;
      mensaje.style.color = "var(--danger)";
    }
  }
}

/* ============================ Eliminar ============================ */

async function eliminarCandidatura(id) {
  const app = buscarApp(id);
  if (!app) return;

  try {
    const borrada = await api(`/applications/${id}`, { method: "DELETE" });
    cerrarDrawer();
    await refrescarTodo();
    mostrarToast(`Eliminada ${borrada.company} · ${borrada.position}`, {
      accion: "Deshacer",
      onAccion: async () => {
        await api("/applications/restore", {
          method: "POST",
          body: JSON.stringify(borrada),
        });
        await refrescarTodo();
        mostrarToast("Candidatura restaurada");
      },
    });
  } catch (error) {
    mostrarToast("No se pudo eliminar: " + error.message, { tipo: "error" });
  }
}

/* ============================ Gráficos ============================ */

const baseChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      labels: {
        color: "#94a3b8",
        font: { family: "'Plus Jakarta Sans', sans-serif", size: 11, weight: 600 },
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
      ticks: { color: "#64748b", font: { family: "'Plus Jakarta Sans', sans-serif", size: 10 } },
      grid: { color: "rgba(255, 255, 255, 0.05)" },
    },
    y: {
      ticks: { color: "#64748b", font: { family: "'Plus Jakarta Sans', sans-serif", size: 10 }, precision: 0 },
      grid: { color: "rgba(255, 255, 255, 0.05)" },
    },
  },
};

function chartDisponible() {
  return typeof Chart !== "undefined";
}

async function cargarGraficos() {
  if (!chartDisponible()) return;
  await Promise.allSettled([cargarWeekly(), cargarFunnel(), cargarByType()]);
}

async function cargarWeekly() {
  try {
    const datos = await api("/stats/weekly");
    const ctx = document.getElementById("chartWeekly");
    if (!ctx) return;
    if (chartWeekly) chartWeekly.destroy();
    chartWeekly = new Chart(ctx, {
      type: "bar",
      data: {
        labels: datos.map((d) => d.semana),
        datasets: [
          {
            label: "Candidaturas",
            data: datos.map((d) => d.candidaturas),
            backgroundColor: "#38bdf8",
            borderRadius: 6,
            hoverBackgroundColor: "#7dd3fc",
          },
        ],
      },
      options: baseChartOptions,
    });
  } catch (error) {
    console.error("Error al cargar gráfico semanal:", error);
  }
}

async function cargarFunnel() {
  try {
    const datos = await api("/stats/funnel");
    const ctx = document.getElementById("chartFunnel");
    if (!ctx) return;
    if (chartFunnel) chartFunnel.destroy();
    chartFunnel = new Chart(ctx, {
      type: "bar",
      data: {
        labels: datos.map((d) => d.etapa),
        datasets: [
          {
            label: "Candidaturas",
            data: datos.map((d) => d.cantidad),
            backgroundColor: ["#64748b", "#38bdf8", "#818cf8", "#fbbf24", "#c084fc", "#34d399"],
            borderRadius: 6,
          },
        ],
      },
      options: { ...baseChartOptions, indexAxis: "y" },
    });
  } catch (error) {
    console.error("Error al cargar funnel:", error);
  }
}

async function cargarByType() {
  try {
    const datos = await api("/stats/by-type");
    const ctx = document.getElementById("chartByType");
    if (!ctx) return;
    if (chartByType) chartByType.destroy();
    chartByType = new Chart(ctx, {
      type: "bar",
      data: {
        labels: datos.map((d) => `${d.job_type} / ${d.cv_version}`),
        datasets: [
          {
            label: "Tasa de respuesta (%)",
            data: datos.map((d) => d.tasa_respuesta),
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
            ticks: { callback: (valor) => valor + "%", color: "#64748b" },
          },
        },
      },
    });
  } catch (error) {
    console.error("Error al cargar by-type:", error);
  }
}

/* ============================ Feedback tabla ============================ */

function mostrarMensajeTabla(texto, esError = false) {
  const mensaje = document.getElementById("tableMsg");
  if (!mensaje) return;
  mensaje.textContent = texto;
  mensaje.className = "table-msg" + (esError ? " error" : "");
  setTimeout(() => {
    mensaje.textContent = "";
  }, 4500);
}

/* ============================ Eventos ============================ */

function instalarEventos() {
  document.getElementById("captureForm").addEventListener("submit", guardarCaptura);

  const input = document.getElementById("captureInput");
  input.addEventListener("input", () => {
    actualizarPreview();
    programarComprobaciones();
  });
  input.addEventListener("focus", () => {
    actualizarPreview();
  });
  input.addEventListener("blur", () => {
    setTimeout(ocultarSugerencias, 160);
  });

  document.getElementById("dateToggle").addEventListener("click", toggleFecha);
  document.getElementById("captureStatusBtn").addEventListener("click", (event) => abrirMenuEstado(event, null));

  document.getElementById("fCompany").addEventListener("input", () => {
    actualizarBotonLimpiar();
    renderLista();
  });
  document.getElementById("fStatus").addEventListener("change", () => {
    actualizarBotonLimpiar();
    renderLista();
  });
  document.getElementById("fClearBtn").addEventListener("click", () => {
    document.getElementById("fCompany").value = "";
    document.getElementById("fStatus").value = "";
    actualizarBotonLimpiar();
    renderLista();
  });

  document.getElementById("viewTableBtn").addEventListener("click", () => aplicarVista("tabla"));
  document.getElementById("viewKanbanBtn").addEventListener("click", () => aplicarVista("kanban"));

  document.getElementById("drawerClose").addEventListener("click", cerrarDrawer);
  document.getElementById("drawerBackdrop").addEventListener("click", cerrarDrawer);
  document.getElementById("detailForm").addEventListener("submit", guardarDetalle);
  document.getElementById("detailDelete").addEventListener("click", () => {
    if (drawerId) eliminarCandidatura(drawerId);
  });

  document.getElementById("toastClose").addEventListener("click", ocultarToast);

  document.getElementById("goalDay").addEventListener("change", (event) => {
    const metas = leerMetas();
    metas.dia = Math.max(1, Number(event.target.value) || 5);
    guardarMetas(metas);
    renderRitmo();
  });
  document.getElementById("goalWeek").addEventListener("change", (event) => {
    const metas = leerMetas();
    metas.semana = Math.max(1, Number(event.target.value) || 25);
    guardarMetas(metas);
    renderRitmo();
  });

  document.getElementById("btnExport").addEventListener("click", () => exportar("txt"));
  document.getElementById("btnExportCsv").addEventListener("click", () => exportar("csv"));

  document.addEventListener("click", (event) => {
    const menu = document.getElementById("statusMenu");
    if (menu && !menu.classList.contains("hidden") && !menu.contains(event.target)) {
      cerrarMenuEstado();
    }
  });

  document.addEventListener("keydown", (event) => {
    const etiqueta = document.activeElement ? document.activeElement.tagName : "";
    const escribiendo = ["INPUT", "TEXTAREA", "SELECT"].includes(etiqueta);

    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      enfocarCaptura();
      return;
    }
    if (event.altKey && event.key.toLowerCase() === "a") {
      event.preventDefault();
      toggleFecha();
      return;
    }
    if (event.key === "Escape") {
      cerrarMenuEstado();
      cerrarDrawer();
      ocultarSugerencias();
      return;
    }
    if (escribiendo) return;
    if (event.key === "/" || event.key.toLowerCase() === "n") {
      event.preventDefault();
      enfocarCaptura();
    }
  });
}

async function exportar(formato) {
  const filtros = filtrosActuales();
  const params = new URLSearchParams();
  if (filtros.status) params.set("status", filtros.status);
  const ruta = formato === "csv" ? "/applications/export/csv" : "/applications/export/txt";
  try {
    mostrarMensajeTabla("Generando archivo...");
    const res = await fetch(`${ruta}?${params.toString()}`);
    if (!res.ok) throw new Error("Error al descargar");
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `candidaturas_${isoLocal()}.${formato}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
    mostrarMensajeTabla("Exportación completada");
  } catch (error) {
    mostrarMensajeTabla("No se pudo exportar: " + error.message, true);
  }
}

/* ============================ Init ============================ */

function init() {
  const hoy = new Date();
  const etiqueta = document.getElementById("todayLabel");
  if (etiqueta) {
    const texto = new Intl.DateTimeFormat("es-ES", {
      weekday: "long",
      day: "numeric",
      month: "long",
    }).format(hoy);
    etiqueta.textContent = texto.charAt(0).toUpperCase() + texto.slice(1);
  }

  actualizarChipCaptura();
  aplicarVista(vista);
  instalarEventos();
  refrescarTodo();
}

// Funciones usadas desde atributos onclick/ondrop del HTML generado.
Object.assign(window, {
  abrirDetalle,
  abrirMenuEstado,
  seleccionarEstadoMenu,
  avanzarEstado,
  eliminarCandidatura,
  hacerSeguimiento,
  marcarRechazada,
  dragStart,
  dragEnd,
  dragOver,
  dragLeave,
  dropEnColumna,
  aplicarSugerencia,
  seleccionarEstadoDetalle,
});

document.addEventListener("DOMContentLoaded", init);
