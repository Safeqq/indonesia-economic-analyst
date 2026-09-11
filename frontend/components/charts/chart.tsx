"use client";

import * as echarts from "echarts";
import { useEffect, useRef } from "react";
import type { EChartsOption } from "echarts";

export function Chart({
  option,
  label,
  height = 360,
}: {
  option: EChartsOption;
  label: string;
  height?: number;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const chart = echarts.init(containerRef.current, undefined, { renderer: "svg" });
    chartRef.current = chart;
    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(containerRef.current);

    return () => {
      observer.disconnect();
      chart.dispose();
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    chartRef.current?.setOption(option, { notMerge: true });
  }, [option]);

  return (
    <div
      ref={containerRef}
      className="chart-canvas"
      style={{ height }}
      role="img"
      aria-label={label}
    />
  );
}

