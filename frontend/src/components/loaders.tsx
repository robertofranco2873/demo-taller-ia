import { GEAR_PATH } from "./Logo";

/* Animaciones de carga temáticas (CSS; respetan prefers-reduced-motion). */

const svgProps = { width: 96, height: 96, viewBox: "0 0 120 120", "aria-hidden": true } as const;

export function GearLoader() {
  return (
    <svg {...svgProps}>
      <g className="ld-spin" style={{ transformOrigin: "48px 52px" }}>
        <path d={`${GEAR_PATH} M32 22 a10 10 0 1 0 0.01 0 Z`} transform="translate(16 20)" fill="var(--purple-500)" fillRule="evenodd" />
      </g>
      <g className="ld-spin-rev" style={{ transformOrigin: "88px 30px" }}>
        <path d={`${GEAR_PATH} M32 22 a10 10 0 1 0 0.01 0 Z`} transform="translate(68 10) scale(0.62)" fill="var(--gold-500)" fillRule="evenodd" />
      </g>
      <g className="ld-spin-rev" style={{ transformOrigin: "86px 88px" }}>
        <path d={`${GEAR_PATH} M32 22 a10 10 0 1 0 0.01 0 Z`} transform="translate(66 68) scale(0.62)" fill="var(--blue-500)" fillRule="evenodd" />
      </g>
    </svg>
  );
}

export function WrenchLoader() {
  return (
    <svg {...svgProps}>
      <rect x="20" y="84" width="80" height="10" rx="5" fill="var(--blue-100)" />
      <g className="ld-tighten" style={{ transformOrigin: "60px 60px" }}>
        <polygon points="60,47 71,53.5 71,66.5 60,73 49,66.5 49,53.5" fill="var(--blue-500)" />
        <circle cx="60" cy="60" r="4.5" fill="var(--blue-100)" />
        <g>
          <path d="M60 41 a19 19 0 1 1 -0.01 0 Z M60 49 a11 11 0 1 0 0.01 0 Z" fill="var(--gold-500)" fillRule="evenodd" />
          <rect x="74" y="54" width="40" height="12" rx="6" fill="var(--gold-500)" />
        </g>
      </g>
    </svg>
  );
}

export function PistonLoader() {
  return (
    <svg {...svgProps}>
      <rect x="36" y="10" width="48" height="62" rx="6" fill="none" stroke="var(--purple-300)" strokeWidth="4" />
      <g className="ld-piston">
        <rect x="40" y="22" width="40" height="22" rx="4" fill="var(--purple-500)" />
        <rect x="40" y="27" width="40" height="3" fill="var(--purple-300)" />
        <rect x="40" y="33" width="40" height="3" fill="var(--purple-300)" />
        <rect x="56" y="44" width="8" height="40" rx="4" fill="var(--blue-500)" />
      </g>
      <g className="ld-spin" style={{ transformOrigin: "60px 96px" }}>
        <circle cx="60" cy="96" r="14" fill="var(--gold-100)" stroke="var(--gold-500)" strokeWidth="4" />
        <circle cx="60" cy="86" r="4" fill="var(--gold-500)" />
      </g>
    </svg>
  );
}

export function LiftLoader() {
  return (
    <svg {...svgProps}>
      <rect x="14" y="20" width="8" height="84" rx="3" fill="var(--blue-300)" />
      <rect x="98" y="20" width="8" height="84" rx="3" fill="var(--blue-300)" />
      <rect x="8" y="102" width="104" height="6" rx="3" fill="var(--blue-500)" />
      <g className="ld-lift">
        <rect x="18" y="74" width="84" height="6" rx="3" fill="var(--purple-500)" />
        <path d="M26 70 L34 56 Q38 50 46 50 L74 50 Q82 50 86 56 L94 64 Q97 66 97 70 Z" fill="var(--gold-500)" />
        <rect x="44" y="55" width="13" height="9" rx="2" fill="var(--gold-100)" />
        <rect x="61" y="55" width="15" height="9" rx="2" fill="var(--gold-100)" />
        <circle cx="40" cy="71" r="6" fill="var(--purple-700)" />
        <circle cx="82" cy="71" r="6" fill="var(--purple-700)" />
      </g>
    </svg>
  );
}

const LOADERS = { gear: GearLoader, wrench: WrenchLoader, piston: PistonLoader, lift: LiftLoader };
export type LoaderKind = keyof typeof LOADERS;

export function ThemedLoader({ kind = "gear", label = "Cargando…" }: { kind?: LoaderKind; label?: string }) {
  const Comp = LOADERS[kind];
  return (
    <div role="status" aria-live="polite" className="flex flex-col items-center justify-center gap-3 py-10 text-muted">
      <Comp />
      <span className="text-sm">{label}</span>
    </div>
  );
}
