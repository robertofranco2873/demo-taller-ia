import { Lock } from "lucide-react";
import type { ReactNode } from "react";
import { useAppInfo } from "../lib/appInfo";
import { Tooltip } from "./ui";

export const DEMO_LOCK_TEXT = "Desactivado en la demo pública";

/**
 * En modo demo muestra el control deshabilitado con un globo explicativo.
 * Los navegadores no disparan eventos de mouse en botones deshabilitados, así que el globo
 * va en un contenedor enfocable y el control no recibe clics (el backend también lo bloquea).
 */
export function DemoLock({ children, locked: lockedProp }: { children: ReactNode; locked?: boolean }) {
  const { demo_mode } = useAppInfo();
  const locked = lockedProp ?? demo_mode;
  if (!locked) return <>{children}</>;
  return (
    <Tooltip content={<span className="inline-flex items-center gap-1"><Lock size={12} aria-hidden />{DEMO_LOCK_TEXT}. Los datos se restablecen cada 24 h.</span>}>
      <span tabIndex={0} aria-label={DEMO_LOCK_TEXT} aria-disabled="true"
        className="inline-flex cursor-not-allowed rounded-md opacity-55 [&>*]:pointer-events-none">
        {children}
      </span>
    </Tooltip>
  );
}
