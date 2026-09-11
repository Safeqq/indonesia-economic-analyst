export type Frequency = "daily" | "monthly" | "quarterly" | "annual";
export type RegionLevel = "country" | "province" | "city";
export type PipelineStatus = "running" | "success" | "failed";

export interface PaginationMetadata {
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
}

export interface IndicatorReference {
  indicator_code: string;
  indicator_name: string;
  unit: string | null;
  frequency: Frequency;
}

export interface IndicatorSummary extends IndicatorReference {
  source_codes: string[];
  observation_count: number;
  region_count: number;
  period_start: string | null;
  period_end: string | null;
}

export interface RegionReference {
  region_code: string;
  region_name: string;
  region_level: RegionLevel;
  parent_region_code: string | null;
}

export interface RegionSummary extends RegionReference {
  indicator_count: number;
  observation_count: number;
  period_start: string | null;
  period_end: string | null;
}

export interface NationalSnapshot {
  source_code: "world_bank";
  observation_date: string;
  observation_year: number;
  gdp_growth_percent: number | null;
  inflation_percent: number | null;
  unemployment_percent: number | null;
  population: number | null;
  gdp_per_capita_current_usd: number | null;
  indicator_coverage: number;
  last_ingested_at: string;
}

export interface MonetarySnapshot {
  source_code: "bank_indonesia";
  observation_date: string;
  observation_year: number;
  observation_quarter: number;
  observation_month: number;
  bi_rate_percent: number | null;
  bi_rate_change_pp: number | null;
  jisdor_idr_per_usd: number | null;
  jisdor_mom_change: number | null;
  jisdor_mom_percent_change: number | null;
  jisdor_rolling_3_month_average: number | null;
  indicator_coverage: number;
  ingested_at: string;
}

export interface OverviewResponse {
  region: RegionReference;
  national: NationalSnapshot | null;
  monetary: MonetarySnapshot | null;
}

export interface SeriesObservation {
  observation_date: string;
  value: number;
  source_code: string;
  ingested_at: string;
}

export interface IndicatorSeriesResponse {
  indicator: IndicatorReference;
  region: RegionReference;
  items: SeriesObservation[];
  pagination: PaginationMetadata;
}

export interface IndicatorListResponse {
  items: IndicatorSummary[];
  pagination: PaginationMetadata;
}

export interface RegionListResponse {
  items: RegionSummary[];
  pagination: PaginationMetadata;
}

export interface RegionIndicatorSnapshot extends IndicatorReference {
  source_code: string;
  observation_date: string;
  value: number;
  ingested_at: string;
}

export interface RegionOverviewResponse {
  region: RegionReference;
  observation_year: number | null;
  items: RegionIndicatorSnapshot[];
  pagination: PaginationMetadata;
}

export interface ASEANComparisonItem {
  region_code: string;
  region_name: string;
  member_since: string;
  was_member_during_period: boolean;
  observation_date: string;
  value: number;
  asean_average: number;
  difference_from_asean_average: number;
  country_coverage: number;
  value_rank_desc: number;
  value_percentile: number;
}

export interface ASEANComparisonResponse {
  indicator: IndicatorReference;
  observation_year: number;
  source_code: "world_bank";
  items: ASEANComparisonItem[];
}

export interface ForecastMetrics {
  mae: number;
  rmse: number;
  mape_percent: number;
}

export interface ForecastPoint {
  forecast_date: string;
  point_forecast: number;
  lower_bound: number;
  upper_bound: number;
}

export interface ForecastResponse {
  forecast_run_id: number;
  indicator: IndicatorReference;
  region: RegionReference;
  source_code: string;
  generated_at: string;
  data_start: string;
  data_end: string;
  test_start: string;
  test_end: string;
  selected_model_name: string;
  selected_model_family: "arima" | "sarima";
  baseline_model_name: string;
  selected_metrics: ForecastMetrics;
  baseline_metrics: ForecastMetrics;
  mae_improvement_percent: number | null;
  interval_coverage_percent: number | null;
  forecast_horizon: number;
  confidence_level: number;
  quality_status: "passed" | "failed";
  quality_reasons: string[];
  quality_thresholds: Record<string, number>;
  anomaly_count: number;
  is_estimate_not_fact: true;
  items: ForecastPoint[];
}

export interface DataQualityCheck {
  name: string;
  blocking: boolean;
  status: "passed" | "failed" | "info";
  finding_count: number;
}

export interface DataQualityResponse {
  status: "healthy" | "degraded";
  blocking_failures: number;
  informational_findings: number;
  checks: DataQualityCheck[];
}

export interface PipelineRunItem {
  run_id: number;
  source_code: string;
  started_at: string;
  completed_at: string | null;
  status: PipelineStatus;
  rows_loaded: number;
  has_error: boolean;
}

export interface PipelineRunListResponse {
  items: PipelineRunItem[];
  pagination: PaginationMetadata;
}

export interface ChartPoint {
  date: string;
  value: number;
}

export interface NamedSeries {
  code: string;
  name: string;
  unit: string | null;
  items: SeriesObservation[];
}

