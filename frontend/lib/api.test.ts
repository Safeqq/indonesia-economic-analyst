import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, buildQuery, getIndicatorSeries } from "@/lib/api";

const reference = {
  indicator: {
    indicator_code: "TEST.CODE",
    indicator_name: "Test indicator",
    unit: "percent",
    frequency: "annual" as const,
  },
  region: {
    region_code: "IDN",
    region_name: "Indonesia",
    region_level: "country" as const,
    parent_region_code: null,
  },
};

afterEach(() => vi.unstubAllGlobals());

describe("API client", () => {
  it("mengabaikan query kosong dan meng-encode nilai", () => {
    expect(buildQuery({ region_code: "ID N", year: 2025, status: null })).toBe(
      "?region_code=ID+N&year=2025",
    );
  });

  it("menggabungkan seluruh halaman seri tanpa kehilangan metadata", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          ...reference,
          items: [{ observation_date: "2024-01-01", value: 1 }],
          pagination: { page: 1, page_size: 100, total_items: 2, total_pages: 2 },
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          ...reference,
          items: [{ observation_date: "2025-01-01", value: 2 }],
          pagination: { page: 2, page_size: 100, total_items: 2, total_pages: 2 },
        }),
      });
    vi.stubGlobal("fetch", fetchMock);

    const result = await getIndicatorSeries("TEST.CODE", "IDN", 2024, 2025);

    expect(result.items.map((item) => item.value)).toEqual([1, 2]);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock.mock.calls[1][0]).toContain("page=2");
  });

  it("meneruskan detail error API beserta status HTTP", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        json: async () => ({ detail: "Data belum tersedia" }),
      }),
    );

    await expect(getIndicatorSeries("TEST.CODE", "IDN")).rejects.toEqual(
      new ApiError("Data belum tersedia", 404),
    );
  });
});

