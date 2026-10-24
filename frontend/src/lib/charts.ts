import type { EChartsOption } from "echarts";
import { axisStyle, baseOption, type ChartColors } from "./chartTheme";

/** Barras verticales simples (una serie). colors opcional por barra (p. ej. sobrecarga en rojo). */
export function barOption(c: ChartColors, opts: {
  categories: string[];
  values: number[];
  name: string;
  format: (v: number) => string;
  colors?: string[];
  refLine?: { value: number; label: string };
  labels?: boolean;
  rotate?: number;
  horizontal?: boolean;
}): EChartsOption {
  const cat = { type: "category" as const, data: opts.categories, ...axisStyle(c),
    axisLabel: { ...axisStyle(c).axisLabel, rotate: opts.rotate ?? 0, interval: 0, width: 110, overflow: "truncate" as const } };
  const val = { type: "value" as const, ...axisStyle(c), axisLabel: { ...axisStyle(c).axisLabel, formatter: (v: number) => opts.format(v) } };
  return {
    ...baseOption(c),
    xAxis: opts.horizontal ? val : cat,
    yAxis: opts.horizontal ? { ...cat, inverse: true } : val,
    series: [{
      type: "bar",
      name: opts.name,
      barMaxWidth: 46,
      data: opts.values.map((v, i) => ({ value: v, itemStyle: { color: opts.colors?.[i] ?? c.series[0], borderRadius: opts.horizontal ? [0, 4, 4, 0] : [4, 4, 0, 0] } })),
      label: opts.labels ? { show: true, position: opts.horizontal ? "right" : "top", color: c.text, fontSize: 11, formatter: (p: { value: unknown }) => opts.format(Number(p.value)) } : undefined,
      emphasis: { itemStyle: { shadowBlur: 12, shadowColor: "rgba(0,0,0,.18)" } },
      markLine: opts.refLine ? { symbol: "none", silent: true, lineStyle: { color: c.ref, type: "dashed" }, label: { formatter: opts.refLine.label, color: c.muted, position: "insideEndTop" }, data: [{ yAxis: opts.horizontal ? undefined : opts.refLine.value, xAxis: opts.horizontal ? opts.refLine.value : undefined }] } : undefined,
    }],
    tooltip: { ...baseOption(c).tooltip, formatter: (p: unknown) => { const q = p as { name: string; value: number }; return `<b>${q.name}</b><br/>${opts.name}: ${opts.format(q.value)}`; } },
  };
}

/** Línea de tendencia con meta opcional. */
export function trendOption(c: ChartColors, opts: {
  categories: string[];
  values: (number | null)[];
  name: string;
  format: (v: number) => string;
  goal?: { value: number; label: string };
  area?: boolean;
}): EChartsOption {
  return {
    ...baseOption(c),
    tooltip: { ...baseOption(c).tooltip, trigger: "axis", valueFormatter: (v: unknown) => (v == null ? "—" : opts.format(Number(v))) },
    xAxis: { type: "category", data: opts.categories, boundaryGap: false, ...axisStyle(c) },
    yAxis: { type: "value", scale: true, ...axisStyle(c), axisLabel: { ...axisStyle(c).axisLabel, formatter: (v: number) => opts.format(v) } },
    series: [{
      type: "line", name: opts.name, data: opts.values, smooth: true, symbolSize: 8, connectNulls: true,
      lineStyle: { width: 2.5, color: c.series[0] }, itemStyle: { color: c.series[0] },
      areaStyle: opts.area ? { color: { type: "linear", x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: `${c.series[0]}55` }, { offset: 1, color: `${c.series[0]}05` }] } } : undefined,
      markLine: opts.goal ? { symbol: "none", silent: true, lineStyle: { color: c.series[1], type: "dashed", width: 1.5 }, label: { formatter: opts.goal.label, color: c.muted, position: "insideEndTop" }, data: [{ yAxis: opts.goal.value }] } : undefined,
    }],
  };
}

/** Pareto: barras = % de cada categoría, línea = % acumulado; ambos en el mismo eje 0-100 %. */
export function paretoOption(c: ChartColors, rows: { name: string; pct: number; cum: number; classA: boolean; value: string }[]): EChartsOption {
  return {
    ...baseOption(c),
    legend: { ...baseOption(c).legend, data: ["% del total", "% acumulado"] },
    tooltip: {
      ...baseOption(c).tooltip, trigger: "axis",
      formatter: (ps: unknown) => {
        const arr = ps as { dataIndex: number }[];
        const r = rows[arr[0].dataIndex];
        return `<b>${r.name}</b><br/>${r.value}<br/>% del total: ${(r.pct * 100).toFixed(1)} %<br/>Acumulado: ${(r.cum * 100).toFixed(1)} %<br/><i>Clic para ver detalle</i>`;
      },
    },
    grid: { ...baseOption(c).grid, bottom: 4 },
    xAxis: { type: "category", data: rows.map((r) => r.name), ...axisStyle(c), axisLabel: { ...axisStyle(c).axisLabel, rotate: 40, interval: 0, width: 120, overflow: "truncate" } },
    yAxis: { type: "value", max: 1, ...axisStyle(c), axisLabel: { ...axisStyle(c).axisLabel, formatter: (v: number) => `${Math.round(v * 100)} %` } },
    series: [
      { type: "bar", name: "% del total", barMaxWidth: 34,
        data: rows.map((r) => ({ value: r.pct, itemStyle: { color: r.classA ? c.series[0] : c.light, borderRadius: [4, 4, 0, 0] } })),
        emphasis: { itemStyle: { color: c.series[2] } } },
      { type: "line", name: "% acumulado", data: rows.map((r) => r.cum), symbolSize: 7, lineStyle: { width: 2, color: c.series[1] }, itemStyle: { color: c.series[1] },
        markLine: { symbol: "none", silent: true, lineStyle: { color: c.ref, type: "dashed" }, label: { formatter: "80 %", color: c.muted }, data: [{ yAxis: 0.8 }] } },
    ],
  };
}

/** Gráfica de control: puntos, LC, LSC, LIC; señales anormales marcadas en rojo. */
export function controlOption(c: ChartColors, opts: {
  values: number[];
  signals: boolean[];
  labels: string[];
  limits: { lc: number; lsc: number; lic: number };
  name: string;
  unit?: string;
}): EChartsOption {
  const unit = opts.unit ?? " h";
  const ml = (v: number, label: string, color: string, type: "solid" | "dashed") =>
    ({ yAxis: v, lineStyle: { color, type, width: 1.5 }, label: { formatter: `${label} ${v.toFixed(2)}${unit}`, color: c.muted, position: "insideEndTop" as const } });
  return {
    ...baseOption(c),
    tooltip: { ...baseOption(c).tooltip, trigger: "axis", formatter: (ps: unknown) => {
      const i = (ps as { dataIndex: number }[])[0].dataIndex;
      return `${opts.labels[i]}<br/><b>${opts.values[i].toFixed(2)}${unit}</b>${opts.signals[i] ? '<br/><span style="color:' + c.bad + '">⚠ señal anormal</span>' : ""}`;
    } },
    xAxis: { type: "category", data: opts.values.map((_, i) => String(i + 1)), ...axisStyle(c), name: "Muestra", nameLocation: "middle", nameGap: 26 },
    yAxis: { type: "value", scale: true, ...axisStyle(c) },
    series: [{
      type: "line", name: opts.name, data: opts.values.map((v, i) => ({ value: v, symbol: opts.signals[i] ? "diamond" : "circle", symbolSize: opts.signals[i] ? 13 : 7, itemStyle: { color: opts.signals[i] ? c.bad : c.series[0] } })),
      lineStyle: { color: c.series[0], width: 2 },
      markLine: { symbol: "none", silent: true, data: [ml(opts.limits.lsc, "LSC", c.bad, "dashed"), ml(opts.limits.lc, "LC", c.ref, "solid"), ml(opts.limits.lic, "LIC", c.bad, "dashed")] },
    }],
  };
}

export interface GanttDay { label: string; start_h: number; end_h: number; start_clock: number }
export interface GanttBar {
  resource: string; folio: string; start: number; end: number; late: boolean; bay: string;
  priority: number; inicio: string; fin: string; customer: string;
}

/**
 * Gantt por días: eje X en horas laborables (sin noches ni domingos), una franja por día
 * con su nombre arriba y horas de reloj en el eje. Barras rojas = tarde. `selected` resalta una orden.
 */
export function ganttDaysOption(c: ChartColors, bars: GanttBar[], resources: string[], days: GanttDay[],
  selected: string | null): EChartsOption {
  const max = days.length ? days[days.length - 1].end_h : 8;
  const clockAt = (x: number) => {
    const d = days.find((s) => x >= s.start_h - 1e-6 && x <= s.end_h + 1e-6) ?? days[days.length - 1];
    if (!d) return "";
    const h = d.start_clock + (x - d.start_h);
    const hh = Math.floor(h + 1e-6);
    const mm = Math.round((h - hh) * 60);
    return `${hh}:${String(mm).padStart(2, "0")}`;
  };
  const hourTicks = days.flatMap((d) => {
    const ticks: number[] = [];
    const len = d.end_h - d.start_h;
    for (let h = Math.ceil(d.start_clock - 1e-6); h <= d.start_clock + len + 1e-6; h++) {
      if (h % 2 === 1 || h === Math.ceil(d.start_clock - 1e-6)) ticks.push(d.start_h + (h - d.start_clock));
    }
    return ticks;
  });
  const fmt = (iso: string) => new Date(iso).toLocaleString("es-MX", { weekday: "short", day: "2-digit", hour: "2-digit", minute: "2-digit" });
  return {
    ...baseOption(c),
    tooltip: { ...baseOption(c).tooltip, formatter: (p: unknown) => {
      const d = (p as { data?: { raw?: GanttBar } }).data?.raw;
      if (!d) return "";
      return `<b>#${d.priority} · ${d.folio}</b><br/>${d.customer} · ${d.bay}<br/>${fmt(d.inicio)} → ${fmt(d.fin)}<br/>`
        + (d.late ? `<span style="color:${c.bad}">⚠ Sale tarde</span>` : "A tiempo");
    } },
    grid: { left: 8, right: 44, top: 40, bottom: 44, containLabel: true },
    dataZoom: [
      { type: "inside", xAxisIndex: 0, filterMode: "weakFilter", startValue: 0, endValue: Math.min(max, 40) },
      { type: "slider", xAxisIndex: 0, height: 16, bottom: 6, filterMode: "weakFilter", startValue: 0, endValue: Math.min(max, 40),
        labelFormatter: (v: number) => days.find((d) => v >= d.start_h && v <= d.end_h)?.label ?? "" },
    ],
    xAxis: {
      type: "value", min: 0, max, ...axisStyle(c), splitLine: { show: false },
      // Marcas en horas exactas de reloj de cada día (9:00, 11:00, …), aunque hoy empiece a media jornada.
      axisTick: { show: true, customValues: hourTicks } as never,
      axisLabel: { ...axisStyle(c).axisLabel, customValues: hourTicks, formatter: (v: number) => clockAt(v) } as never,
    },
    yAxis: { type: "category", data: resources, inverse: true, ...axisStyle(c),
      axisLabel: { ...axisStyle(c).axisLabel, width: 130, overflow: "truncate" } },
    series: [
      {
        type: "custom",
        name: "Órdenes",
        renderItem: ((params: unknown, api: unknown) => {
          const a = api as { value: (i: number) => number; coord: (v: [number, number]) => [number, number]; size: (v: [number, number]) => [number, number] };
          const p = params as { dataIndex: number; coordSys: { x: number; y: number; width: number; height: number } };
          const bar = bars[p.dataIndex];
          const cat = a.value(0);
          const start = a.coord([a.value(1), cat]);
          const end = a.coord([a.value(2), cat]);
          const h = a.size([0, 1])[1] * 0.6;
          const x = Math.max(start[0], p.coordSys.x);
          const w = Math.min(end[0], p.coordSys.x + p.coordSys.width) - x;
          if (w <= 0) return null;
          const dim = selected !== null && selected !== bar.folio;
          const isSel = selected === bar.folio;
          const rect = {
            type: "rect", shape: { x, y: start[1] - h / 2, width: w, height: h, r: 5 },
            style: { fill: bar.late ? c.bad : c.series[0], opacity: dim ? 0.35 : 1, stroke: isSel ? c.series[1] : c.surface, lineWidth: isSel ? 3 : 1.5 },
          };
          const label = w > 34 ? {
            type: "text", style: { text: w > 90 ? `#${bar.priority} ${bar.folio}` : `#${bar.priority}`, x: x + 6, y: start[1],
              verticalAlign: "middle", fill: "#ffffff", font: "600 11px system-ui", opacity: dim ? 0.6 : 1 },
          } : null;
          return { type: "group", children: label ? [rect, label] : [rect] };
        }) as never,
        encode: { x: [1, 2], y: 0 },
        // "sel" en los datos (no solo en renderItem) para que el cambio de selección redibuje la gráfica.
        data: bars.map((b) => ({ value: [resources.indexOf(b.resource), b.start, b.end], raw: b, sel: b.folio === selected })),
        markArea: {
          silent: true,
          data: days.map((d, i) => [
            { xAxis: d.start_h, name: d.label, itemStyle: { color: i % 2 ? "rgba(124,156,201,0.07)" : "rgba(201,162,77,0.08)" } },
            { xAxis: d.end_h },
          ]) as never,
          label: { show: true, position: "top", color: c.text, fontWeight: "bold", fontSize: 12 },
        },
        markLine: {
          symbol: "none", silent: true, label: { show: false },
          lineStyle: { color: c.border, type: "solid", width: 1 },
          data: days.slice(1).map((d) => ({ xAxis: d.start_h })),
        },
      },
    ],
  };
}
