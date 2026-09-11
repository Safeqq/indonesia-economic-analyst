"use client";

import { Award, Globe2 } from "lucide-react";

import { ComparisonChart } from "@/components/charts/dashboard-charts";
import { useDashboard } from "@/components/dashboard-provider";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/data-state";
import { ExportButton } from "@/components/ui/export-button";
import { MetricCard } from "@/components/ui/metric-card";
import { PageHeader } from "@/components/ui/page-header";
import { UpdateStamp } from "@/components/ui/update-stamp";
import { ApiError, getAseanComparison, getIndicatorSeries } from "@/lib/api";
import { downloadCsv } from "@/lib/csv";
import { formatDate, formatSigned, formatValue, sourceName } from "@/lib/format";
import { useApiQuery } from "@/lib/use-api-query";

export default function AseanBenchmarkPage() {
  const { indicatorCode, countryCode, endYear } = useDashboard();
  const query = useApiQuery(
    `asean:${indicatorCode}:${countryCode}:${endYear}`,
    async (signal) => {
      const comparison = await getAseanComparison(indicatorCode, endYear, signal);
      const selectedSeries = await getIndicatorSeries(
        indicatorCode,
        countryCode,
        endYear,
        endYear,
        signal,
      );
      return { comparison, selectedSeries };
    },
    Boolean(indicatorCode),
  );

  if (query.isLoading) return <LoadingState label="Membandingkan negara ASEAN…" />;
  if (query.error instanceof ApiError && query.error.status === 404) {
    return (
      <div className="page-stack">
        <PageHeader
          eyebrow="ASEAN benchmark"
          title="Posisi relatif di kawasan"
          description="Bandingkan negara pada indikator dan tahun observasi yang sama."
        />
        <EmptyState
          title="Benchmark belum tersedia"
          description="Indikator atau tahun ini belum memiliki cakupan negara ASEAN. Pilih indikator World Bank dan periode yang tersedia."
        />
      </div>
    );
  }
  if (query.error) return <ErrorState error={query.error} onRetry={query.retry} />;
  if (!query.data || query.data.comparison.items.length === 0) {
    return <EmptyState description="Tidak ada negara yang dapat dibandingkan pada filter aktif." />;
  }

  const { comparison, selectedSeries } = query.data;
  const items = comparison.items;
  const selected = items.find((item) => item.region_code === countryCode);
  const reference = selected ?? items[0];
  const lastUpdated = [...selectedSeries.items]
    .sort((left, right) => left.ingested_at.localeCompare(right.ingested_at))
    .at(-1)?.ingested_at;

  const exportCurrentView = () => {
    downloadCsv(
      `asean-${comparison.indicator.indicator_code}-${comparison.observation_year}.csv`,
      [
        { key: "rank", label: "Peringkat" },
        { key: "country_code", label: "Kode negara" },
        { key: "country", label: "Negara" },
        { key: "period", label: "Periode" },
        { key: "value", label: "Nilai" },
        { key: "asean_average", label: "Rata-rata ASEAN" },
        { key: "difference", label: "Selisih dari rata-rata" },
        { key: "unit", label: "Satuan" },
        { key: "source", label: "Sumber" },
      ],
      items.map((item) => ({
        rank: item.value_rank_desc,
        country_code: item.region_code,
        country: item.region_name,
        period: item.observation_date,
        value: item.value,
        asean_average: item.asean_average,
        difference: item.difference_from_asean_average,
        unit: comparison.indicator.unit,
        source: comparison.source_code,
      })),
    );
  };

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="ASEAN benchmark"
        title="Posisi relatif di kawasan"
        description="Peringkat, jarak terhadap rata-rata, dan cakupan negara pada basis data yang sama."
        actions={<ExportButton onClick={exportCurrentView} />}
      />

      <div className="section-meta">
        <div className="source-pills">
          <span className="source-pill">{sourceName(comparison.source_code)}</span>
          <span className="source-pill source-pill-muted">
            {items.length} dari {reference.country_coverage} negara tercakup
          </span>
        </div>
        <UpdateStamp value={lastUpdated} />
      </div>

      <section className="metric-grid metric-grid-four">
        <MetricCard
          label={selected?.region_name ?? "Negara terpilih"}
          value={selected ? formatValue(selected.value, comparison.indicator.unit) : "—"}
          period={selected ? formatDate(selected.observation_date) : "Tidak tercakup"}
          source={sourceName(comparison.source_code)}
        />
        <MetricCard
          label="Rata-rata ASEAN"
          value={formatValue(reference.asean_average, comparison.indicator.unit)}
          period={`Tahun ${comparison.observation_year}`}
          source={sourceName(comparison.source_code)}
          tone="amber"
        />
        <MetricCard
          label="Selisih dari rata-rata"
          value={selected ? formatSigned(selected.difference_from_asean_average) : "—"}
          change={
            selected
              ? selected.difference_from_asean_average >= 0
                ? "Di atas rata-rata"
                : "Di bawah rata-rata"
              : undefined
          }
          changeValue={selected?.difference_from_asean_average}
          period={selected?.region_name ?? "Tidak tercakup"}
          source={sourceName(comparison.source_code)}
          tone="violet"
        />
        <MetricCard
          label="Peringkat kawasan"
          value={selected ? `#${selected.value_rank_desc}` : "—"}
          period={selected ? `Persentil ${Math.round(selected.value_percentile * 100)}` : "Tidak tercakup"}
          source={sourceName(comparison.source_code)}
          tone="blue"
        />
      </section>

      <section className="content-grid content-grid-balanced">
        <article className="panel">
          <div className="panel-heading">
            <div>
              <span className="panel-kicker">Comparison chart</span>
              <h2>{comparison.indicator.indicator_name}</h2>
              <p>Negara pada filter ditandai warna jingga.</p>
            </div>
            <span className="unit-chip"><Globe2 size={14} /> {comparison.observation_year}</span>
          </div>
          <ComparisonChart
            label={`Benchmark ASEAN ${comparison.indicator.indicator_name}`}
            unit={comparison.indicator.unit}
            selectedCode={countryCode}
            items={items.map((item) => ({
              code: item.region_code,
              name: item.region_name,
              value: item.value,
            }))}
          />
        </article>

        <article className="panel">
          <div className="panel-heading">
            <div>
              <span className="panel-kicker">Ranking</span>
              <h2>Urutan negara</h2>
            </div>
            <Award size={20} />
          </div>
          <div className="ranking-list">
            {[...items]
              .sort((left, right) => left.value_rank_desc - right.value_rank_desc)
              .map((item) => (
                <div
                  className={item.region_code === countryCode ? "ranking-row ranking-row-active" : "ranking-row"}
                  key={item.region_code}
                >
                  <strong>{item.value_rank_desc}</strong>
                  <div><span>{item.region_name}</span><small>{formatDate(item.observation_date)}</small></div>
                  <b>{formatValue(item.value, comparison.indicator.unit)}</b>
                </div>
              ))}
          </div>
        </article>
      </section>
    </div>
  );
}
