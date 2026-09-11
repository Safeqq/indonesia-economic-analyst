"use client";

import { Maximize2, TrendingUp } from "lucide-react";

import { TimeSeriesChart } from "@/components/charts/dashboard-charts";
import { useDashboard } from "@/components/dashboard-provider";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/data-state";
import { ExportButton } from "@/components/ui/export-button";
import { MetricCard } from "@/components/ui/metric-card";
import { PageHeader } from "@/components/ui/page-header";
import { UpdateStamp } from "@/components/ui/update-stamp";
import { getIndicatorSeries } from "@/lib/api";
import { downloadCsv } from "@/lib/csv";
import {
  formatDate,
  formatSigned,
  formatValue,
  frequencyName,
  sourceName,
} from "@/lib/format";
import { summarizeSeries } from "@/lib/stats";
import { useApiQuery } from "@/lib/use-api-query";

export default function TrendExplorerPage() {
  const { indicatorCode, regionCode, startYear, endYear } = useDashboard();
  const query = useApiQuery(
    `trend:${indicatorCode}:${regionCode}:${startYear}:${endYear}`,
    (signal) =>
      getIndicatorSeries(indicatorCode, regionCode, startYear, endYear, signal),
    Boolean(indicatorCode),
  );

  const exportCurrentView = () => {
    if (!query.data) return;
    const { indicator, region, items } = query.data;
    downloadCsv(
      `trend-${indicator.indicator_code}-${region.region_code}-${startYear}-${endYear}.csv`,
      [
        { key: "period", label: "Periode" },
        { key: "value", label: "Nilai" },
        { key: "unit", label: "Satuan" },
        { key: "region", label: "Wilayah" },
        { key: "source", label: "Sumber" },
        { key: "ingested_at", label: "Waktu ingestion" },
      ],
      items.map((item) => ({
        period: item.observation_date,
        value: item.value,
        unit: indicator.unit,
        region: region.region_name,
        source: item.source_code,
        ingested_at: item.ingested_at,
      })),
    );
  };

  if (query.isLoading) return <LoadingState label="Mengambil rangkaian waktu…" />;
  if (query.error) return <ErrorState error={query.error} onRetry={query.retry} />;
  if (!query.data || query.data.items.length === 0) {
    return (
      <div className="page-stack">
        <PageHeader
          eyebrow="Trend explorer"
          title="Telusuri arah perubahan"
          description="Bandingkan observasi dari waktu ke waktu pada periode yang konsisten."
        />
        <EmptyState description="Tidak ada observasi pada kombinasi filter ini. Ubah periode, indikator, atau wilayah." />
      </div>
    );
  }

  const { indicator, region, items } = query.data;
  const summary = summarizeSeries(items)!;
  const latestUpdate = [...items].sort((a, b) =>
    a.ingested_at.localeCompare(b.ingested_at),
  ).at(-1)?.ingested_at;

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Trend explorer"
        title="Telusuri arah perubahan"
        description="Baca level, rentang, dan perubahan antar-observasi tanpa kehilangan konteks sumber."
        actions={<ExportButton onClick={exportCurrentView} />}
      />

      <div className="section-meta">
        <div className="source-pills">
          <span className="source-pill">{sourceName(summary.latest.source_code)}</span>
          <span className="source-pill source-pill-muted">{frequencyName(indicator.frequency)}</span>
        </div>
        <UpdateStamp value={latestUpdate} />
      </div>

      <section className="metric-grid metric-grid-four">
        <MetricCard
          label="Nilai terbaru"
          value={formatValue(summary.latest.value, indicator.unit)}
          change={formatSigned(summary.percentChange, "%")}
          changeValue={summary.percentChange}
          period={formatDate(summary.latest.observation_date)}
          source={sourceName(summary.latest.source_code)}
        />
        <MetricCard
          label="Perubahan absolut"
          value={formatSigned(summary.absoluteChange)}
          period={summary.previous ? `dari ${formatDate(summary.previous.observation_date)}` : "Tanpa pembanding"}
          source={sourceName(summary.latest.source_code)}
          tone="amber"
        />
        <MetricCard
          label="Nilai minimum"
          value={formatValue(summary.minimum, indicator.unit)}
          period={`${items.length} observasi aktif`}
          source={sourceName(summary.latest.source_code)}
          tone="violet"
        />
        <MetricCard
          label="Nilai maksimum"
          value={formatValue(summary.maximum, indicator.unit)}
          period={`${startYear}–${endYear}`}
          source={sourceName(summary.latest.source_code)}
          tone="blue"
        />
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="panel-kicker">Time series</span>
            <h2>{indicator.indicator_name}</h2>
            <p>{region.region_name} · {items.length} observasi</p>
          </div>
          <span className="unit-chip"><TrendingUp size={14} /> {indicator.unit ?? "Tanpa satuan"}</span>
        </div>
        <TimeSeriesChart
          label={`Time series ${indicator.indicator_name} di ${region.region_name}`}
          unit={indicator.unit}
          height={420}
          series={[
            {
              name: indicator.indicator_name,
              points: items.map((item) => ({ date: item.observation_date, value: item.value })),
              color: "#18a999",
            },
          ]}
        />
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="panel-kicker">Observasi</span>
            <h2>Data yang sedang dilihat</h2>
          </div>
          <span className="table-count"><Maximize2 size={14} /> {items.length} baris</span>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>Periode</th><th>Nilai</th><th>Satuan</th><th>Sumber</th><th>Ingestion</th></tr>
            </thead>
            <tbody>
              {[...items].reverse().map((item) => (
                <tr key={`${item.observation_date}-${item.source_code}`}>
                  <td>{formatDate(item.observation_date)}</td>
                  <td className="numeric-cell">{formatValue(item.value, indicator.unit)}</td>
                  <td>{indicator.unit ?? "—"}</td>
                  <td><span className="source-pill">{sourceName(item.source_code)}</span></td>
                  <td>{formatDate(item.ingested_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
