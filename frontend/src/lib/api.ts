/** Cliente de la API. El token JWT vive en localStorage; un 401 cierra la sesión. */
const TOKEN_KEY = "token";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* almacenamiento no disponible: la sesión dura lo que la pestaña */
  }
}

type Params = Record<string, string | number | boolean | null | undefined>;

function url(path: string, params?: Params) {
  const qs = new URLSearchParams();
  Object.entries(params ?? {}).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") qs.set(k, String(v));
  });
  const q = qs.toString();
  return q ? `${path}?${q}` : path;
}

async function request<T>(method: string, path: string, body?: unknown, params?: Params, raw = false): Promise<T> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  let payload: BodyInit | undefined;
  if (body instanceof FormData) payload = body;
  else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }
  let res: Response;
  try {
    res = await fetch(url(path, params), { method, headers, body: payload });
  } catch {
    throw new ApiError(0, "No hay conexión con el servidor.");
  }
  if (res.status === 401 && token) {
    setToken(null);
    window.dispatchEvent(new Event("sesion-expirada"));
  }
  if (!res.ok) {
    let message = `Error ${res.status}`;
    try {
      const data = await res.json();
      if (typeof data.detail === "string") message = data.detail;
      else if (Array.isArray(data.detail)) message = data.detail.map((d: { msg: string }) => d.msg).join(" · ");
    } catch {
      /* respuesta sin JSON */
    }
    throw new ApiError(res.status, message);
  }
  if (raw) return (await res.blob()) as T;
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string, params?: Params) => request<T>("GET", path, undefined, params),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, body ?? {}),
  put: <T>(path: string, body?: unknown) => request<T>("PUT", path, body ?? {}),
  patch: <T>(path: string, body?: unknown) => request<T>("PATCH", path, body ?? {}),
  del: <T>(path: string) => request<T>("DELETE", path),
  upload: <T>(path: string, form: FormData) => request<T>("POST", path, form),
  /** Descarga un archivo (GET si no hay body, POST si lo hay). */
  async download(path: string, filename: string, body?: unknown) {
    const blob = await request<Blob>(body === undefined ? "GET" : "POST", path, body, undefined, true);
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    link.click();
    setTimeout(() => URL.revokeObjectURL(link.href), 2000);
  },
};
