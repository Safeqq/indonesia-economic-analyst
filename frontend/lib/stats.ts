import type { NamedSeries, SeriesObservation } from "@/lib/types";

export interface AlignedRow {
  date: string;
  values: Record<string, number>;
}

export interface SeriesSummary {
  latest: SeriesObservation;
  previous: SeriesObservation | null;
  absoluteChange: number | null;
  percentChange: number | null;
  minimum: number;
  maximum: number;
}

export function summarizeSeries(items: SeriesObservation[]): SeriesSummary | null {
  if (items.length === 0) return null;
  const sorted = [...items].sort((a, b) =>
    a.observation_date.localeCompare(b.observation_date),
  );
  const latest = sorted.at(-1)!;
  const previous = sorted.at(-2) ?? null;
  const absoluteChange = previous ? latest.value - previous.value : null;
  const percentChange =
    previous && previous.value !== 0
      ? ((latest.value - previous.value) / Math.abs(previous.value)) * 100
      : null;

  return {
    latest,
    previous,
    absoluteChange,
    percentChange,
    minimum: Math.min(...sorted.map((item) => item.value)),
    maximum: Math.max(...sorted.map((item) => item.value)),
  };
}

export function alignSeries(series: NamedSeries[]): AlignedRow[] {
  if (series.length === 0) return [];
  const rows = new Map<string, Record<string, number>>();

  series.forEach((currentSeries) => {
    currentSeries.items.forEach((item) => {
      const row = rows.get(item.observation_date) ?? {};
      row[currentSeries.code] = item.value;
      rows.set(item.observation_date, row);
    });
  });

  return [...rows.entries()]
    .filter(([, values]) => series.every(({ code }) => values[code] !== undefined))
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([date, values]) => ({ date, values }));
}

export function pearsonCorrelation(left: number[], right: number[]): number | null {
  if (left.length !== right.length || left.length < 2) return null;
  const leftMean = left.reduce((sum, value) => sum + value, 0) / left.length;
  const rightMean = right.reduce((sum, value) => sum + value, 0) / right.length;

  let covariance = 0;
  let leftVariance = 0;
  let rightVariance = 0;
  left.forEach((value, index) => {
    const leftDifference = value - leftMean;
    const rightDifference = right[index] - rightMean;
    covariance += leftDifference * rightDifference;
    leftVariance += leftDifference ** 2;
    rightVariance += rightDifference ** 2;
  });

  const denominator = Math.sqrt(leftVariance * rightVariance);
  return denominator === 0 ? null : covariance / denominator;
}

export function correlationMatrix(
  series: NamedSeries[],
  rows: AlignedRow[],
): Array<[number, number, number | null]> {
  return series.flatMap((left, leftIndex) =>
    series.map((right, rightIndex) => [
      leftIndex,
      rightIndex,
      pearsonCorrelation(
        rows.map((row) => row.values[left.code]),
        rows.map((row) => row.values[right.code]),
      ),
    ] as [number, number, number | null]),
  );
}

