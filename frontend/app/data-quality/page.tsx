"use client";

import { Activity, CircleCheck, CircleX, Info, ServerCog } from "lucide-react";

import { EmptyState, ErrorState, LoadingState } from "@/components/ui/data-state";
import { ExportButton } from "@/components/ui/export-button";
import { MetricCard } from "@/components/ui/metric-card";
import { PageHeader } from "@/components/ui/page-header";
import { UpdateStamp } from "@/components/ui/update-stamp";
import { getDataQuality, getPipelineRuns } from "@/lib/api";
import { downloadCsv } from "@/lib/csv";
import {
  formatDateTime,
  formatNumber,
  qualityCheckName,
  sourceName,
} from "@/lib/format";
import { useApiQuery } from "@/lib/use-api-query";

export default function DataQualityCenterPage() {
  const query = useApiQuery("data-quality-center", async (signal) => {
    const [quality, runs] = await Promise.all([
      getDataQuality(signal),
      getPipelineRuns(signal),
    ]);
    return { quality, runs };
  });

  if (query.isLoading) return <LoadingState label="Menjalankan ringkasan kualitas…" />;
  if (query.error) return <ErrorState error={query.error} onRetry={query.retry} />;
  if (!query.data) return <EmptyState description="Status operasional belum tersedia." />;

  const { quality, runs } = query.data;
  const blockingChecks = quality.checks.filter((check) => check.blocking);
  const passedBlocking = blockingChecks.filter((check) => check.status === "passed").length;
  const successfulRuns = runs.items.filter((run) => run.status === "success").length;
  const latestTimestamp = runs.items
    .flatMap((run) => [run.completed_at, run.started_at])
    .filter((value): value is string => Boolean(value))
    .sort()
    .at(-1);

  const exportChecks = () => {
    downloadCsv(
      "data-quality-checks.csv",
      [
        { key: "check", label: "Pemeriksaan" },
        { key: "blocking", label: "Blocking" },
        { key: "status", label: "Status" },
        { key: "findings", label: "Jumlah temuan" },
      ],
      quality.checks.map((check) => ({
        check: check.name,
        blocking: check.blocking,
        status: check.status,
        findings: check.finding_count,
      })),
    );
  };

  const exportRuns = () => {
    downloadCsv(
      "pipeline-runs.csv",
      [
        { key: "run_id", label: "Run ID" },
        { key: "source", label: "Sumber" },
        { key: "started_at", label: "Mulai" },
        { key: "completed_at", label: "Selesai" },
        { key: "status", label: "Status" },
        { key: "rows_loaded", label: "Baris dimuat" },
        { key: "has_error", label: "Memiliki error" },
      ],
      runs.items.map((run) => ({
        run_id: run.run_id,
        source: run.source_code,
        started_at: run.started_at,
        completed_at: run.completed_at,
        status: run.status,
        rows_loaded: run.rows_loaded,
        has_error: run.has_error,
      })),
    );
  };

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Data quality center"
        title="Kepercayaan data yang terlihat"
        description="Pantau pemeriksaan blocking, temuan informasional, dan hasil run pipeline terbaru."
        actions={<ExportButton onClick={exportChecks} label="Export checks" />}
      />

      <div className="section-meta">
        <div className="source-pills">
          <span className={quality.status === "healthy" ? "status-badge status-success" : "status-badge status-danger"}>
            {quality.status === "healthy" ? <CircleCheck size={14} /> : <CircleX size={14} />}
            {quality.status === "healthy" ? "Semua blocking check lulus" : "Perlu perhatian"}
          </span>
        </div>
        <UpdateStamp value={latestTimestamp} />
      </div>

      <section className="metric-grid metric-grid-four">
        <MetricCard
          label="Blocking check lulus"
          value={`${passedBlocking}/${blockingChecks.length}`}
          period={quality.status === "healthy" ? "Status sehat" : "Ada kegagalan"}
          source="SQL quality suite"
        />
        <MetricCard
          label="Blocking failures"
          value={formatNumber(quality.blocking_failures)}
          period="Harus nol untuk status sehat"
          source="SQL quality suite"
          tone="amber"
        />
        <MetricCard
          label="Temuan informasional"
          value={formatNumber(quality.informational_findings)}
          period="Tidak memblokir publikasi"
          source="Freshness & coverage"
          tone="violet"
        />
        <MetricCard
          label="Run berhasil"
          value={`${successfulRuns}/${runs.items.length}`}
          period="Riwayat yang sedang dilihat"
          source="fact_pipeline_run"
          tone="blue"
        />
      </section>

      <section className="content-grid content-grid-balanced quality-layout">
        <article className="panel">
          <div className="panel-heading">
            <div>
              <span className="panel-kicker">Quality checks</span>
              <h2>Hasil pemeriksaan</h2>
            </div>
            <Activity size={20} />
          </div>
          {quality.checks.length === 0 ? (
            <EmptyState description="Belum ada pemeriksaan kualitas yang terdaftar." />
          ) : (
            <div className="quality-check-list">
              {quality.checks.map((check) => (
                <div className="quality-check" key={check.name}>
                  <div className={`quality-icon quality-${check.status}`}>
                    {check.status === "passed" ? (
                      <CircleCheck size={18} />
                    ) : check.status === "failed" ? (
                      <CircleX size={18} />
                    ) : (
                      <Info size={18} />
                    )}
                  </div>
                  <div>
                    <strong>{qualityCheckName(check.name)}</strong>
                    <span>{check.blocking ? "Blocking" : "Informasional"}</span>
                  </div>
                  <b>{check.finding_count} temuan</b>
                </div>
              ))}
            </div>
          )}
        </article>

        <article className="panel">
          <div className="panel-heading">
            <div>
              <span className="panel-kicker">Pipeline activity</span>
              <h2>Run terbaru</h2>
            </div>
            <ExportButton onClick={exportRuns} label="Export runs" disabled={runs.items.length === 0} />
          </div>
          {runs.items.length === 0 ? (
            <EmptyState description="Belum ada run pipeline yang tercatat." />
          ) : (
            <div className="pipeline-list">
              {runs.items.slice(0, 12).map((run) => (
                <div className="pipeline-row" key={run.run_id}>
                  <div className="run-mark"><ServerCog size={17} /></div>
                  <div>
                    <strong>{sourceName(run.source_code)}</strong>
                    <span>{formatDateTime(run.started_at)}</span>
                  </div>
                  <div className="run-result">
                    <span className={`status-dot status-${run.status}`}>{run.status}</span>
                    <small>{formatNumber(run.rows_loaded)} baris</small>
                  </div>
                </div>
              ))}
            </div>
          )}
        </article>
      </section>
    </div>
  );
}
