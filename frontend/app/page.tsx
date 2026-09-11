"use client";

import { ArrowRight, DatabaseZap, Layers3 } from "lucide-react";
import Link from "next/link";

import { TimeSeriesChart } from "@/components/charts/dashboard-charts";
import { useDashboard } from "@/components/dashboard-provider";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/data-state";
import { ExportButton } from "@/components/ui/export-button";
import { MetricCard } from "@/components/ui/metric-card";
import { PageHeader } from "@/components/ui/page-header";
import { UpdateStamp } from "@/components/ui/update-stamp";
import { getIndicatorSeries, getOverview } from "@/lib/api";
import { downloadCsv } from "@/lib/csv";
import { formatDate, formatSigned, formatValue, sourceName } from "@/lib/format";
import { summarizeSeries } from "@/lib/stats";
import type { IndicatorSeriesResponse } from "@/lib/types";
import { useApiQuery } from "@/lib/use-api-query";

const overviewIndicatorCodes = [
  "NY.GDP.MKTP.KD.ZG",
  "FP.CPI.TOTL.ZG",
  "SL.UEM.TOTL.ZS",
  "BI.POLICY_RATE.MONTHLY",
  "BI.JISDOR.USD_IDR.MONTHLY_AVG",
];

const tones = ["teal", "amber", "violet", "blue", "teal"] as const;

export default function ExecutiveOverviewPage() {
  const { indicatorCode, regionCode, startYear, endYear } = useDashboard();
  const currentYear = new Date().getFullYear();
  const query = useApiQuery(
    `overview:${indicatorCode}:${regionCode}:${startYear}:${endYear}:${currentYear}`,
    async (signal) => {
      const [overview, selectedSeries, kpiResults] = await Promise.all([
        getOverview(signal),
        getIndicatorSeries(indicatorCode, regionCode, startYear, endYear, signal),
        Promise.allSettled(
          overviewIndicatorCodes.map((code) =>
            getIndicatorSeries(code, "IDN", currentYear - 2, currentYear, signal),
          ),
        ),
      ]);
      const kpiSeries = kpiResults.flatMap((result) =>
        result.status === "fulfilled" ? [result.value] : [],
      );
      return { overview, selectedSeries, kpiSeries };
    },
    Boolean(indicatorCode),
  );

  if (query.isLoading) return <LoadingState label="Menyusun ringkasan ekonomi…" />;
  if (query.error) return <ErrorState error={query.error} onRetry={query.retry} />;
  if (!query.data) {
    return <EmptyState description="Katalog indikator belum memiliki data untuk diringkas." />;
  }

  const { overview, selectedSeries, kpiSeries } = query.data;
  const selectedSummary = summarizeSeries(selectedSeries.items);
  const overviewSources: string[] = [];
  if (overview.national) overviewSources.push(overview.national.source_code);
  if (overview.monetary) overviewSources.push(overview.monetary.source_code);
  const timestamps = [
    overview.national?.last_ingested_at,
    overview.monetary?.ingested_at,
    ...selectedSeries.items.map((item) => item.ingested_at),
  ].filter((value): value is string => Boolean(value));
  const lastUpdated = [...timestamps].sort().at(-1);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Executive overview"
        title="Sinyal ekonomi dalam satu layar"
        description="Ringkasan data nasional, moneter, dan tren terpilih dari sumber resmi."
        actions={
          <ExportButton
            disabled={selectedSeries.items.length === 0}
            onClick={() => exportSeries(selectedSeries)}
          />
        }
      />

      <div className="section-meta">
        <div className="source-pills">
          {overviewSources.map((code) => (
            <span className="source-pill" key={code}>{sourceName(code)}</span>
          ))}
        </div>
        <UpdateStamp value={lastUpdated} />
      </div>

      {kpiSeries.length > 0 ? (
        <section className="metric-grid" aria-label="Indikator ekonomi utama">
          {kpiSeries.map((series, index) => {
            const summary = summarizeSeries(series.items);
            if (!summary) return null;
            const changeUsesPoints = series.indicator.unit
              ?.toLowerCase()
              .includes("percent");
            const comparableChange = changeUsesPoints
              ? summary.absoluteChange
              : summary.percentChange;
            return (
              <MetricCard
                key={series.indicator.indicator_code}
                label={series.indicator.indicator_name}
                value={formatValue(
                  summary.latest.value,
                  series.indicator.unit,
                  Math.abs(summary.latest.value) >= 10_000,
                )}
                change={formatSigned(comparableChange, changeUsesPoints ? " poin" : "%")}
                changeValue={comparableChange}
                period={formatDate(summary.latest.observation_date)}
                source={sourceName(summary.latest.source_code)}
                tone={tones[index % tones.length]}
              />
            );
          })}
        </section>
      ) : (
        <EmptyState description="Nilai KPI belum tersedia pada periode filter yang dipilih." />
      )}

      <section className="content-grid content-grid-main">
        <article className="panel panel-large">
          <div className="panel-heading">
            <div>
              <span className="panel-kicker">Tren terpilih</span>
              <h2>{selectedSeries.indicator.indicator_name}</h2>
              <p>{selectedSeries.region.region_name} · {startYear}–{endYear}</p>
            </div>
            <span className="unit-chip">{selectedSeries.indicator.unit ?? "Tanpa satuan"}</span>
          </div>
          {selectedSeries.items.length > 0 ? (
            <TimeSeriesChart
              label={`Tren ${selectedSeries.indicator.indicator_name}`}
              unit={selectedSeries.indicator.unit}
              series={[
                {
                  name: selectedSeries.indicator.indicator_name,
                  points: selectedSeries.items.map((item) => ({
                    date: item.observation_date,
                    value: item.value,
                  })),
                  color: "#18a999",
                },
              ]}
            />
          ) : (
            <EmptyState description="Tidak ada observasi untuk kombinasi indikator, wilayah, dan periode ini." />
          )}
        </article>

        <aside className="panel insight-panel">
          <div className="insight-icon"><DatabaseZap size={21} /></div>
          <span className="panel-kicker">Pembacaan terbaru</span>
          <h2>
            {selectedSummary
              ? formatValue(selectedSummary.latest.value, selectedSeries.indicator.unit)
              : "—"}
          </h2>
          <p>
            {selectedSummary
              ? `Observasi ${formatDate(selectedSummary.latest.observation_date)} untuk ${selectedSeries.region.region_name}.`
              : "Belum ada observasi pada rentang aktif."}
          </p>
          {selectedSummary?.previous && (
            <div className="insight-row">
              <span>Perubahan antar-observasi</span>
              <strong>{formatSigned(selectedSummary.percentChange, "%")}</strong>
            </div>
          )}
          <div className="insight-row">
            <span>Sumber</span>
            <strong>
              {selectedSummary ? sourceName(selectedSummary.latest.source_code) : "—"}
            </strong>
          </div>
          <Link className="text-link" href="/trends">
            Analisis tren lengkap <ArrowRight size={15} />
          </Link>
        </aside>
      </section>

      <section className="provenance-strip">
        <Layers3 size={20} />
        <div>
          <strong>Angka berasal dari pipeline produksi</strong>
          <span>Tooltip, periode, sumber, dan waktu ingestion mengikuti respons FastAPI.</span>
        </div>
      </section>
    </div>
  );
}

function exportSeries(series: IndicatorSeriesResponse) {
  downloadCsv(
    `${series.indicator.indicator_code}-${series.region.region_code}.csv`,
    [
      { key: "date", label: "Periode" },
      { key: "value", label: "Nilai" },
      { key: "unit", label: "Satuan" },
      { key: "region", label: "Wilayah" },
      { key: "source", label: "Sumber" },
      { key: "ingested_at", label: "Waktu ingestion" },
    ],
    series.items.map((item) => ({
      date: item.observation_date,
      value: item.value,
      unit: series.indicator.unit,
      region: series.region.region_name,
      source: item.source_code,
      ingested_at: item.ingested_at,
    })),
  );
}
