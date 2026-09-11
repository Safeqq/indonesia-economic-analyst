"use client";

import { useMemo } from "react";
import type { EChartsOption } from "echarts";

import { Chart } from "@/components/charts/chart";
import { formatDate, formatNumber, formatValue } from "@/lib/format";
import type { ForecastPoint } from "@/lib/types";

const palette = ["#18a999", "#5b8def", "#f4a261", "#9b7ede", "#e76f51"];

interface TimeSeriesDefinition {
  name: string;
  points: Array<{ date: string; value: number }>;
  color?: string;
  dashed?: boolean;
}

function baseGrid() {
  return { left: 16, right: 22, top: 42, bottom: 16, containLabel: true };
}

function axisLabelColor() {
  return { color: "#75878e", fontSize: 11 };
}

export function TimeSeriesChart({
  series,
  unit,
  label,
  height,
}: {
  series: TimeSeriesDefinition[];
  unit?: string | null;
  label: string;
  height?: number;
}) {
  const option = useMemo<EChartsOption>(() => {
    const dates = [...new Set(series.flatMap((item) => item.points.map((point) => point.date)))].sort();
    const valuesBySeries = series.map((item) =>
      new Map(item.points.map((point) => [point.date, point.value])),
    );

    return {
      animationDuration: 500,
      color: palette,
      grid: baseGrid(),
      legend: {
        top: 4,
        left: 4,
        textStyle: { color: "#53666d", fontSize: 11 },
      },
      tooltip: {
        trigger: "axis",
        backgroundColor: "rgba(8, 28, 36, .96)",
        borderWidth: 0,
        textStyle: { color: "#fff" },
        valueFormatter: (value) => formatValue(Number(value), unit),
      },
      xAxis: {
        type: "category",
        data: dates,
        boundaryGap: false,
        axisLine: { lineStyle: { color: "#dbe5e8" } },
        axisTick: { show: false },
        axisLabel: {
          ...axisLabelColor(),
          formatter: (value: string) => value.slice(0, 7),
          hideOverlap: true,
        },
      },
      yAxis: {
        type: "value",
        scale: true,
        splitLine: { lineStyle: { color: "#edf2f3" } },
        axisLabel: {
          ...axisLabelColor(),
          formatter: (value: number) => formatValue(value, unit, true),
        },
      },
      series: series.map((item, index) => ({
        name: item.name,
        type: "line",
        data: dates.map((date) => valuesBySeries[index].get(date) ?? null),
        showSymbol: dates.length < 40,
        symbolSize: 7,
        smooth: dates.length > 3 ? 0.18 : false,
        connectNulls: false,
        lineStyle: {
          width: 2.5,
          type: item.dashed ? "dashed" : "solid",
          color: item.color,
        },
        itemStyle: { color: item.color },
        areaStyle:
          index === 0 && series.length === 1
            ? { color: "rgba(24, 169, 153, .10)" }
            : undefined,
      })),
    };
  }, [series, unit]);

  return <Chart option={option} label={label} height={height} />;
}

export function ComparisonChart({
  items,
  unit,
  selectedCode,
  label,
}: {
  items: Array<{ code: string; name: string; value: number }>;
  unit?: string | null;
  selectedCode?: string;
  label: string;
}) {
  const option = useMemo<EChartsOption>(() => {
    const sorted = [...items].sort((left, right) => left.value - right.value);
    return {
      animationDuration: 500,
      grid: { left: 8, right: 24, top: 8, bottom: 12, containLabel: true },
      tooltip: {
        trigger: "axis",
        axisPointer: { type: "shadow" },
        backgroundColor: "rgba(8, 28, 36, .96)",
        borderWidth: 0,
        textStyle: { color: "#fff" },
        valueFormatter: (value) => formatValue(Number(value), unit),
      },
      xAxis: {
        type: "value",
        scale: true,
        splitLine: { lineStyle: { color: "#edf2f3" } },
        axisLabel: {
          ...axisLabelColor(),
          formatter: (value: number) => formatValue(value, unit, true),
        },
      },
      yAxis: {
        type: "category",
        data: sorted.map((item) => item.name),
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { ...axisLabelColor(), width: 130, overflow: "truncate" },
      },
      series: [
        {
          type: "bar",
          data: sorted.map((item) => ({
            value: item.value,
            itemStyle: {
              color: item.code === selectedCode ? "#f4a261" : "#18a999",
              borderRadius: [0, 6, 6, 0],
            },
          })),
          barMaxWidth: 22,
        },
      ],
    };
  }, [items, selectedCode, unit]);

  return <Chart option={option} label={label} height={Math.max(330, items.length * 34)} />;
}

export function ScatterChart({
  points,
  xName,
  yName,
  xUnit,
  yUnit,
}: {
  points: Array<{ x: number; y: number; date: string }>;
  xName: string;
  yName: string;
  xUnit?: string | null;
  yUnit?: string | null;
}) {
  const option = useMemo<EChartsOption>(() => ({
    animationDuration: 500,
    grid: baseGrid(),
    tooltip: {
      trigger: "item",
      backgroundColor: "rgba(8, 28, 36, .96)",
      borderWidth: 0,
      textStyle: { color: "#fff" },
      formatter: (raw: unknown) => {
        const params = raw as { value: [number, number, string] };
        return [
          `<strong>${formatDate(params.value[2])}</strong>`,
          `${xName}: ${formatValue(params.value[0], xUnit)}`,
          `${yName}: ${formatValue(params.value[1], yUnit)}`,
        ].join("<br/>");
      },
    },
    xAxis: {
      type: "value",
      name: xName,
      nameLocation: "middle",
      nameGap: 34,
      nameTextStyle: { color: "#53666d", fontSize: 11 },
      axisLabel: { ...axisLabelColor(), formatter: (value: number) => formatNumber(value) },
      splitLine: { lineStyle: { color: "#edf2f3" } },
      scale: true,
    },
    yAxis: {
      type: "value",
      name: yName,
      nameLocation: "middle",
      nameGap: 48,
      nameTextStyle: { color: "#53666d", fontSize: 11 },
      axisLabel: { ...axisLabelColor(), formatter: (value: number) => formatNumber(value) },
      splitLine: { lineStyle: { color: "#edf2f3" } },
      scale: true,
    },
    series: [
      {
        type: "scatter",
        data: points.map((point) => [point.x, point.y, point.date]),
        symbolSize: 11,
        itemStyle: {
          color: "#18a999",
          borderColor: "#ffffff",
          borderWidth: 2,
          shadowBlur: 8,
          shadowColor: "rgba(24, 169, 153, .25)",
        },
      },
    ],
  }), [points, xName, xUnit, yName, yUnit]);

  return <Chart option={option} label={`Scatter plot ${xName} dan ${yName}`} />;
}

export function CorrelationHeatmap({
  labels,
  values,
}: {
  labels: string[];
  values: Array<[number, number, number | null]>;
}) {
  const option = useMemo<EChartsOption>(() => ({
    animationDuration: 500,
    grid: { left: 16, right: 34, top: 16, bottom: 60, containLabel: true },
    tooltip: {
      position: "top",
      backgroundColor: "rgba(8, 28, 36, .96)",
      borderWidth: 0,
      textStyle: { color: "#fff" },
      formatter: (raw: unknown) => {
        const params = raw as { value: [number, number, number | null] };
        const [x, y, correlation] = params.value;
        return `${labels[y]} × ${labels[x]}<br/><strong>${
          correlation === null ? "N/A" : correlation.toFixed(3)
        }</strong>`;
      },
    },
    xAxis: {
      type: "category",
      data: labels,
      splitArea: { show: true },
      axisLabel: { ...axisLabelColor(), rotate: 24, width: 105, overflow: "truncate" },
      axisTick: { show: false },
    },
    yAxis: {
      type: "category",
      data: labels,
      splitArea: { show: true },
      axisLabel: { ...axisLabelColor(), width: 110, overflow: "truncate" },
      axisTick: { show: false },
    },
    visualMap: {
      min: -1,
      max: 1,
      calculable: false,
      orient: "horizontal",
      left: "center",
      bottom: 0,
      inRange: { color: ["#d86b61", "#f3f0df", "#159b8d"] },
      textStyle: { color: "#75878e" },
    },
    series: [
      {
        type: "heatmap",
        data: values.map(([x, y, value]) => [x, y, value]),
        label: {
          show: true,
          formatter: (raw: unknown) => {
            const params = raw as { value: [number, number, number | null] };
            return params.value[2] === null ? "—" : params.value[2].toFixed(2);
          },
          color: "#18333d",
          fontSize: 11,
        },
        emphasis: { itemStyle: { shadowBlur: 10, shadowColor: "rgba(0,0,0,.2)" } },
      },
    ],
  }), [labels, values]);

  return <Chart option={option} label="Matriks korelasi indikator" height={410} />;
}

export function ForecastChart({
  history,
  forecast,
  unit,
}: {
  history: Array<{ date: string; value: number }>;
  forecast: ForecastPoint[];
  unit?: string | null;
}) {
  const option = useMemo<EChartsOption>(() => {
    const dates = [
      ...new Set([
        ...history.map((point) => point.date),
        ...forecast.map((point) => point.forecast_date),
      ]),
    ].sort();
    const historyMap = new Map(history.map((point) => [point.date, point.value]));
    const forecastMap = new Map(forecast.map((point) => [point.forecast_date, point]));
    const bridge = history.at(-1);

    return {
      animationDuration: 500,
      grid: baseGrid(),
      legend: {
        top: 4,
        left: 4,
        data: ["Aktual", "Estimasi", "Interval kepercayaan"],
        textStyle: { color: "#53666d", fontSize: 11 },
      },
      tooltip: {
        trigger: "axis",
        backgroundColor: "rgba(8, 28, 36, .96)",
        borderWidth: 0,
        textStyle: { color: "#fff" },
        valueFormatter: (value) => formatValue(Number(value), unit),
      },
      xAxis: {
        type: "category",
        data: dates,
        boundaryGap: false,
        axisLine: { lineStyle: { color: "#dbe5e8" } },
        axisTick: { show: false },
        axisLabel: { ...axisLabelColor(), formatter: (value: string) => value.slice(0, 7), hideOverlap: true },
      },
      yAxis: {
        type: "value",
        scale: true,
        splitLine: { lineStyle: { color: "#edf2f3" } },
        axisLabel: { ...axisLabelColor(), formatter: (value: number) => formatValue(value, unit, true) },
      },
      series: [
        {
          name: "Aktual",
          type: "line",
          data: dates.map((date) => historyMap.get(date) ?? null),
          showSymbol: false,
          lineStyle: { width: 2.5, color: "#18a999" },
          itemStyle: { color: "#18a999" },
        },
        {
          name: "Batas bawah",
          type: "line",
          stack: "confidence",
          data: dates.map((date) => forecastMap.get(date)?.lower_bound ?? null),
          symbol: "none",
          lineStyle: { opacity: 0 },
          areaStyle: { opacity: 0 },
          tooltip: { show: false },
        },
        {
          name: "Interval kepercayaan",
          type: "line",
          stack: "confidence",
          data: dates.map((date) => {
            const point = forecastMap.get(date);
            return point ? point.upper_bound - point.lower_bound : null;
          }),
          symbol: "none",
          lineStyle: { opacity: 0 },
          areaStyle: { color: "rgba(244, 162, 97, .30)" },
          tooltip: { show: false },
        },
        {
          name: "Estimasi",
          type: "line",
          data: dates.map((date) => {
            if (bridge?.date === date) return bridge.value;
            return forecastMap.get(date)?.point_forecast ?? null;
          }),
          connectNulls: true,
          showSymbol: true,
          symbolSize: 7,
          lineStyle: { width: 2.5, color: "#f4a261", type: "dashed" },
          itemStyle: { color: "#f4a261" },
        },
      ],
    };
  }, [forecast, history, unit]);

  return <Chart option={option} label="Grafik aktual dan estimasi dengan interval kepercayaan" height={410} />;
}
