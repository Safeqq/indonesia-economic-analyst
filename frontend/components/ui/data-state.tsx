import { AlertTriangle, Inbox, RefreshCw } from "lucide-react";

export function LoadingState({ label = "Memuat data resmi…" }: { label?: string }) {
  return (
    <div className="state-card state-loading" role="status">
      <div className="loading-orbit" aria-hidden="true"><span /></div>
      <strong>{label}</strong>
      <p>Dashboard sedang meminta data terbaru dari API.</p>
      <div className="skeleton-lines" aria-hidden="true"><i /><i /><i /></div>
    </div>
  );
}

export function EmptyState({
  title = "Data belum tersedia",
  description,
}: {
  title?: string;
  description: string;
}) {
  return (
    <div className="state-card" role="status">
      <div className="state-icon"><Inbox size={24} /></div>
      <strong>{title}</strong>
      <p>{description}</p>
    </div>
  );
}

export function ErrorState({
  error,
  onRetry,
}: {
  error: Error;
  onRetry: () => void;
}) {
  return (
    <div className="state-card state-error" role="alert">
      <div className="state-icon"><AlertTriangle size={24} /></div>
      <strong>Data gagal dimuat</strong>
      <p>{error.message}</p>
      <button className="button button-secondary" type="button" onClick={onRetry}>
        <RefreshCw size={15} /> Coba lagi
      </button>
    </div>
  );
}

