import { useId } from "react";

/** Silueta del engrane de 8 dientes (viewBox 64×64), compartida con el favicon y el loader. */
export const GEAR_PATH =
  "M51.86 23.77 L53.05 27.63 L58.74 28.27 L58.74 35.73 L53.05 36.37 L51.86 40.23 L49.97 43.80 L53.55 48.27 " +
  "L48.27 53.55 L43.80 49.97 L40.23 51.86 L36.37 53.05 L35.73 58.74 L28.27 58.74 L27.63 53.05 L23.77 51.86 " +
  "L20.20 49.97 L15.73 53.55 L10.45 48.27 L14.03 43.80 L12.14 40.23 L10.95 36.37 L5.26 35.73 L5.26 28.27 " +
  "L10.95 27.63 L12.14 23.77 L14.03 20.20 L10.45 15.73 L15.73 10.45 L20.20 14.03 L23.77 12.14 L27.63 10.95 " +
  "L28.27 5.26 L35.73 5.26 L36.37 10.95 L40.23 12.14 L43.80 14.03 L48.27 10.45 L53.55 15.73 L49.97 20.20 Z";

export function LogoIcon({ size = 36, title = "AutoServicio Demo" }: { size?: number; title?: string }) {
  const id = useId().replace(/:/g, "");
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" role="img" aria-label={title}>
      <defs>
        <linearGradient id={`g-${id}`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#8f7ad6" />
          <stop offset="1" stopColor="#4a78c2" />
        </linearGradient>
        <linearGradient id={`w-${id}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#f2d58b" />
          <stop offset="1" stopColor="#c9962b" />
        </linearGradient>
        <mask id={`m-${id}`}>
          <rect width="64" height="64" fill="white" />
          <rect x="28.6" y="3" width="6.8" height="11" rx="1.5" fill="black" />
          <circle cx="32" cy="53" r="1.9" fill="black" />
        </mask>
      </defs>
      <path d={`${GEAR_PATH} M32 21 a11 11 0 1 0 0.01 0 Z`} fill={`url(#g-${id})`} fillRule="evenodd" />
      <g transform="rotate(45 32 32)" mask={`url(#m-${id})`}>
        <circle cx="32" cy="14.5" r="9" fill={`url(#w-${id})`} />
        <rect x="28.4" y="18" width="7.2" height="37" rx="3.6" fill={`url(#w-${id})`} />
        <circle cx="32" cy="53" r="4.6" fill={`url(#w-${id})`} />
      </g>
      <circle cx="32" cy="32" r="3.2" fill="#fbf6e9" opacity="0.9" />
    </svg>
  );
}

export function Logo({ size = 36, compact = false }: { size?: number; compact?: boolean }) {
  return (
    <span className="inline-flex items-center gap-2.5 select-none">
      <LogoIcon size={size} />
      {!compact && (
        <span className="leading-tight">
          <span className="block font-bold tracking-tight text-text" style={{ fontSize: size * 0.46 }}>
            AutoServicio <span className="text-gold">Demo</span>
          </span>
          <span className="block text-muted" style={{ fontSize: Math.max(10, size * 0.27) }}>
            Taller · datos ficticios
          </span>
        </span>
      )}
    </span>
  );
}
