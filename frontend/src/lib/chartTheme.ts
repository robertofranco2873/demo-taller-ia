import { BarChart, CustomChart, LineChart, ScatterChart } from "echarts/charts";
import {
  DataZoomComponent, GridComponent, LegendComponent, MarkAreaComponent, MarkLineComponent, TooltipComponent,
} from "echarts/components";
import * as echarts from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { useMemo } from "react";
import { useTheme } from "./theme";

// Solo los módulos que usa la app (mucho más ligero que el paquete completo).
echarts.use([BarChart, LineChart, ScatterChart, CustomChart, GridComponent, TooltipComponent, LegendComponent,
  MarkLineComponent, MarkAreaComponent, DataZoomComponent, CanvasRenderer]);

export { echarts };

export interface ChartColors {
  series: string[];
  good: string;
  bad: string;
  ref: string;
  grid: string;
  text: string;
  muted: string;
  surface: string;
  border: string;
  light: string;
}

function readVar(name: string) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

/** Colores de gráficas leídos de los design tokens (cambian con el tema). */
export function useChartColors(): ChartColors {
  const { theme } = useTheme();
  return useMemo(() => {
    void theme;
    return {
      series: [readVar("--chart-1"), readVar("--chart-2"), readVar("--chart-3")],
      good: readVar("--chart-good"),
      bad: readVar("--chart-bad"),
      ref: readVar("--chart-ref"),
      grid: readVar("--chart-grid"),
      text: readVar("--text"),
      muted: readVar("--text-muted"),
      surface: readVar("--surface-solid"),
      border: readVar("--border-strong"),
      light: readVar("--chart-light-1"),
    };
  }, [theme]);
}

/** Opciones base comunes: un solo eje Y, rejilla tenue, tooltip con estilo de tarjeta. */
export function baseOption(c: ChartColors) {
  return {
    color: c.series,
    textStyle: { fontFamily: "system-ui, -apple-system, Segoe UI, sans-serif", color: c.muted },
    animationDuration: 700,
    animationEasing: "cubicOut",
    grid: { left: 8, right: 16, top: 36, bottom: 8, containLabel: true },
    tooltip: {
      trigger: "item",
      backgroundColor: c.surface,
      borderColor: c.border,
      borderWidth: 1,
      textStyle: { color: c.text, fontSize: 12 },
      extraCssText: "border-radius:12px;box-shadow:0 8px 24px rgba(0,0,0,.12);",
    },
    legend: { top: 0, right: 0, textStyle: { color: c.muted }, itemWidth: 12, itemHeight: 8, icon: "roundRect" },
  };
}

export function axisStyle(c: ChartColors) {
  return {
    axisLine: { lineStyle: { color: c.border } },
    axisTick: { show: false },
    axisLabel: { color: c.muted, fontSize: 11 },
    splitLine: { lineStyle: { color: c.grid } },
  };
}
