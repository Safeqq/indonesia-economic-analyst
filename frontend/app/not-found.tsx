import Link from "next/link";

import { EmptyState } from "@/components/ui/data-state";

export default function NotFound() {
  return (
    <div className="not-found">
      <EmptyState
        title="Halaman tidak ditemukan"
        description="Alamat yang dibuka tidak termasuk ruang kerja analitik ini."
      />
      <Link className="button button-primary" href="/">Kembali ke overview</Link>
    </div>
  );
}
