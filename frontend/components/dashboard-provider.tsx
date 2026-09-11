"use client";

import {
  createContext,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { getIndicators, getRegions } from "@/lib/api";
import type { IndicatorSummary, RegionSummary } from "@/lib/types";
import { useApiQuery } from "@/lib/use-api-query";

interface DashboardContextValue {
  indicators: IndicatorSummary[];
  regions: RegionSummary[];
  countries: RegionSummary[];
  indicatorCode: string;
  regionCode: string;
  countryCode: string;
  startYear: number;
  endYear: number;
  setIndicatorCode: (value: string) => void;
  setRegionCode: (value: string) => void;
  setCountryCode: (value: string) => void;
  setStartYear: (value: number) => void;
  setEndYear: (value: number) => void;
  isCatalogLoading: boolean;
  catalogError: Error | null;
  retryCatalog: () => void;
}

const DashboardContext = createContext<DashboardContextValue | null>(null);

function yearFromDate(value: string | null, fallback: number): number {
  if (!value) return fallback;
  const year = Number(value.slice(0, 4));
  return Number.isFinite(year) ? year : fallback;
}

export function DashboardProvider({ children }: { children: ReactNode }) {
  const currentYear = new Date().getFullYear();
  const catalog = useApiQuery(
    "dashboard-catalog",
    async (signal) => {
      const [indicators, regions] = await Promise.all([
        getIndicators(signal),
        getRegions(signal),
      ]);
      return { indicators, regions };
    },
  );
  const [selectedIndicator, setSelectedIndicator] = useState("");
  const [selectedRegion, setSelectedRegion] = useState("IDN");
  const [selectedCountry, setSelectedCountry] = useState("IDN");
  const [periodOverride, setPeriodOverride] = useState<{
    start: number;
    end: number;
  } | null>(null);

  const indicators = useMemo(
    () => catalog.data?.indicators.filter((item) => item.observation_count > 0) ?? [],
    [catalog.data],
  );
  const regions = useMemo(
    () => catalog.data?.regions ?? [],
    [catalog.data],
  );
  const countries = useMemo(
    () => regions.filter((item) => item.region_level === "country"),
    [regions],
  );
  const defaultIndicator =
    indicators.find(
      (item) => item.source_codes.includes("world_bank") && item.region_count > 1,
    ) ?? indicators[0];
  const indicatorCode = indicators.some(
    (item) => item.indicator_code === selectedIndicator,
  )
    ? selectedIndicator
    : (defaultIndicator?.indicator_code ?? "");
  const activeIndicator = indicators.find(
    (item) => item.indicator_code === indicatorCode,
  );
  const availableStart = yearFromDate(activeIndicator?.period_start ?? null, currentYear - 10);
  const availableEnd = yearFromDate(activeIndicator?.period_end ?? null, currentYear);
  const defaultPeriod = {
    start: Math.max(availableStart, availableEnd - 10),
    end: availableEnd,
  };
  const startYear = periodOverride?.start ?? defaultPeriod.start;
  const endYear = periodOverride?.end ?? defaultPeriod.end;
  const regionCode = regions.some((item) => item.region_code === selectedRegion)
    ? selectedRegion
    : (regions.find((item) => item.region_code === "IDN")?.region_code ??
      regions[0]?.region_code ??
      "IDN");
  const countryCode = countries.some(
    (item) => item.region_code === selectedCountry,
  )
    ? selectedCountry
    : (countries.find((item) => item.region_code === "IDN")?.region_code ??
      countries[0]?.region_code ??
      "IDN");

  const value: DashboardContextValue = {
    indicators,
    regions,
    countries,
    indicatorCode,
    regionCode,
    countryCode,
    startYear,
    endYear,
    setIndicatorCode: (nextCode) => {
      setSelectedIndicator(nextCode);
      setPeriodOverride(null);
    },
    setRegionCode: setSelectedRegion,
    setCountryCode: (nextCode) => {
      setSelectedCountry(nextCode);
      setSelectedRegion(nextCode);
    },
    setStartYear: (year) =>
      setPeriodOverride({ start: Math.min(year, endYear), end: endYear }),
    setEndYear: (year) =>
      setPeriodOverride({ start: Math.min(startYear, year), end: year }),
    isCatalogLoading: catalog.isLoading,
    catalogError: catalog.error,
    retryCatalog: catalog.retry,
  };

  return <DashboardContext.Provider value={value}>{children}</DashboardContext.Provider>;
}

export function useDashboard(): DashboardContextValue {
  const context = useContext(DashboardContext);
  if (!context) throw new Error("useDashboard harus digunakan di DashboardProvider");
  return context;
}
