import { animate, useMotionValue, useReducedMotion } from "framer-motion";
import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api";

type Params = Record<string, string | number | boolean | null | undefined>;

/** Carga datos de la API; vuelve a cargar cuando cambian path o params. */
export function useApi<T>(path: string | null, params?: Params) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(path !== null);
  const [tick, setTick] = useState(0);
  const key = JSON.stringify(params ?? {});

  useEffect(() => {
    if (path === null) return;
    let alive = true;
    setLoading(true);
    setError(null);
    api
      .get<T>(path, JSON.parse(key))
      .then((d) => alive && setData(d))
      .catch((e: Error) => alive && setError(e.message))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [path, key, tick]);

  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { data, error, loading, reload, setData };
}

/** Número que cuenta animado hasta su valor. */
export function useCountUp(value: number | null | undefined, duration = 0.9) {
  const reduced = useReducedMotion();
  const mv = useMotionValue(0);
  const [display, setDisplay] = useState(0);
  useEffect(() => {
    if (value == null) return;
    if (reduced) {
      setDisplay(value);
      return;
    }
    const controls = animate(mv, value, { duration, ease: [0.22, 1, 0.36, 1], onUpdate: setDisplay });
    return () => controls.stop();
  }, [value, duration, mv, reduced]);
  return value == null ? null : display;
}

/** Atajo de teclado global (p. ej. Ctrl+K). */
export function useHotkey(key: string, handler: () => void) {
  const ref = useRef(handler);
  useEffect(() => {
    ref.current = handler;
  });
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === key) {
        e.preventDefault();
        ref.current();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [key]);
}

export function useDebounced<T>(value: T, ms = 250) {
  const [v, setV] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setV(value), ms);
    return () => clearTimeout(id);
  }, [value, ms]);
  return v;
}
