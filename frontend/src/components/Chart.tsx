import ReactEChartsCore from "echarts-for-react/lib/core";
import type { EChartsOption } from "echarts";
import { echarts } from "../lib/chartTheme";
import { SkeletonChart } from "./Skeleton";

export interface ChartClick {
  name: string;
  dataIndex: number;
  seriesName?: string;
  value?: unknown;
  data?: unknown;
}

/** Gráfica ECharts con skeleton de carga y evento de clic. */
export function Chart({ option, height = 300, loading, onClick, ariaLabel }: {
  option: EChartsOption;
  height?: number;
  loading?: boolean;
  onClick?: (p: ChartClick) => void;
  ariaLabel: string;
}) {
  if (loading) return <SkeletonChart height={height} />;
  return (
    <div role="img" aria-label={ariaLabel} className={onClick ? "cursor-pointer" : undefined}>
      <ReactEChartsCore
        echarts={echarts}
        option={option}
        notMerge
        lazyUpdate
        style={{ height, width: "100%" }}
        onEvents={onClick ? { click: (p: ChartClick) => onClick(p) } : undefined}
      />
    </div>
  );
}
