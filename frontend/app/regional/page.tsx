"use client";

import { BarChart3, MapPinned } from "lucide-react";

import { ComparisonChart } from "@/components/charts/dashboard-charts";
import { useDashboard } from "@/components/dashboard-provider";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/data-state";
import { ExportButton } from "@/components/ui/export-button";
import { MetricCard } from "@/components/ui/metric-card";
import { PageHeader } from "@/components/ui/page-header";
import { UpdateStamp } from "@/components/ui/update-stamp";
import { getRegionOverview } from "@/lib/api";
import { downloadCsv } from "@/lib/csv";
import { formatDate, formatValue, sourceName } from "@/lib/format";
import type { RegionIndicatorSnapshot } from "@/lib/types";
import { useApiQuery } from "@/lib/use-api-query";

interface RegionalValue {
  regionCode: string;
  regionName: string;
  observation: RegionIndicatorSnapshot;
}

function median(values: number[]): number | null {
  if (values.length === 0) return null;
  const sorted = [...values].sort((left, right) => left - right);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2
    ? sorted[middle]
    : (sorted[middle - 1] + sorted[middle]) / 2;
}

export default function RegionalAnalysisPage() {
  const {
    indicatorCode,
    regionCode,
    endYear,
    regions,
    isCatalogLoading,
  } = useDashboard();
  const provinces = regions.filter((region) => region.region_level === "province");
  const provinceKey = provinces.map((region) => region.region_code).join(",");
  const query = useApiQuery(
    `regional:${indicatorCode}:${endYear}:${provinceKey}`,
    async (signal) => {
      const results = await Promise.all(
        provinces.map((region) =>
          getRegionOverview(region.region_code, endYear, signal).then((response) => ({
            region,
            response,
          })),
        ),
      );
      return results.flatMap(({ region, response }): RegionalValue[] => {
        const observation = response.items.find(
          (item) => item.indicator_code === indicatorCode,
        );
        return observation
          ? [{ regionCode: region.region_code, regionName: region.region_name, observation }]
          : [];
      });
    },
    Boolean(indicatorCode) && provinces.length > 0,
  );

  if (isCatalogLoading || query.isLoading) {
    return <LoadingState label="Menyusun perbandingan regional…" />;
  }
  if (query.error) return <ErrorState error={query.error} onRetry={query.retry} />;

  const values = query.data ?? [];
  const first = values[0]?.observation;
  const selected = values.find((item) => item.regionCode === regionCode);
  const sorted = [...values].sort(
    (left, right) => right.observation.value - left.observation.value,
  );
  const middle = median(values.map((item) => item.observation.value));
  const timestamps = values.map((item) => item.observation.ingested_at).sort();

  const exportCurrentView = () => {
    downloadCsv(
      `regional-${indicatorCode}-${endYear}.csv`,
      [
        { key: "region_code", label: "Kode wilayah" },
        { key: "region", label: "Wilayah" },
        { key: "period", label: "Periode" },
        { key: "value", label: "Nilai" },
        { key: "unit", label: "Satuan" },
        { key: "source", label: "Sumber" },
      ],
      sorted.map((item) => ({
        region_code: item.regionCode,
        region: item.regionName,
        period: item.observation.observation_date,
        value: item.observation.value,
        unit: item.observation.unit,
        source: item.observation.source_code,
      })),
    );
  };

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Regional analysis"
        title="Lihat kesenjangan antarwilayah"
        description="Bandingkan satu indikator pada periode yang sama di seluruh provinsi yang tersedia."
        actions={<ExportButton onClick={exportCurrentView} disabled={values.length === 0} />}
      />

      {provinces.length === 0 ? (
        <EmptyState
          title="Katalog provinsi belum tersedia"
          description="Jalankan pipeline BPS dengan API key yang valid agar wilayah provinsi dan observasinya masuk ke database."
        />
      ) : values.length === 0 ? (
        <EmptyState
          description={`Tidak ada data regional untuk indikator dan tahun ${endYear} ini. Pilih indikator BPS atau periode lain.`}
        />
      ) : (
        <>
          <div className="section-meta">
            <div className="source-pills">
              <span className="source-pill">{sourceName(first.source_code)}</span>
              <span className="source-pill source-pill-muted">{values.length} provinsi tercakup</span>
            </div>
            <UpdateStamp value={timestamps.at(-1)} />
          </div>

          <section className="metric-grid metric-grid-four">
            <MetricCard
              label="Wilayah tertinggi"
              value={formatValue(sorted[0].observation.value, first.unit)}
              period={`${sorted[0].regionName} · ${formatDate(sorted[0].observation.observation_date)}`}
              source={sourceName(sorted[0].observation.source_code)}
            />
            <MetricCard
              label="Median provinsi"
              value={formatValue(middle, first.unit)}
              period={`${values.length} provinsi`}
              source={sourceName(first.source_code)}
              tone="amber"
            />
            <MetricCard
              label="Wilayah terpilih"
              value={selected ? formatValue(selected.observation.value, first.unit) : "—"}
              period={selected?.regionName ?? "Pilih provinsi pada filter wilayah"}
              source={selected ? sourceName(selected.observation.source_code) : sourceName(first.source_code)}
              tone="violet"
            />
            <MetricCard
              label="Rentang nilai"
              value={formatValue(
                sorted[0].observation.value - sorted.at(-1)!.observation.value,
                first.unit,
              )}
              period={`${sorted.at(-1)!.regionName} hingga ${sorted[0].regionName}`}
              source={sourceName(first.source_code)}
              tone="blue"
            />
          </section>

          <section className="panel">
            <div className="panel-heading">
              <div>
                <span className="panel-kicker">Perbandingan provinsi</span>
                <h2>{first.indicator_name}</h2>
                <p>Tahun {endYear}; wilayah terpilih ditandai warna jingga.</p>
              </div>
              <span className="unit-chip"><BarChart3 size={14} /> {first.unit ?? "Tanpa satuan"}</span>
            </div>
            <ComparisonChart
              label={`Perbandingan regional ${first.indicator_name}`}
              unit={first.unit}
              selectedCode={regionCode}
              items={values.map((item) => ({
                code: item.regionCode,
                name: item.regionName,
                value: item.observation.value,
              }))}
            />
          </section>

          <section className="provenance-strip provenance-strip-amber">
            <MapPinned size={20} />
            <div>
              <strong>Peta belum ditampilkan</strong>
              <span>Visual tetap berupa perbandingan batang sampai kode wilayah dan geometri batas provinsi selesai divalidasi.</span>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
