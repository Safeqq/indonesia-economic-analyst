"use client";

import { CalendarRange, Database, Globe2, MapPin } from "lucide-react";

import { useDashboard } from "@/components/dashboard-provider";

export function GlobalFilters() {
  const {
    indicators,
    regions,
    countries,
    indicatorCode,
    regionCode,
    countryCode,
    startYear,
    endYear,
    setIndicatorCode,
    setRegionCode,
    setCountryCode,
    setStartYear,
    setEndYear,
    isCatalogLoading,
    catalogError,
    retryCatalog,
  } = useDashboard();

  return (
    <section className="filter-panel" aria-label="Filter global dashboard">
      <div className="filter-grid">
        <label className="filter-field filter-field-wide">
          <span><Database size={14} /> Indikator</span>
          <select
            value={indicatorCode}
            onChange={(event) => setIndicatorCode(event.target.value)}
            disabled={isCatalogLoading || indicators.length === 0}
          >
            {isCatalogLoading && <option value="">Memuat indikator…</option>}
            {!isCatalogLoading && indicators.length === 0 && (
              <option value="">Belum ada indikator</option>
            )}
            {indicators.map((item) => (
              <option key={item.indicator_code} value={item.indicator_code}>
                {item.indicator_name}
              </option>
            ))}
          </select>
        </label>

        <label className="filter-field">
          <span><MapPin size={14} /> Wilayah</span>
          <select
            value={regionCode}
            onChange={(event) => setRegionCode(event.target.value)}
            disabled={isCatalogLoading || regions.length === 0}
          >
            {regions.map((item) => (
              <option key={item.region_code} value={item.region_code}>
                {item.region_name}
              </option>
            ))}
          </select>
        </label>

        <label className="filter-field">
          <span><Globe2 size={14} /> Negara</span>
          <select
            value={countryCode}
            onChange={(event) => setCountryCode(event.target.value)}
            disabled={isCatalogLoading || countries.length === 0}
          >
            {countries.map((item) => (
              <option key={item.region_code} value={item.region_code}>
                {item.region_name}
              </option>
            ))}
          </select>
        </label>

        <div className="filter-field filter-period">
          <span><CalendarRange size={14} /> Periode</span>
          <div>
            <input
              aria-label="Tahun mulai"
              type="number"
              min={1900}
              max={endYear}
              value={startYear}
              onChange={(event) => {
                const year = Number(event.target.value);
                if (Number.isInteger(year) && year >= 1900 && year <= endYear) {
                  setStartYear(year);
                }
              }}
            />
            <span aria-hidden="true">—</span>
            <input
              aria-label="Tahun akhir"
              type="number"
              min={startYear}
              max={new Date().getFullYear()}
              value={endYear}
              onChange={(event) => {
                const year = Number(event.target.value);
                if (
                  Number.isInteger(year) &&
                  year >= startYear &&
                  year <= new Date().getFullYear()
                ) {
                  setEndYear(year);
                }
              }}
            />
          </div>
        </div>
      </div>
      {catalogError && (
        <div className="filter-error" role="alert">
          Katalog filter gagal dimuat.
          <button type="button" onClick={retryCatalog}>Coba lagi</button>
        </div>
      )}
    </section>
  );
}
