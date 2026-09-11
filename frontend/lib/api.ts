import type {
  ASEANComparisonResponse,
  DataQualityResponse,
  ForecastResponse,
  IndicatorListResponse,
  IndicatorSeriesResponse,
  IndicatorSummary,
  OverviewResponse,
  PipelineRunListResponse,
  RegionListResponse,
  RegionOverviewResponse,
  RegionSummary,
} from "@/lib/types";

const API_PREFIX = "/backend";
const PAGE_SIZE = 100;

type QueryValue = string | number | boolean | null | undefined;

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export function buildQuery(parameters: Record<string, QueryValue>): string {
  const query = new URLSearchParams();
  Object.entries(parameters).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== "") {
      query.set(key, String(value));
    }
  });
  const serialized = query.toString();
  return serialized ? `?${serialized}` : "";
}

async function request<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_PREFIX}${path}`, {
    cache: "no-store",
    headers: { Accept: "application/json" },
    signal,
  });

  if (!response.ok) {
    let message = "Layanan data tidak dapat memproses permintaan.";
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) message = body.detail;
    } catch {
      // Respons non-JSON tetap diterjemahkan menjadi pesan yang aman.
    }
    throw new ApiError(message, response.status);
  }

  return (await response.json()) as T;
}

async function collectPages<T>(
  loadPage: (page: number) => Promise<{
    items: T[];
    pagination: { total_pages: number };
  }>,
): Promise<T[]> {
  const firstPage = await loadPage(1);
  if (firstPage.pagination.total_pages <= 1) return firstPage.items;

  const remaining = await Promise.all(
    Array.from(
      { length: firstPage.pagination.total_pages - 1 },
      (_, index) => loadPage(index + 2),
    ),
  );
  return [firstPage, ...remaining].flatMap((page) => page.items);
}

export function getOverview(signal?: AbortSignal): Promise<OverviewResponse> {
  return request("/api/v1/overview", signal);
}

export function getIndicators(signal?: AbortSignal): Promise<IndicatorSummary[]> {
  return collectPages((page) =>
    request<IndicatorListResponse>(
      `/api/v1/indicators${buildQuery({ page, page_size: PAGE_SIZE })}`,
      signal,
    ),
  );
}

export function getRegions(signal?: AbortSignal): Promise<RegionSummary[]> {
  return collectPages((page) =>
    request<RegionListResponse>(
      `/api/v1/regions${buildQuery({ page, page_size: PAGE_SIZE })}`,
      signal,
    ),
  );
}

export function getIndicatorSeries(
  indicatorCode: string,
  regionCode: string,
  startYear?: number,
  endYear?: number,
  signal?: AbortSignal,
): Promise<IndicatorSeriesResponse> {
  const encodedCode = encodeURIComponent(indicatorCode);
  const queryForPage = (page: number) =>
    buildQuery({
      region_code: regionCode,
      start_year: startYear,
      end_year: endYear,
      page,
      page_size: PAGE_SIZE,
    });

  return request<IndicatorSeriesResponse>(
    `/api/v1/indicators/${encodedCode}/series${queryForPage(1)}`,
    signal,
  ).then(async (firstPage) => {
    if (firstPage.pagination.total_pages <= 1) return firstPage;
    const remaining = await Promise.all(
      Array.from(
        { length: firstPage.pagination.total_pages - 1 },
        (_, index) =>
          request<IndicatorSeriesResponse>(
            `/api/v1/indicators/${encodedCode}/series${queryForPage(index + 2)}`,
            signal,
          ),
      ),
    );
    return {
      ...firstPage,
      items: [firstPage, ...remaining].flatMap((page) => page.items),
    };
  });
}

export function getRegionOverview(
  regionCode: string,
  year: number,
  signal?: AbortSignal,
): Promise<RegionOverviewResponse> {
  return request(
    `/api/v1/regions/${encodeURIComponent(regionCode)}/overview${buildQuery({
      year,
      page_size: PAGE_SIZE,
    })}`,
    signal,
  );
}

export function getAseanComparison(
  indicatorCode: string,
  year: number,
  signal?: AbortSignal,
): Promise<ASEANComparisonResponse> {
  return request(
    `/api/v1/asean/comparison${buildQuery({
      indicator_code: indicatorCode,
      year,
    })}`,
    signal,
  );
}

export function getForecast(
  indicatorCode: string,
  regionCode: string,
  signal?: AbortSignal,
): Promise<ForecastResponse> {
  return request(
    `/api/v1/forecasts/${encodeURIComponent(indicatorCode)}${buildQuery({
      region_code: regionCode,
    })}`,
    signal,
  );
}

export function getDataQuality(signal?: AbortSignal): Promise<DataQualityResponse> {
  return request("/api/v1/data-quality", signal);
}

export function getPipelineRuns(
  signal?: AbortSignal,
): Promise<PipelineRunListResponse> {
  return request(`/api/v1/pipeline-runs?page_size=${PAGE_SIZE}`, signal);
}

