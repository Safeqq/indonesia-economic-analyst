import { expect, test, type Route } from "@playwright/test";

const updatedAt = "2026-09-10T05:00:00Z";
const pagination = { page: 1, page_size: 100, total_items: 3, total_pages: 1 };
const indicators = [
  {
    indicator_code: "NY.GDP.MKTP.KD.ZG",
    indicator_name: "GDP growth",
    unit: "percent",
    frequency: "annual",
    source_codes: ["world_bank"],
    observation_count: 26,
    region_count: 11,
    period_start: "2000-01-01",
    period_end: "2025-01-01",
  },
  {
    indicator_code: "FP.CPI.TOTL.ZG",
    indicator_name: "Inflation",
    unit: "percent",
    frequency: "annual",
    source_codes: ["world_bank"],
    observation_count: 26,
    region_count: 11,
    period_start: "2000-01-01",
    period_end: "2025-01-01",
  },
  {
    indicator_code: "SL.UEM.TOTL.ZS",
    indicator_name: "Unemployment",
    unit: "percent",
    frequency: "annual",
    source_codes: ["world_bank"],
    observation_count: 26,
    region_count: 11,
    period_start: "2000-01-01",
    period_end: "2025-01-01",
  },
];
const regions = [
  {
    region_code: "IDN",
    region_name: "Indonesia",
    region_level: "country",
    parent_region_code: null,
    indicator_count: 7,
    observation_count: 300,
    period_start: "2000-01-01",
    period_end: "2026-08-01",
  },
  {
    region_code: "3100",
    region_name: "DKI Jakarta",
    region_level: "province",
    parent_region_code: "IDN",
    indicator_count: 2,
    observation_count: 20,
    period_start: "2015-01-01",
    period_end: "2025-01-01",
  },
];

function seriesPayload(code: string) {
  const indicator = indicators.find((item) => item.indicator_code === code) ?? indicators[0];
  return {
    indicator,
    region: regions[0],
    items: [
      { observation_date: "2023-01-01", value: 5.05, source_code: "world_bank", ingested_at: updatedAt },
      { observation_date: "2024-01-01", value: 5.03, source_code: "world_bank", ingested_at: updatedAt },
      { observation_date: "2025-01-01", value: 5.11, source_code: "world_bank", ingested_at: updatedAt },
    ],
    pagination: { ...pagination, total_items: 3 },
  };
}

async function mockBackend(route: Route) {
  const url = new URL(route.request().url());
  const path = url.pathname.replace(/^\/backend/, "");
  let status = 200;
  let body: object;

  if (path === "/api/v1/indicators") {
    body = { items: indicators, pagination };
  } else if (path === "/api/v1/regions") {
    body = { items: regions, pagination: { ...pagination, total_items: 2 } };
  } else if (path === "/api/v1/overview") {
    body = {
      region: regions[0],
      national: {
        source_code: "world_bank",
        observation_date: "2025-01-01",
        observation_year: 2025,
        gdp_growth_percent: 5.11,
        inflation_percent: 1.9,
        unemployment_percent: 4.9,
        population: 285000000,
        gdp_per_capita_current_usd: 5000,
        indicator_coverage: 5,
        last_ingested_at: updatedAt,
      },
      monetary: null,
    };
  } else if (/^\/api\/v1\/indicators\/[^/]+\/series$/.test(path)) {
    body = seriesPayload(decodeURIComponent(path.split("/")[4]));
  } else if (/^\/api\/v1\/regions\/[^/]+\/overview$/.test(path)) {
    body = {
      region: regions[1],
      observation_year: 2025,
      items: [
        {
          ...indicators[0],
          source_code: "bps",
          observation_date: "2025-01-01",
          value: 5.2,
          ingested_at: updatedAt,
        },
      ],
      pagination: { ...pagination, total_items: 1 },
    };
  } else if (path === "/api/v1/asean/comparison") {
    body = {
      indicator: indicators[0],
      observation_year: 2025,
      source_code: "world_bank",
      items: [
        {
          region_code: "IDN",
          region_name: "Indonesia",
          member_since: "1967-08-08",
          was_member_during_period: true,
          observation_date: "2025-01-01",
          value: 5.11,
          asean_average: 4.8,
          difference_from_asean_average: 0.31,
          country_coverage: 11,
          value_rank_desc: 4,
          value_percentile: 0.7,
        },
      ],
    };
  } else if (path.startsWith("/api/v1/forecasts/")) {
    status = 404;
    body = { detail: "Forecast belum tersedia untuk indikator ini" };
  } else if (path === "/api/v1/data-quality") {
    body = {
      status: "healthy",
      blocking_failures: 0,
      informational_findings: 1,
      checks: [
        { name: "check_duplicates", blocking: true, status: "passed", finding_count: 0 },
        { name: "check_data_freshness", blocking: false, status: "info", finding_count: 1 },
      ],
    };
  } else if (path === "/api/v1/pipeline-runs") {
    body = {
      items: [
        {
          run_id: 1,
          source_code: "world_bank",
          started_at: updatedAt,
          completed_at: updatedAt,
          status: "success",
          rows_loaded: 100,
          has_error: false,
        },
      ],
      pagination: { ...pagination, total_items: 1 },
    };
  } else {
    status = 404;
    body = { detail: `Fixture belum tersedia untuk ${path}` };
  }

  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

const pages = [
  ["/", "Sinyal ekonomi dalam satu layar"],
  ["/trends", "Telusuri arah perubahan"],
  ["/regional", "Lihat kesenjangan antarwilayah"],
  ["/asean", "Posisi relatif di kawasan"],
  ["/drivers", "Uji hubungan antarindikator"],
  ["/forecasting", "Estimasi yang lolos quality gate"],
  ["/data-quality", "Kepercayaan data yang terlihat"],
] as const;

test.beforeEach(async ({ page }) => {
  await page.route("**/backend/**", mockBackend);
});

for (const [path, heading] of pages) {
  test(`${path} dapat dibuka tanpa error runtime`, async ({ page }) => {
    const runtimeErrors: string[] = [];
    page.on("pageerror", (error) => runtimeErrors.push(error.message));

    const response = await page.goto(path);

    expect(response?.ok()).toBeTruthy();
    await expect(page.getByRole("heading", { level: 1, name: heading })).toBeVisible();
    await expect(page.getByRole("region", { name: "Filter global dashboard" })).toBeVisible();
    expect(runtimeErrors).toEqual([]);
  });
}
