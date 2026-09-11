import { describe, expect, it } from "vitest";

import { alignSeries, pearsonCorrelation, summarizeSeries } from "@/lib/stats";
import type { NamedSeries, SeriesObservation } from "@/lib/types";

function observation(date: string, value: number): SeriesObservation {
  return {
    observation_date: date,
    value,
    source_code: "official_source",
    ingested_at: "2026-09-11T01:00:00Z",
  };
}

describe("summarizeSeries", () => {
  it("mengurutkan observasi sebelum menghitung nilai terbaru dan perubahan", () => {
    const summary = summarizeSeries([
      observation("2025-01-01", 120),
      observation("2024-01-01", 100),
      observation("2023-01-01", 90),
    ]);

    expect(summary?.latest.value).toBe(120);
    expect(summary?.previous?.value).toBe(100);
    expect(summary?.absoluteChange).toBe(20);
    expect(summary?.percentChange).toBe(20);
    expect(summary?.minimum).toBe(90);
    expect(summary?.maximum).toBe(120);
  });

  it("tidak membuat perubahan palsu jika hanya ada satu observasi", () => {
    const summary = summarizeSeries([observation("2025-01-01", 5)]);

    expect(summary?.previous).toBeNull();
    expect(summary?.absoluteChange).toBeNull();
    expect(summary?.percentChange).toBeNull();
  });
});

describe("alignment dan korelasi", () => {
  const series: NamedSeries[] = [
    {
      code: "A",
      name: "Seri A",
      unit: null,
      items: [observation("2022-01-01", 1), observation("2023-01-01", 2)],
    },
    {
      code: "B",
      name: "Seri B",
      unit: null,
      items: [observation("2021-01-01", 0), observation("2023-01-01", 4)],
    },
  ];

  it("hanya mempertahankan tanggal yang tersedia di seluruh seri", () => {
    expect(alignSeries(series)).toEqual([
      { date: "2023-01-01", values: { A: 2, B: 4 } },
    ]);
  });

  it("menghasilkan korelasi Pearson pada pasangan valid", () => {
    expect(pearsonCorrelation([1, 2, 3], [2, 4, 6])).toBeCloseTo(1);
    expect(pearsonCorrelation([1, 2, 3], [6, 4, 2])).toBeCloseTo(-1);
  });

  it("menolak pasangan pendek atau tanpa variasi", () => {
    expect(pearsonCorrelation([1], [2])).toBeNull();
    expect(pearsonCorrelation([1, 1], [2, 3])).toBeNull();
  });
});

