import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

import { AppShell } from "@/components/app-shell";
import { DashboardProvider } from "@/components/dashboard-provider";

import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "Indonesia Economic Intelligence",
    template: "%s | Indonesia Economic Intelligence",
  },
  description: "Dashboard indikator ekonomi Indonesia dari sumber publik resmi.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#081c24",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="id">
      <body>
        <DashboardProvider>
          <AppShell>{children}</AppShell>
        </DashboardProvider>
      </body>
    </html>
  );
}

