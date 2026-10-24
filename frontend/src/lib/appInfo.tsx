import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api } from "./api";

export interface AppInfo {
  demo_mode: boolean;
  reset_hours: number | null;
  last_reset: string | null;
  next_reset: string | null;
}

const DEFAULT: AppInfo = { demo_mode: false, reset_hours: null, last_reset: null, next_reset: null };
const AppInfoContext = createContext<AppInfo>(DEFAULT);

/** Información pública del servidor (modo demo). El backend bloquea igual; esto solo ajusta la UI. */
export function AppInfoProvider({ children }: { children: ReactNode }) {
  const [info, setInfo] = useState<AppInfo>(DEFAULT);
  useEffect(() => {
    api.get<AppInfo>("/api/app-info").then(setInfo).catch(() => {});
  }, []);
  return <AppInfoContext.Provider value={info}>{children}</AppInfoContext.Provider>;
}

export const useAppInfo = () => useContext(AppInfoContext);
