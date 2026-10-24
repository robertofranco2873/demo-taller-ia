import type { InputHTMLAttributes, ReactNode, SelectHTMLAttributes, TextareaHTMLAttributes } from "react";
import { useId } from "react";

export function Field({ label, hint, ...props }: { label: string; hint?: ReactNode } & InputHTMLAttributes<HTMLInputElement>) {
  const id = useId();
  return (
    <div>
      <label htmlFor={id} className="field-label">{label}</label>
      <input id={id} className="field" {...props} />
      {hint && <p className="mt-1 text-xs text-muted">{hint}</p>}
    </div>
  );
}

export function SelectField({ label, children, ...props }: { label: string; children: ReactNode } & SelectHTMLAttributes<HTMLSelectElement>) {
  const id = useId();
  return (
    <div>
      <label htmlFor={id} className="field-label">{label}</label>
      <select id={id} className="field cursor-pointer" {...props}>{children}</select>
    </div>
  );
}

export function TextArea({ label, ...props }: { label: string } & TextareaHTMLAttributes<HTMLTextAreaElement>) {
  const id = useId();
  return (
    <div>
      <label htmlFor={id} className="field-label">{label}</label>
      <textarea id={id} className="field min-h-24 resize-y" {...props} />
    </div>
  );
}

/** Rango de fechas con atajos (30 / 90 días / todo). */
export function DateRange({ start, end, min, max, onChange }: {
  start: string;
  end: string;
  min?: string;
  max?: string;
  onChange: (start: string, end: string) => void;
}) {
  const shift = (days: number) => {
    const d = new Date(`${max ?? end}T12:00:00`);
    d.setDate(d.getDate() - days);
    const iso = d.toISOString().slice(0, 10);
    onChange(min && iso < min ? min : iso, max ?? end);
  };
  return (
    <div className="flex flex-wrap items-end gap-2">
      <div className="w-36">
        <label className="field-label" htmlFor="dr-start">Desde</label>
        <input id="dr-start" type="date" className="field" value={start} min={min} max={end} onChange={(e) => onChange(e.target.value, end)} />
      </div>
      <div className="w-36">
        <label className="field-label" htmlFor="dr-end">Hasta</label>
        <input id="dr-end" type="date" className="field" value={end} min={start} max={max} onChange={(e) => onChange(start, e.target.value)} />
      </div>
      <div className="flex gap-1">
        {[["30 d", 30], ["90 d", 90]].map(([l, d]) => (
          <button key={l} type="button" onClick={() => shift(d as number)} className="h-10 cursor-pointer rounded-md border border-border px-3 text-xs font-medium text-secondary hover:border-accent hover:text-accent">{l}</button>
        ))}
        {min && max && (
          <button type="button" onClick={() => onChange(min, max)} className="h-10 cursor-pointer rounded-md border border-border px-3 text-xs font-medium text-secondary hover:border-accent hover:text-accent">Todo</button>
        )}
      </div>
    </div>
  );
}
