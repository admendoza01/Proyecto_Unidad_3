// Lógica del cliente web: captura el formulario y llama a la API con fetch()

const API_URL = "/predict"; // mismo origen que sirve FastAPI

const form = document.getElementById("form-cliente");
const btnEnviar = document.getElementById("btn-enviar");
const btnLimpiar = document.getElementById("btn-limpiar");
const cajaErrores = document.getElementById("errores");
const estadoVacio = document.getElementById("estado-vacio");
const cargando = document.getElementById("cargando");
const tarjeta = document.getElementById("tarjeta-resultado");

const CAMPOS_ENTERO = ["edad", "antiguedad_meses", "num_productos", "nivel_satisfaccion"];
const CAMPOS_DECIMAL = ["ingresos_anuales", "saldo_cuenta"];
const CAMPOS_TEXTO = ["id_cliente", "nivel_estudios", "tipo_cuenta", "canal_preferido"];

/* ---------- Utilidades de interfaz ---------- */

function mostrarErrores(mensajes) {
  cajaErrores.innerHTML =
    "<strong>Revisa los datos:</strong><ul>" +
    mensajes.map((m) => `<li>${escapar(m)}</li>`).join("") +
    "</ul>";
  cajaErrores.hidden = false;
}

function ocultarErrores() {
  cajaErrores.hidden = true;
  cajaErrores.innerHTML = "";
  form.querySelectorAll(".invalido").forEach((el) => el.classList.remove("invalido"));
}

function escapar(texto) {
  const div = document.createElement("div");
  div.textContent = texto;
  return div.innerHTML;
}

function mostrarEstado(estado) {
  estadoVacio.hidden = estado !== "vacio";
  cargando.hidden = estado !== "cargando";
  tarjeta.hidden = estado !== "resultado";
}

/* ---------- Construcción y validación del payload ---------- */

function construirPayload() {
  const datos = new FormData(form);
  const payload = {};
  const errores = [];

  CAMPOS_TEXTO.forEach((campo) => {
    const valor = (datos.get(campo) || "").toString().trim();
    if (!valor) {
      errores.push(`El campo «${campo}» es obligatorio.`);
      form.elements[campo].classList.add("invalido");
    }
    payload[campo] = valor;
  });

  [...CAMPOS_ENTERO, ...CAMPOS_DECIMAL].forEach((campo) => {
    const bruto = (datos.get(campo) || "").toString().trim();
    const numero = Number(bruto);
    if (bruto === "" || Number.isNaN(numero)) {
      errores.push(`El campo «${campo}» debe ser un número.`);
      form.elements[campo].classList.add("invalido");
    } else if (CAMPOS_ENTERO.includes(campo) && !Number.isInteger(numero)) {
      errores.push(`El campo «${campo}» debe ser un número entero.`);
      form.elements[campo].classList.add("invalido");
    }
    payload[campo] = numero;
  });

  payload.tiene_tarjeta = form.elements["tiene_tarjeta"].checked;

  // Regla cruzada igual que en el backend (schemas.py)
  if (
    Number.isFinite(payload.edad) &&
    Number.isFinite(payload.antiguedad_meses) &&
    payload.antiguedad_meses > (payload.edad - 18) * 12
  ) {
    errores.push("La antigüedad no puede superar los meses transcurridos desde los 18 años de edad.");
    form.elements["antiguedad_meses"].classList.add("invalido");
  }

  return { payload, errores };
}

/* ---------- Mensajes de error de la API ---------- */

function formatearErrorApi(cuerpo, status) {
  // FastAPI/Pydantic devuelve 422 con detail = [{loc, msg}, ...]
  if (Array.isArray(cuerpo?.detail)) {
    return cuerpo.detail.map((e) => {
      const campo = e.loc ? e.loc[e.loc.length - 1] : "";
      return campo ? `${campo}: ${e.msg}` : e.msg;
    });
  }
  if (typeof cuerpo?.detail === "string") return [cuerpo.detail];
  return [`Error inesperado del servidor (HTTP ${status}).`];
}

/* ---------- Pintado del resultado ---------- */

function pintarResultado(r) {
  const porcentaje = (r.probabilidad_abandono * 100).toFixed(1);
  const clase = `riesgo-${r.nivel_riesgo.toLowerCase()}`;

  tarjeta.className = `tarjeta ${clase}`;
  document.getElementById("res-id").textContent = r.id_cliente;
  document.getElementById("res-nivel").textContent = `Riesgo ${r.nivel_riesgo}`;
  document.getElementById("res-prob").textContent = `${porcentaje}%`;
  document.getElementById("res-abandono").textContent =
    r.abandono === 1 ? "El modelo predice abandono" : "El modelo predice que el cliente permanece";
  document.getElementById("res-accion").textContent = r.accion_recomendada;

  const barra = document.getElementById("res-barra");
  barra.style.width = "0";
  requestAnimationFrame(() => {
    barra.style.width = `${porcentaje}%`;
  });

  mostrarEstado("resultado");
}

/* ---------- Eventos ---------- */

form.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  ocultarErrores();

  const { payload, errores } = construirPayload();
  if (errores.length) {
    mostrarErrores(errores);
    return;
  }

  btnEnviar.disabled = true;
  mostrarEstado("cargando");

  try {
    const respuesta = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const cuerpo = await respuesta.json().catch(() => ({}));

    if (!respuesta.ok) {
      mostrarErrores(formatearErrorApi(cuerpo, respuesta.status));
      mostrarEstado("vacio");
      return;
    }

    pintarResultado(cuerpo);
  } catch (error) {
    mostrarErrores(["No se pudo conectar con la API. Comprueba que el servidor está en marcha."]);
    mostrarEstado("vacio");
  } finally {
    btnEnviar.disabled = false;
  }
});

btnLimpiar.addEventListener("click", () => {
  form.reset();
  ocultarErrores();
  mostrarEstado("vacio");
});
