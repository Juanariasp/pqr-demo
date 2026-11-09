"use client";

import { useCallback, useEffect, useRef, useState, FormEvent } from "react";
import {
  ArrowDownToLine,
  ArrowLeft,
  ArrowRight,
  ArrowUpRight,
  Check,
  CheckCheck,
  ChevronRight,
  CircleHelp,
  Clock3,
  FileText,
  Inbox,
  LayoutDashboard,
  LoaderCircle,
  LogOut,
  Menu,
  MessageSquareText,
  Plus,
  Search,
  ShieldCheck,
  Sparkles,
  UploadCloud,
  X,
} from "lucide-react";

type Result = {
  category: string;
  reason: string;
  priority: string;
  topic: string;
  summary: string;
  relevant_data: string[];
  response: string;
  engine: string;
  model?: string;
};
type Pqr = {
  id: string;
  reference: string;
  title: string;
  text: string;
  original_text: string | null;
  file: { id: string; filename: string; size: number } | null;
  status: string;
  created_at: string;
  updated_at: string;
  result: Result | null;
  error: string | null;
};
type Health = { mode: string; ai_mode: string; max_upload_mb: number };
const labels: Record<string, string> = {
  peticion: "Petición",
  queja: "Queja",
  reclamo: "Reclamo",
  otra: "Otra",
  alta: "Alta",
  media: "Media",
  baja: "Baja",
  recibida: "Recibida",
  procesando: "En análisis",
  completada: "Completada",
  error: "Requiere atención",
};
const date = (value: string) =>
  new Intl.DateTimeFormat("es-CO", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
async function api(path: string, options?: RequestInit) {
  const response = await fetch(`/api/${path}`, {
    ...options,
    headers:
      options?.body instanceof FormData
        ? undefined
        : { "Content-Type": "application/json" },
  });
  const data = await response.json();
  if (!response.ok) {
    if (response.status === 401 && !path.startsWith("auth/"))
      window.dispatchEvent(new Event("session-expired"));
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : "Revisa los datos ingresados y vuelve a intentar.",
    );
  }
  return data;
}
function Brand() {
  return (
    <span className="brand">
      <span className="brand-icon">
        <MessageSquareText size={23} strokeWidth={1.8} />
      </span>
      nexo<span className="brand-dot">.</span>
    </span>
  );
}
function Badge({ value }: { value: string }) {
  return (
    <span className={`badge ${value}`}>
      <span />
      {labels[value] || value}
    </span>
  );
}

export default function Home() {
  const [user, setUser] = useState<{ email: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [health, setHealth] = useState<Health | null>(null);
  const [items, setItems] = useState<Pqr[]>([]);
  const [screen, setScreen] = useState<
    "dashboard" | "list" | "new" | "detail" | "help"
  >("dashboard");
  const [selected, setSelected] = useState<Pqr | null>(null);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("todas");
  const [mobile, setMobile] = useState(false);
  const refresh = useCallback(async () => {
    const values: Pqr[] = await api("pqrs");
    setItems(values);
    setSelected((previous) =>
      previous
        ? values.find((item) => item.id === previous.id) || previous
        : null,
    );
  }, []);
  useEffect(() => {
    api("health")
      .then(setHealth)
      .catch(() => {});
    api("auth/me")
      .then(setUser)
      .catch(() => {})
      .finally(() => setLoading(false));
    const expired = () => {
      setUser(null);
      setItems([]);
      setSelected(null);
      setError("Tu sesión venció. Inicia sesión nuevamente.");
    };
    window.addEventListener("session-expired", expired);
    return () => window.removeEventListener("session-expired", expired);
  }, []);
  useEffect(() => {
    if (user) refresh().catch((err) => setError(err.message));
  }, [user, refresh]);
  useEffect(() => {
    if (!busyId) return;
    const timer = setInterval(() => refresh().catch(() => {}), 2000);
    return () => clearInterval(timer);
  }, [busyId, refresh]);
  function go(next: typeof screen) {
    setScreen(next);
    setMobile(false);
    setError("");
  }
  async function analyze(item: Pqr) {
    setBusyId(item.id);
    setError("");
    try {
      const value = await api(`pqrs/${item.id}/analyze`, { method: "POST" });
      setSelected(value);
      await refresh();
    } catch (err) {
      setError((err as Error).message);
      await refresh().catch(() => {});
    } finally {
      setBusyId(null);
    }
  }
  async function created(item: Pqr) {
    setSelected(item);
    setScreen("detail");
    await refresh();
    await analyze(item);
  }
  if (loading)
    return (
      <div className="initial">
        <Brand />
        <LoaderCircle className="spin" />
        <p>Preparando tu espacio…</p>
      </div>
    );
  if (!user)
    return (
      <Login
        onLogin={(value) => {
          setUser(value);
          setError("");
          setScreen("dashboard");
        }}
        initialError={error}
        health={health}
      />
    );
  const completed = items.filter((item) => item.status === "completada").length;
  const pending = items.filter((item) =>
    ["recibida", "procesando"].includes(item.status),
  ).length;
  const filtered = items.filter(
    (item) =>
      (filter === "todas" || item.status === filter) &&
      `${item.title} ${item.reference} ${item.result?.topic || ""}`
        .toLowerCase()
        .includes(search.toLowerCase()),
  );
  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobile ? "open" : ""}`}>
        <div className="sidebar-top">
          <Brand />
          <button
            className="icon-button mobile-only"
            aria-label="Cerrar menú"
            onClick={() => setMobile(false)}
          >
            <X size={20} />
          </button>
        </div>
        <div className="workspace">
          <span className="workspace-icon">P</span>
          <div>
            <strong>Portal de solicitudes</strong>
            <small>Tu espacio personal</small>
          </div>
          <ChevronRight size={15} />
        </div>
        <p className="nav-label">PRINCIPAL</p>
        <nav>
          <button
            className={screen === "dashboard" ? "active" : ""}
            onClick={() => go("dashboard")}
          >
            <LayoutDashboard size={19} />
            Resumen
          </button>
          <button
            className={["list", "detail"].includes(screen) ? "active" : ""}
            onClick={() => go("list")}
          >
            <Inbox size={19} />
            Mis solicitudes<span className="nav-count">{items.length}</span>
          </button>
          <button
            className={screen === "new" ? "active" : ""}
            onClick={() => go("new")}
          >
            <Plus size={19} />
            Nueva solicitud
          </button>
        </nav>
        <div className="sidebar-bottom">
          <div className="demo-card">
            <span className="tiny-spark">
              <Sparkles size={17} />
            </span>
            <strong>Una mejor forma de escuchar</strong>
            <p>Cada solicitud es el primer paso hacia una solución.</p>
            <span>DEMO · DATOS FICTICIOS</span>
          </div>
          <button
            className={`help-link ${screen === "help" ? "active" : ""}`}
            onClick={() => go("help")}
          >
            <CircleHelp size={18} />
            Guía de la demo
            <ArrowUpRight size={14} />
          </button>
          <div className="profile">
            <span className="avatar">{user.email.charAt(0).toUpperCase()}</span>
            <div>
              <strong>Mi cuenta</strong>
              <small title={user.email}>{user.email}</small>
            </div>
            <button
              aria-label="Cerrar sesión"
              className="icon-button"
              onClick={async () => {
                try {
                  await api("auth/logout", { method: "POST" });
                  setUser(null);
                  setItems([]);
                  setSelected(null);
                } catch (err) {
                  setError((err as Error).message);
                }
              }}
            >
              <LogOut size={17} />
            </button>
          </div>
        </div>
      </aside>
      {mobile && (
        <button
          className="scrim"
          aria-label="Cerrar menú"
          onClick={() => setMobile(false)}
        />
      )}
      <main className="main">
        <header className="topbar">
          <div className="breadcrumb">
            <button
              className="icon-button mobile-only"
              aria-label="Abrir menú"
              onClick={() => setMobile(true)}
            >
              <Menu size={20} />
            </button>
            Mi espacio
            <ChevronRight size={14} />
            <strong>
              {
                {
                  dashboard: "Resumen",
                  list: "Mis solicitudes",
                  new: "Nueva solicitud",
                  detail: "Detalle de solicitud",
                  help: "Guía de la demo",
                }[screen]
              }
            </strong>
          </div>
          <span className="environment">
            <span />
            {health?.mode === "cloud" ? "Firebase conectado" : "Entorno local"}
          </span>
        </header>
        <div className="page-content">
          {error && (
            <div className="error-banner" role="alert">
              {error}
              <button aria-label="Cerrar aviso" onClick={() => setError("")}>
                <X size={17} />
              </button>
            </div>
          )}
          {screen === "dashboard" && (
            <>
              <div className="page-heading">
                <div>
                  <div className="eyebrow">TU VOZ CUENTA</div>
                  <h1>
                    Todo empieza con escucharte<span>.</span>
                  </h1>
                  <p>
                    Gestiona tus peticiones, quejas y reclamos desde un solo
                    lugar.
                  </p>
                </div>
                <button className="primary" onClick={() => go("new")}>
                  <Plus size={18} />
                  Nueva solicitud
                </button>
              </div>
              <div className="stats">
                <Stat
                  label="Total de solicitudes"
                  value={items.length}
                  note="Todas tus conversaciones"
                  icon={<Inbox size={20} />}
                />
                <Stat
                  label="En seguimiento"
                  value={pending}
                  note="Recibidas o en análisis"
                  icon={<Clock3 size={20} />}
                />
                <Stat
                  label="Análisis completados"
                  value={completed}
                  note="Con una respuesta sugerida"
                  icon={<CheckCheck size={20} />}
                />
              </div>
              <section className="feature">
                <div className="feature-copy">
                  <span className="tag">
                    <Sparkles size={13} />
                    ASISTENCIA INTELIGENTE
                  </span>
                  <h2>
                    Cuéntanos qué pasó.
                    <br />
                    Te ayudamos con el siguiente paso.
                  </h2>
                  <p>
                    Escribe tu solicitud o adjunta un documento. Nuestro
                    asistente organiza la información y prepara una respuesta
                    para revisión.
                  </p>
                  <button onClick={() => go("new")}>
                    Crear mi primera solicitud
                    <ArrowUpRight size={17} />
                  </button>
                </div>
                <div className="feature-art" aria-hidden="true">
                  <div className="art-orbit orbit-one" />
                  <div className="art-orbit orbit-two" />
                  <div className="art-note">
                    <div className="art-note-icon">
                      <MessageSquareText size={25} />
                    </div>
                    <span className="art-line long" />
                    <span className="art-line" />
                    <span className="art-line short" />
                    <div className="art-note-footer">
                      <span />
                      <span />
                      <span />
                      <i>
                        <Check size={15} />
                      </i>
                    </div>
                  </div>
                  <span className="art-star">
                    <Sparkles size={24} />
                  </span>
                  <div className="art-pill">
                    <span />
                    <CheckCheck size={15} />
                    Información organizada
                  </div>
                </div>
              </section>
            </>
          )}
          {(screen === "list" || screen === "dashboard") && (
            <section className="requests">
              <div className="section-heading">
                <div>
                  <h2>
                    {screen === "dashboard"
                      ? "Tus últimas solicitudes"
                      : "Mis solicitudes"}
                  </h2>
                  <p>
                    {screen === "dashboard"
                      ? "Consulta el estado y los detalles de cada caso."
                      : "El historial de lo que has compartido con nosotros."}
                  </p>
                </div>
                {screen === "dashboard" ? (
                  <button className="text-button" onClick={() => go("list")}>
                    Ver todas
                    <ArrowRight size={15} />
                  </button>
                ) : (
                  <button className="primary" onClick={() => go("new")}>
                    <Plus size={18} />
                    Nueva solicitud
                  </button>
                )}
              </div>
              {screen === "list" && (
                <div className="table-tools">
                  <div className="search-field">
                    <Search size={17} />
                    <input
                      aria-label="Buscar solicitudes"
                      value={search}
                      placeholder="Buscar por asunto o radicado…"
                      onChange={(event) => setSearch(event.target.value)}
                    />
                  </div>
                  <select
                    aria-label="Filtrar por estado"
                    value={filter}
                    onChange={(event) => setFilter(event.target.value)}
                  >
                    <option value="todas">Todos los estados</option>
                    {["recibida", "procesando", "completada", "error"].map(
                      (status) => (
                        <option key={status} value={status}>
                          {labels[status]}
                        </option>
                      ),
                    )}
                  </select>
                  <button
                    className="secondary"
                    onClick={() =>
                      refresh().catch((err) => setError(err.message))
                    }
                  >
                    Actualizar
                  </button>
                </div>
              )}
              {(screen === "dashboard" ? items : filtered).length ? (
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>SOLICITUD</th>
                        <th>TIPO</th>
                        <th>ESTADO</th>
                        <th>FECHA</th>
                        <th>
                          <span className="sr-only">Ver detalle</span>
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {(screen === "dashboard"
                        ? items.slice(0, 5)
                        : filtered
                      ).map((item) => (
                        <tr key={item.id}>
                          <td>
                            <button
                              className="row-title"
                              onClick={() => {
                                setSelected(item);
                                go("detail");
                              }}
                            >
                              <span className="file-icon">
                                <FileText size={19} />
                              </span>
                              <span>
                                <strong>{item.title}</strong>
                                <small>{item.reference}</small>
                              </span>
                            </button>
                          </td>
                          <td>
                            {item.result ? (
                              labels[item.result.category]
                            ) : (
                              <span className="muted">Por clasificar</span>
                            )}
                          </td>
                          <td>
                            <Badge value={item.status} />
                          </td>
                          <td className="date-cell">{date(item.created_at)}</td>
                          <td>
                            <button
                              className="icon-button"
                              aria-label={`Ver ${item.reference}`}
                              onClick={() => {
                                setSelected(item);
                                go("detail");
                              }}
                            >
                              <ArrowUpRight size={18} />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="empty">
                  <div className="empty-icon">
                    <Inbox size={28} strokeWidth={1.5} />
                  </div>
                  <h3>
                    {items.length
                      ? "Sin coincidencias"
                      : "Tu próxima conversación empieza aquí"}
                  </h3>
                  <p>
                    {items.length
                      ? "Intenta con otra búsqueda o cambia el estado."
                      : "Todavía no tienes solicitudes. Cuando crees una, podrás seguir su avance desde este espacio."}
                  </p>
                  {!items.length && (
                    <button className="secondary" onClick={() => go("new")}>
                      <Plus size={16} />
                      Crear una solicitud
                    </button>
                  )}
                </div>
              )}
            </section>
          )}
          {screen === "new" && (
            <NewPqr
              health={health}
              onCreated={created}
              onBack={() => go("dashboard")}
            />
          )}
          {screen === "detail" && selected && (
            <Detail
              item={selected}
              busy={busyId === selected.id}
              onBack={() => go("list")}
              onAnalyze={() => analyze(selected)}
            />
          )}
          {screen === "help" && (
            <section className="help-page">
              <div className="eyebrow">GUÍA DE LA DEMO</div>
              <h1>Un recorrido sencillo, de principio a fin.</h1>
              <p>
                Esta plataforma es un prototipo de entrevista. Usa únicamente
                información ficticia.
              </p>
              {[
                [
                  "01",
                  "Comparte tu solicitud",
                  "Escribe al menos 20 caracteres o adjunta un Word o PDF de hasta 5 MB. Si el PDF está escaneado, escribe su contenido manualmente.",
                ],
                [
                  "02",
                  "Revisa antes de enviar",
                  "El texto extraído aparece en un campo editable. Puedes corregirlo y complementar los datos. El documento original se conserva por separado.",
                ],
                [
                  "03",
                  "Consulta el análisis",
                  "La solicitud pasa por recibida, en análisis y completada. Si falla el modelo, verás el estado de error y podrás reintentar. La respuesta siempre requiere revisión humana.",
                ],
              ].map(([n, t, d]) => (
                <article key={n}>
                  <span>{n}</span>
                  <div>
                    <h2>{t}</h2>
                    <p>{d}</p>
                  </div>
                </article>
              ))}
              <div className="info-note">
                <ShieldCheck size={21} />
                <p>
                  {health?.mode === "cloud"
                    ? "Firebase autentica tu cuenta. Tus solicitudes y archivos solo se sirven después de validar tu identidad y propiedad."
                    : "En modo local, las cuentas y solicitudes se guardan en este equipo. Las reglas de ensayo no son un modelo de IA."}{" "}
                  {health?.ai_mode === "gemini"
                    ? "El análisis usa tres agentes Google ADK con Gemini."
                    : "El análisis actual usa reglas locales sin consumo de APIs."}
                </p>
              </div>
            </section>
          )}
          <footer className="footer">
            <span>Hecho para escucharte.</span>
            <span>
              <ShieldCheck size={13} />
              {health?.ai_mode === "gemini"
                ? "Google ADK · Gemini"
                : "Demo local · Análisis por reglas"}
              <span className="footer-dot">·</span>Solo datos ficticios
            </span>
          </footer>
        </div>
      </main>
    </div>
  );
}

function Stat({
  label,
  value,
  note,
  icon,
}: {
  label: string;
  value: number;
  note: string;
  icon: React.ReactNode;
}) {
  return (
    <article className="stat">
      <div>
        <p>{label}</p>
        <strong>{value.toString().padStart(2, "0")}</strong>
        <small>{note}</small>
      </div>
      <span className="stat-icon">{icon}</span>
    </article>
  );
}

function Login({
  onLogin,
  initialError,
  health,
}: {
  onLogin: (user: { email: string }) => void;
  initialError: string;
  health: Health | null;
}) {
  const [register, setRegister] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(initialError);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const data = new FormData(event.currentTarget);
    try {
      onLogin(
        await api(register ? "auth/register" : "auth/login", {
          method: "POST",
          body: JSON.stringify({
            email: data.get("email"),
            password: data.get("password"),
          }),
        }),
      );
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="login-page">
      <section className="login-story">
        <Brand />
        <div className="login-message">
          <span className="tag">
            <MessageSquareText size={14} />
            UN ESPACIO PARA TU VOZ
          </span>
          <h1>
            Las buenas soluciones
            <br />
            empiezan con una
            <br />
            <em>conversación.</em>
          </h1>
          <p>
            Un lugar para compartir lo que necesitas,
            <br />
            hacer seguimiento y encontrar claridad.
          </p>
          <div className="login-points">
            <span>
              <Check size={16} />
              Todo en un solo lugar
            </span>
            <span>
              <Check size={16} />
              Respuestas con contexto
            </span>
          </div>
        </div>
        <small>Portal de peticiones, quejas y reclamos · Demo</small>
        <div className="login-ring" aria-hidden="true" />
      </section>
      <section className="login-form-side">
        <div className="login-form-wrap">
          <span className="login-kicker">BIENVENIDO A NEXO</span>
          <h2>{register ? "Crea tu espacio." : "Qué bueno tenerte aquí."}</h2>
          <p>
            {register
              ? "Regístrate para gestionar tus solicitudes."
              : "Ingresa a tu cuenta para continuar."}
          </p>
          <form onSubmit={submit}>
            {error && (
              <div className="error-banner" role="alert">
                {error}
              </div>
            )}
            <label htmlFor="email">Correo electrónico</label>
            <input
              id="email"
              name="email"
              type="email"
              autoComplete="email"
              placeholder="tu@correo.com"
              required
              maxLength={254}
            />
            <label htmlFor="password">Contraseña</label>
            <input
              id="password"
              name="password"
              type="password"
              autoComplete={register ? "new-password" : "current-password"}
              placeholder="Mínimo 8 caracteres"
              minLength={8}
              maxLength={128}
              required
            />
            <button className="primary" type="submit" disabled={busy}>
              {busy ? (
                <LoaderCircle className="spin" size={18} />
              ) : (
                <>
                  {register ? "Crear cuenta" : "Iniciar sesión"}
                  <ArrowRight size={18} />
                </>
              )}
            </button>
          </form>
          <div className="login-switch">
            {register ? "¿Ya tienes cuenta?" : "¿Es tu primera vez?"}
            <button
              onClick={() => {
                setRegister(!register);
                setError("");
              }}
            >
              {register ? "Inicia sesión" : "Crea una cuenta"}
            </button>
          </div>
          <div className="login-disclaimer">
            <ShieldCheck size={18} />
            <span>
              {health?.mode === "cloud"
                ? "Acceso protegido con Firebase Authentication."
                : "Modo local listo para ensayar. Crea una cuenta de prueba."}
              <br />
              Usa únicamente datos ficticios.
            </span>
          </div>
        </div>
        <span className="login-bottom">Tu voz tiene un lugar aquí.</span>
      </section>
    </main>
  );
}

function NewPqr({
  health,
  onCreated,
  onBack,
}: {
  health: Health | null;
  onCreated: (item: Pqr) => Promise<void>;
  onBack: () => void;
}) {
  const [title, setTitle] = useState(""),
    [text, setText] = useState(""),
    [upload, setUpload] = useState<{ id: string; filename: string } | null>(
      null,
    ),
    [busy, setBusy] = useState(false),
    [extracting, setExtracting] = useState(false),
    [error, setError] = useState("");
  const input = useRef<HTMLInputElement>(null);
  async function load(file: File | undefined) {
    if (!file) return;
    setError("");
    if (!/\.(docx|pdf)$/i.test(file.name)) {
      setError("Selecciona un Word (.docx) o PDF (.pdf).");
      return;
    }
    if (!file.size || file.size > (health?.max_upload_mb || 5) * 1024 * 1024) {
      setError("El archivo está vacío o supera el tamaño permitido.");
      return;
    }
    setExtracting(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const data = await api("uploads", { method: "POST", body: form });
      setUpload(data);
      setText(data.text);
      if (!title) setTitle(file.name.replace(/\.[^.]+$/, "").slice(0, 120));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setExtracting(false);
      if (input.current) input.current.value = "";
    }
  }
  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const item = await api("pqrs", {
        method: "POST",
        body: JSON.stringify({
          title: title.trim(),
          text: text.trim(),
          upload_id: upload?.id || null,
        }),
      });
      await onCreated(item);
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }
  return (
    <>
      <button className="back" onClick={onBack}>
        <ArrowLeft size={16} />
        Volver al resumen
      </button>
      <div className="page-heading">
        <div>
          <div className="eyebrow">TE ESCUCHAMOS</div>
          <h1>
            Cuéntanos qué necesitas<span>.</span>
          </h1>
          <p>Comparte los detalles. Nosotros te ayudamos a organizarlos.</p>
        </div>
      </div>
      <div className="create-layout">
        <form className="form-card" onSubmit={submit}>
          <div className="form-card-title">
            <span className="file-icon">
              <FileText size={21} />
            </span>
            <div>
              <h2>Nueva solicitud</h2>
              <p>Los campos marcados con * son obligatorios.</p>
            </div>
          </div>
          {error && (
            <div className="error-banner" role="alert">
              {error}
            </div>
          )}
          <label htmlFor="title">Asunto *</label>
          <input
            id="title"
            placeholder="Ej. Revisión de cobro en mi factura"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            minLength={5}
            maxLength={120}
            required
            disabled={busy}
          />
          <label>
            Documento <span className="muted">(opcional)</span>
          </label>
          <input
            ref={input}
            type="file"
            id="document"
            accept=".docx,.pdf"
            className="sr-only"
            onChange={(event) => load(event.target.files?.[0])}
            disabled={busy || extracting}
          />
          <button
            className={`upload-zone ${upload ? "has-upload" : ""}`}
            type="button"
            onClick={() => input.current?.click()}
            disabled={busy || extracting}
          >
            {extracting ? (
              <LoaderCircle size={26} className="spin" />
            ) : upload ? (
              <CheckCheck size={27} />
            ) : (
              <UploadCloud size={27} />
            )}
            <strong>
              {extracting
                ? "Extrayendo el texto del documento…"
                : upload
                  ? upload.filename
                  : "Selecciona un documento"}
            </strong>
            <small>
              {upload
                ? "Texto extraído. Puedes editarlo antes de enviar."
                : `Word o PDF · Hasta ${health?.max_upload_mb || 5} MB`}
            </small>
          </button>
          {upload && (
            <button
              type="button"
              className="text-button remove-file"
              onClick={() => setUpload(null)}
              disabled={busy}
            >
              Quitar documento adjunto
              <X size={13} />
            </button>
          )}
          <div className="field-label">
            <label htmlFor="text">
              {upload ? "Vista previa editable *" : "Describe tu solicitud *"}
            </label>
            <span>{text.length.toLocaleString("es-CO")} / 20.000</span>
          </div>
          <textarea
            id="text"
            value={text}
            onChange={(event) => setText(event.target.value)}
            placeholder="Cuéntanos qué ocurrió, cuándo pasó y qué solución esperas. Incluye las referencias que nos ayuden a entender tu caso."
            minLength={20}
            maxLength={20000}
            rows={9}
            required
            disabled={busy || extracting}
          />
          <p className="field-help">
            Incluye al menos 20 caracteres. Usa únicamente datos ficticios.
          </p>
          <div className="form-actions">
            <button
              type="button"
              className="secondary"
              onClick={onBack}
              disabled={busy}
            >
              Cancelar
            </button>
            <button
              type="submit"
              className="primary"
              disabled={
                busy ||
                extracting ||
                text.trim().length < 20 ||
                title.trim().length < 5
              }
            >
              {busy ? (
                <LoaderCircle size={17} className="spin" />
              ) : (
                <ArrowUpRight size={17} />
              )}
              {busy ? "Enviando solicitud…" : "Enviar solicitud"}
            </button>
          </div>
        </form>
        <aside className="form-aside">
          <span className="aside-spark">
            <Sparkles size={24} />
          </span>
          <h2>¿Qué pasa después?</h2>
          {[
            [
              "1",
              "Recibimos tu solicitud",
              "Guardamos tu texto y el documento adjunto.",
            ],
            [
              "2",
              "Organizamos la información",
              "Identificamos el tipo, el tema y la prioridad.",
            ],
            [
              "3",
              "Preparamos una respuesta",
              "Podrás consultar una sugerencia para revisión.",
            ],
          ].map(([n, t, d]) => (
            <div className="aside-step" key={n}>
              <span>{n}</span>
              <div>
                <strong>{t}</strong>
                <p>{d}</p>
              </div>
            </div>
          ))}
          <p className="aside-note">
            Tu solicitud solo es visible desde tu cuenta. La respuesta generada
            es una sugerencia y requiere revisión humana.
          </p>
        </aside>
      </div>
    </>
  );
}

function Detail({
  item,
  busy,
  onBack,
  onAnalyze,
}: {
  item: Pqr;
  busy: boolean;
  onBack: () => void;
  onAnalyze: () => void;
}) {
  const [downloadError, setDownloadError] = useState("");
  async function download() {
    try {
      const response = await fetch(`/api/pqrs/${item.id}/file`);
      if (!response.ok)
        throw new Error("No se pudo descargar el archivo. Revisa tu sesión.");
      const url = URL.createObjectURL(await response.blob());
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = item.file!.filename;
      anchor.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (err) {
      setDownloadError((err as Error).message);
    }
  }
  return (
    <>
      <button className="back" onClick={onBack}>
        <ArrowLeft size={16} />
        Mis solicitudes
      </button>
      <div className="page-heading detail-heading">
        <div>
          <div className="eyebrow">{item.reference}</div>
          <h1>{item.title}</h1>
          <p>
            Creada el {date(item.created_at)} · Actualizada el{" "}
            {date(item.updated_at)}
          </p>
        </div>
        <Badge value={busy ? "procesando" : item.status} />
      </div>
      <div className="detail-grid">
        <section className="detail-card">
          <h2>
            <MessageSquareText size={20} />
            Tu solicitud
          </h2>
          <p className="original-text">{item.text}</p>
          {item.file && (
            <>
              <button className="attachment" onClick={download}>
                <span className="file-icon">
                  <FileText size={19} />
                </span>
                <span>
                  <strong>{item.file.filename}</strong>
                  <small>
                    {(item.file.size / 1024).toFixed(1)} KB · Documento original
                  </small>
                </span>
                <ArrowDownToLine size={18} />
              </button>
              {downloadError && (
                <p role="alert" className="inline-error">
                  {downloadError}
                </p>
              )}
            </>
          )}
          {item.original_text && (
            <details>
              <summary>Ver texto extraído del documento original</summary>
              <p className="original-text">{item.original_text}</p>
            </details>
          )}
        </section>
        <section className="detail-card analysis-card">
          <div className="analysis-title">
            <h2>
              <Sparkles size={20} />
              Análisis de la solicitud
            </h2>
            <span className="small-tag">ASISTIDO</span>
          </div>
          {busy ? (
            <div className="analyzing" role="status">
              <LoaderCircle size={32} className="spin" />
              <h3>Estamos organizando tu solicitud</h3>
              <p>Clasificación → análisis → respuesta sugerida</p>
              <small>Puedes consultar el historial mientras finaliza.</small>
            </div>
          ) : item.result ? (
            <>
              <div className="result-tags">
                <Badge value={item.result.category} />
                <Badge value={item.result.priority} />
              </div>
              <h3>{item.result.topic}</h3>
              <p>{item.result.summary}</p>
              <details>
                <summary>¿Por qué esta clasificación?</summary>
                <p>{item.result.reason}</p>
              </details>
              {item.result.relevant_data.length > 0 && (
                <div className="facts">
                  <h4>Información identificada</h4>
                  <ul>
                    {item.result.relevant_data.map((fact, i) => (
                      <li key={i}>{fact}</li>
                    ))}
                  </ul>
                </div>
              )}
              <div className="suggested">
                <div>
                  <CheckCheck size={18} />
                  <h3>Respuesta sugerida</h3>
                </div>
                <p>{item.result.response}</p>
              </div>
              <div className="result-disclaimer">
                <ShieldCheck size={15} />
                <small>
                  Requiere revisión humana.{" "}
                  {item.result.engine === "google-adk"
                    ? `Google ADK · ${item.result.model}`
                    : "Ensayo con reglas locales; sin IA generativa."}
                </small>
              </div>
            </>
          ) : (
            <div className="analyzing">
              {item.error && (
                <p className="inline-error" role="alert">
                  {item.error}
                </p>
              )}
              <p>
                {item.status === "procesando"
                  ? "El análisis está en curso. Si se interrumpió, podrás recuperarlo al cabo de dos minutos."
                  : "Tu solicitud está guardada. Inicia el análisis cuando quieras."}
              </p>
              <button className="primary" onClick={onAnalyze}>
                <Sparkles size={16} />
                {item.status === "error" || item.status === "procesando"
                  ? "Reintentar análisis"
                  : "Analizar solicitud"}
              </button>
            </div>
          )}
        </section>
      </div>
    </>
  );
}
