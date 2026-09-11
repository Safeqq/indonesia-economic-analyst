import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { EmptyState, ErrorState, LoadingState } from "@/components/ui/data-state";

afterEach(cleanup);

describe("status data dashboard", () => {
  it("mengumumkan loading dan empty state kepada pembaca layar", () => {
    const { rerender } = render(<LoadingState label="Memuat indikator…" />);
    expect(screen.getByRole("status")).toHaveTextContent("Memuat indikator…");

    rerender(<EmptyState description="Tidak ada observasi." />);
    expect(screen.getByRole("status")).toHaveTextContent("Tidak ada observasi.");
  });

  it("menampilkan pesan error dan menjalankan retry", () => {
    const retry = vi.fn();
    render(<ErrorState error={new Error("API tidak tersedia")} onRetry={retry} />);

    expect(screen.getByRole("alert")).toHaveTextContent("API tidak tersedia");
    fireEvent.click(screen.getByRole("button", { name: "Coba lagi" }));
    expect(retry).toHaveBeenCalledOnce();
  });
});
