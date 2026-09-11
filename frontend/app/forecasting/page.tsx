"use client";

import { Beaker, ShieldAlert, ShieldCheck, Sparkles } from "lucide-react";

import { ForecastChart } from "@/components/charts/dashboard-charts";
import { useDashboard } from "@/components/dashboard-provider";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/data-state";
import { ExportButton } from "@/components/ui/export-button";
import { MetricCard } from "@/components/ui/metric-card";
import { PageHeader } from "@/components/ui/page-header";
import { UpdateStamp } from "@/components/ui/update-stamp";
import { ApiError, getForecast, getIndicatorSeries } from "@/lib/api";
import { downloadCsv } from "@/lib/csv";
import { formatDate, formatSigned, formatValue, sourceName } from "@/lib/format";
import { useApiQuery } from "@/lib/use-api-query";

const JISDOR_CODE = "BI.JISDOR.USD_IDR.MONTHLY_AVG";

export default function ForecastingLabPage() {
  const {
    indicators,
    indicatorCode,
    regionCode,
    startYear,
    endYear,
    setIndicatorCode,
  } = useDashboard();
  const query = useApiQuery(
    `forecast:${indicatorCode}:${regionCode}:${startYear}:${endYear}`,
    async (signal) => {
      const forecast = await getForecast(indicatorCode, regionCode, signal);
      const history = await getIndicatorSeries(
        indicatorCode,
        regionCode,
        startYear,
        endYear,
        signal,
      );
      return { forecast, history };
    },
    Boolean(indicatorCode),
  );
  const jisdorAvailable = indicators.some(
    (item) => item.indicator_code === JISDOR_CODE,
  );

  if (query.isLoading) return <LoadingState label="Memeriksa hasil forecasting…" />;
  if (query.error instanceof ApiError && query.error.status === 404) {
    return (
      <div className="page-stack">
        <PageHeader
          eyebrow="Forecasting lab"
          title="Estimasi yang lolos quality gate"
          description="Hanya run model tervalidasi yang dapat memublikasikan titik estimasi."
        />
        <div className="state-card" role="status">
          <div className="state-icon"><Beaker size={24} /></div>
          <strong>Forecast belum tersedia untuk pilihan ini</strong>
          <p>Pilih indikator dan wilayah yang sudah memiliki run advanced analytics.</p>
          {jisdorAvailable && indicatorCode !== JISDOR_CODE && (
            <button
              className="button button-primary"
              type="button"
              onClick={() => setIndicatorCode(JISDOR_CODE)}
            >
              <Sparkles size={16} /> Buka forecast JISDOR
            </button>
          )}
        </div>
      </div>
    );
  }
  if (query.error) return <ErrorState error={query.error} onRetry={query.retry} />;
  if (!query.data) return <EmptyState description="Belum ada hasil model tersimpan." />;

  const { forecast, history } = query.data;
  const gatePassed = forecast.quality_status === "passed";

  const exportCurrentView = () => {
    downloadCsv(
      `forecast-${forecast.indicator.indicator_code}-${forecast.forecast_run_id}.csv`,
      [
        { key: "period", label: "Periode estimasi" },
        { key: "point", label: "Estimasi titik" },
        { key: "lower", label: "Batas bawah" },
        { key: "upper", label: "Batas atas" },
        { key: "unit", label: "Satuan" },
        { key: "model", label: "Model" },
        { key: "source", label: "Sumber" },
        { key: "is_estimate", label: "Merupakan estimasi" },
      ],
      forecast.items.map((point) => ({
        period: point.forecast_date,
        point: point.point_forecast,
        lower: point.lower_bound,
        upper: point.upper_bound,
        unit: forecast.indicator.unit,
        model: forecast.selected_model_name,
        source: forecast.source_code,
        is_estimate: forecast.is_estimate_not_fact,
      })),
    );
  };

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Forecasting lab"
        title="Estimasi yang lolos quality gate"
        description="Evaluasi out-of-sample, pembanding naïve, dan interval ketidakpastian tampil bersama hasil model."
        actions={
          <ExportButton
            onClick={exportCurrentView}
            disabled={!gatePassed || forecast.items.length === 0}
          />
        }
      />

      <div className="section-meta">
        <div className="source-pills">
          <span className="source-pill">{sourceName(forecast.source_code)}</span>
          <span className={gatePassed ? "status-badge status-success" : "status-badge status-danger"}>
            {gatePassed ? <ShieldCheck size={14} /> : <ShieldAlert size={14} />}
            Quality gate {gatePassed ? "lulus" : "gagal"}
          </span>
          <span className="estimate-badge">Estimasi model · bukan fakta</span>
        </div>
        <UpdateStamp value={forecast.generated_at} />
      </div>

      <section className="metric-grid metric-grid-four">
        <MetricCard
          label="MAE model"
          value={formatValue(forecast.selected_metrics.mae, forecast.indicator.unit)}
          change={`Baseline ${formatValue(forecast.baseline_metrics.mae, forecast.indicator.unit)}`}
          period={`${formatDate(forecast.test_start)}–${formatDate(forecast.test_end)}`}
          source={forecast.selected_model_name}
        />
        <MetricCard
          label="Perbaikan MAE"
          value={formatSigned(forecast.mae_improvement_percent, "%")}
          changeValue={forecast.mae_improvement_percent}
          period={`vs ${forecast.baseline_model_name}`}
          source="Evaluasi out-of-sample"
          tone="amber"
        />
        <MetricCard
          label="Cakupan interval"
          value={formatValue(forecast.interval_coverage_percent, "percent")}
          period={`Confidence ${Math.round(forecast.confidence_level * 100)}%`}
          source="Holdout test"
          tone="violet"
        />
        <MetricCard
          label="Horizon"
          value={`${forecast.forecast_horizon} periode`}
          period={`${forecast.items.length} estimasi dipublikasikan`}
          source={`Run #${forecast.forecast_run_id}`}
          tone="blue"
        />
      </section>

      {!gatePassed ? (
        <section className="panel gate-failure">
          <ShieldAlert size={23} />
          <div>
            <h2>Estimasi tidak dipublikasikan</h2>
            <p>{forecast.quality_reasons.join(" · ") || "Quality gate model tidak terpenuhi."}</p>
          </div>
        </section>
      ) : forecast.items.length === 0 ? (
        <EmptyState description="Run lulus tetapi belum memiliki titik estimasi yang dapat ditampilkan." />
      ) : (
        <section className="panel">
          <div className="panel-heading">
            <div>
              <span className="panel-kicker">Actual vs estimate</span>
              <h2>{forecast.indicator.indicator_name}</h2>
              <p>Garis putus-putus dan area jingga adalah hasil model beserta intervalnya.</p>
            </div>
            <span className="unit-chip"><Sparkles size={14} /> {forecast.indicator.unit ?? "Tanpa satuan"}</span>
          </div>
          <ForecastChart
            unit={forecast.indicator.unit}
            history={history.items.map((item) => ({
              date: item.observation_date,
              value: item.value,
            }))}
            forecast={forecast.items}
          />
        </section>
      )}

      <section className="content-grid content-grid-balanced">
        <article className="panel compact-panel">
          <span className="panel-kicker">Konfigurasi terpilih</span>
          <h2>{forecast.selected_model_name}</h2>
          <dl className="definition-list">
            <div><dt>Keluarga</dt><dd>{forecast.selected_model_family.toUpperCase()}</dd></div>
            <div><dt>Baseline</dt><dd>{forecast.baseline_model_name}</dd></div>
            <div><dt>Data latih sampai</dt><dd>{formatDate(forecast.data_end)}</dd></div>
            <div><dt>Anomali terdeteksi</dt><dd>{forecast.anomaly_count}</dd></div>
          </dl>
        </article>
        <article className="panel compact-panel">
          <span className="panel-kicker">Ketelitian holdout</span>
          <h2>Evaluasi sebelum publikasi</h2>
          <dl className="definition-list">
            <div><dt>RMSE</dt><dd>{formatValue(forecast.selected_metrics.rmse, forecast.indicator.unit)}</dd></div>
            <div><dt>MAPE</dt><dd>{formatValue(forecast.selected_metrics.mape_percent, "percent")}</dd></div>
            <div><dt>Mulai holdout</dt><dd>{formatDate(forecast.test_start)}</dd></div>
            <div><dt>Akhir holdout</dt><dd>{formatDate(forecast.test_end)}</dd></div>
          </dl>
        </article>
      </section>
    </div>
  );
}
