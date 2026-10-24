import ReactEChartsCore from "echarts-for-react/lib/core";
import type { EChartsOption, EChartsType } from "echarts";
import { useEffect, useRef } from "react";
import { echarts } from "../lib/chartTheme";
import { SkeletonChart } from "./Skeleton";

export interface ChartClick {
  dataIndex: number;
}

/**
 * Gráfica ECharts con skeleton de carga. Con onClick, toda la columna de la categoría es clicable
 * (no solo la barra), para que las barras pequeñas también se puedan seleccionar.
 */
export function Chart({ option, height = 300, loading, onClick, ariaLabel }: {
  option: EChartsOption;
  height?: number;
  loading?: boolean;
  onClick?: (p: ChartClick) => void;
  ariaLabel: string;
}) {
  const ref = useRef<ReactEChartsCore>(null);
  const handler = useRef(onClick);
  // Reutiliza el mismo objeto de opciones si su contenido no cambió: evita que un re-render
  // del padre reemplace las series mientras el mouse está encima (error getRawIndex de ECharts).
  const stable = useRef<{ sig: string; option: EChartsOption } | null>(null);
  const sig = JSON.stringify(option, (_, v) => (typeof v === "function" ? undefined : v));
  if (!stable.current || stable.current.sig !== sig) stable.current = { sig, option };
  const stableOption = stable.current.option;
  useEffect(() => {
    handler.current = onClick;
  });
  const clickable = !!onClick;

  useEffect(() => {
    if (!clickable || loading) return;
    const chart = ref.current?.getEchartsInstance() as EChartsType | undefined;
    if (!chart) return;
    const zr = chart.getZr();
    const onZrClick = (e: { offsetX: number; offsetY: number }) => {
      const point = [e.offsetX, e.offsetY];
      if (!chart.containPixel("grid", point)) return;
      const [index] = chart.convertFromPixel({ seriesIndex: 0 }, point) as number[];
      // Diferido: si el clic provoca un re-render con opciones nuevas, ECharts termina antes su evento.
      if (Number.isFinite(index) && index >= 0) setTimeout(() => handler.current?.({ dataIndex: Math.round(index) }), 0);
    };
    const onMove = (e: { offsetX: number; offsetY: number }) => {
      zr.setCursorStyle(chart.containPixel("grid", [e.offsetX, e.offsetY]) ? "pointer" : "default");
    };
    zr.on("click", onZrClick);
    zr.on("mousemove", onMove);
    return () => {
      zr.off("click", onZrClick);
      zr.off("mousemove", onMove);
    };
  }, [clickable, loading]);

  if (loading) return <SkeletonChart height={height} />;
  return (
    <div role="img" aria-label={ariaLabel}>
      <ReactEChartsCore ref={ref} echarts={echarts} option={stableOption} notMerge lazyUpdate style={{ height, width: "100%" }} />
    </div>
  );
}
