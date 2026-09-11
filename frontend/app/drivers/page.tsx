"use client";

import { Braces, Sigma } from "lucide-react";
import { useState } from "react";

import { CorrelationHeatmap, ScatterChart } from "@/components/charts/dashboard-charts";
import { useDashboard } from "@/components/dashboard-provider";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/data-state";
import { ExportButton } from "@/components/ui/export-button";
import { MetricCard } from "@/components/ui/metric-card";
import { PageHeader } from "@/components/ui/page-header";
import { UpdateStamp } from "@/components/ui/update-stamp";
import { getIndicatorSeries } from "@/lib/api";
import { downloadCsv } from "@/lib/csv";
import { formatNumber, sourceName } from "@/lib/format";
import { alignSeries, correlationMatrix, pearsonCorrelation } from "@/lib/stats";
import type { NamedSeries } from "@/lib/types";
import { useApiQuery } from "@/lib/use-api-query";

export default function CorrelationDriversPage() {
  const {
    indicators,
    indicatorCode,
    regionCode,
    startYear,
    endYear,
  } = useDashboard();
  const [driverSelection, setDriverSelection] = useState<string[]>([]);
  const [scatterSelection, setScatterSelection] = useState("");
  const primary = indicators.find((item) => item.indicator_code === indicatorCode);
  const compatible = indicators.filter(
    (item) =>
      item.indicator_code !== indicatorCode && item.frequency === primary?.frequency,
  );
  const defaults = compatible.slice(0, 3).map((item) => item.indicator_code);
  const validCustom = driverSelection.filter((code) =>
    compatible.some((item) => item.indicator_code === code),
  );
  const drivers = (validCustom.length > 0 ? validCustom : defaults).slice(0, 4);
  const seriesCodes = [indicatorCode, ...drivers].filter(Boolean);
  const scatterCode = drivers.includes(scatterSelection)
    ? scatterSelection
    : (drivers[0] ?? "");

  const query = useApiQuery(
    `drivers:${seriesCodes.join(",")}:${regionCode}:${startYear}:${endYear}`,
    async (signal) => {
      const responses = await Promise.all(
        seriesCodes.map((code) =>
          getIndicatorSeries(code, regionCode, startYear, endYear, signal),
        ),
      );
      return responses.map((response): NamedSeries => ({
        code: response.indicator.indicator_code,
        name: response.indicator.indicator_name,
        unit: response.indicator.unit,
        items: response.items,
      }));
    },
    seriesCodes.length >= 2,
  );

  const toggleDriver = (code: string) => {
    setDriverSelection((current) => {
      const effective = current.filter((item) =>
        compatible.some((candidate) => candidate.indicator_code === item),
      );
      const base = effective.length > 0 ? effective : defaults;
      if (base.includes(code)) return base.filter((item) => item !== code);
      return base.length >= 4 ? base : [...base, code];
    });
  };

  if (!primary || compatible.length === 0) {
    return (
      <div className="page-stack">
        <PageHeader
          eyebrow="Correlation & drivers"
          title="Uji hubungan antarindikator"
          description="Korelasi dihitung hanya pada periode yang tersedia di seluruh seri."
        />
        <EmptyState description="Indikator ini belum memiliki seri lain dengan frekuensi yang sama untuk dibandingkan." />
      </div>
    );
  }
  if (query.isLoading) return <LoadingState label="Menghitung korelasi observasi…" />;
  if (query.error) return <ErrorState error={query.error} onRetry={query.retry} />;

  const series = query.data ?? [];
  const rows = alignSeries(series);
  const matrix = correlationMatrix(series, rows);
  const primarySeries = series.find((item) => item.code === indicatorCode);
  const scatterSeries = series.find((item) => item.code === scatterCode);
  const pairRows = primarySeries && scatterSeries
    ? alignSeries([primarySeries, scatterSeries])
    : [];
  const driverCorrelations = series
    .filter((item) => item.code !== indicatorCode)
    .map((item) => ({
      item,
      value: pearsonCorrelation(
        rows.map((row) => row.values[indicatorCode]),
        rows.map((row) => row.values[item.code]),
      ),
    }))
    .filter((item): item is { item: NamedSeries; value: number } => item.value !== null)
    .sort((left, right) => Math.abs(right.value) - Math.abs(left.value));
  const strongest = driverCorrelations[0];
  const lastUpdated = series
    .flatMap((item) => item.items.map((point) => point.ingested_at))
    .sort()
    .at(-1);

  const exportCurrentView = () => {
    downloadCsv(
      `correlation-${regionCode}-${startYear}-${endYear}.csv`,
      [
        { key: "period", label: "Periode" },
        ...series.map((item) => ({ key: item.code, label: item.name })),
      ],
      rows.map((row) => ({ period: row.date, ...row.values })),
    );
  };

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Correlation & drivers"
        title="Uji hubungan antarindikator"
        description="Matriks Pearson dan scatter plot menggunakan tanggal yang beririsan; hasil tidak menyatakan sebab-akibat."
        actions={<ExportButton onClick={exportCurrentView} disabled={rows.length === 0} />}
      />

      <section className="driver-picker" aria-label="Pilih indikator pembanding">
        <div>
          <span className="panel-kicker">Indikator pembanding</span>
          <p>Pilih maksimal empat seri dengan frekuensi {primary.frequency}.</p>
        </div>
        <div className="driver-chips">
          {compatible.map((item) => {
            const checked = drivers.includes(item.indicator_code);
            return (
              <button
                type="button"
                key={item.indicator_code}
                className={checked ? "driver-chip driver-chip-active" : "driver-chip"}
                aria-pressed={checked}
                onClick={() => toggleDriver(item.indicator_code)}
              >
                <span /> {item.indicator_name}
              </button>
            );
          })}
        </div>
      </section>

      {rows.length < 2 ? (
        <EmptyState description="Sedikitnya dua periode yang sama dibutuhkan untuk menghitung korelasi. Perluas periode atau pilih seri lain." />
      ) : (
        <>
          <div className="section-meta">
            <div className="source-pills">
              {[...new Set(series.flatMap((item) => item.items.map((point) => point.source_code)))].map((code) => (
                <span className="source-pill" key={code}>{sourceName(code)}</span>
              ))}
            </div>
            <UpdateStamp value={lastUpdated} />
          </div>

          <section className="metric-grid metric-grid-four">
            <MetricCard
              label="Periode beririsan"
              value={String(rows.length)}
              period={`${rows[0].date.slice(0, 4)}–${rows.at(-1)!.date.slice(0, 4)}`}
              source="API indikator"
            />
            <MetricCard
              label="Korelasi terkuat"
              value={strongest ? formatNumber(strongest.value) : "—"}
              period={strongest?.item.name ?? "Belum dapat dihitung"}
              source="Perhitungan Pearson"
              tone="amber"
            />
            <MetricCard
              label="Jumlah seri"
              value={String(series.length)}
              period={`Frekuensi ${primary.frequency}`}
              source="Katalog indikator"
              tone="violet"
            />
            <MetricCard
              label="Observasi scatter"
              value={String(pairRows.length)}
              period={scatterSeries?.name ?? "Pilih pembanding"}
              source="Tanggal beririsan"
              tone="blue"
            />
          </section>

          <section className="content-grid content-grid-balanced">
            <article className="panel">
              <div className="panel-heading">
                <div>
                  <span className="panel-kicker">Correlation heatmap</span>
                  <h2>Matriks hubungan linear</h2>
                </div>
                <Sigma size={20} />
              </div>
              <CorrelationHeatmap
                labels={series.map((item) => item.name)}
                values={matrix}
              />
            </article>

            <article className="panel">
              <div className="panel-heading">
                <div>
                  <span className="panel-kicker">Scatter plot</span>
                  <h2>Pola pasangan observasi</h2>
                </div>
                <select
                  className="compact-select"
                  aria-label="Indikator sumbu Y"
                  value={scatterCode}
                  onChange={(event) => setScatterSelection(event.target.value)}
                >
                  {series.filter((item) => item.code !== indicatorCode).map((item) => (
                    <option key={item.code} value={item.code}>{item.name}</option>
                  ))}
                </select>
              </div>
              {primarySeries && scatterSeries && (
                <ScatterChart
                  xName={primarySeries.name}
                  yName={scatterSeries.name}
                  xUnit={primarySeries.unit}
                  yUnit={scatterSeries.unit}
                  points={pairRows.map((row) => ({
                    date: row.date,
                    x: row.values[primarySeries.code],
                    y: row.values[scatterSeries.code],
                  }))}
                />
              )}
            </article>
          </section>

          <section className="provenance-strip">
            <Braces size={20} />
            <div>
              <strong>Korelasi bersifat deskriptif</strong>
              <span>Koefisien dihitung di browser dari data API yang sedang dilihat dan tidak membuktikan hubungan kausal.</span>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
