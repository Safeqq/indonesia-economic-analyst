"use client";

import {
  Activity,
  BarChart3,
  Boxes,
  ChartNoAxesCombined,
  Gauge,
  Landmark,
  Menu,
  SearchCode,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, type ReactNode } from "react";

import { GlobalFilters } from "@/components/global-filters";

const navigation = [
  { href: "/", label: "Executive Overview", icon: Gauge },
  { href: "/trends", label: "Trend Explorer", icon: ChartNoAxesCombined },
  { href: "/regional", label: "Regional Analysis", icon: MapIcon },
  { href: "/asean", label: "ASEAN Benchmark", icon: Landmark },
  { href: "/drivers", label: "Correlation & Drivers", icon: Boxes },
  { href: "/forecasting", label: "Forecasting Lab", icon: Sparkles },
  { href: "/data-quality", label: "Data Quality Center", icon: ShieldCheck },
];

function MapIcon({ size = 19 }: { size?: number }) {
  return <BarChart3 size={size} />;
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="app-shell">
      <aside className={`sidebar ${menuOpen ? "sidebar-open" : ""}`}>
        <div className="brand">
          <div className="brand-mark"><Activity size={22} /></div>
          <div>
            <strong>Indonesia</strong>
            <span>Economic Intelligence</span>
          </div>
          <button
            className="icon-button sidebar-close"
            type="button"
            aria-label="Tutup navigasi"
            onClick={() => setMenuOpen(false)}
          >
            <X size={20} />
          </button>
        </div>

        <nav className="main-nav" aria-label="Navigasi utama">
          <span className="nav-label">Workspace</span>
          {navigation.map(({ href, label, icon: Icon }) => {
            const active = href === "/" ? pathname === href : pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                className={active ? "nav-link nav-link-active" : "nav-link"}
                aria-current={active ? "page" : undefined}
                onClick={() => setMenuOpen(false)}
              >
                <Icon size={19} />
                <span>{label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="sidebar-note">
          <SearchCode size={17} />
          <div>
            <strong>Data dapat dilacak</strong>
            <span>Setiap angka membawa sumber dan periode.</span>
          </div>
        </div>
      </aside>

      {menuOpen && (
        <button
          className="sidebar-backdrop"
          type="button"
          aria-label="Tutup navigasi"
          onClick={() => setMenuOpen(false)}
        />
      )}

      <div className="workspace">
        <header className="topbar">
          <button
            className="icon-button mobile-menu"
            type="button"
            aria-label="Buka navigasi"
            onClick={() => setMenuOpen(true)}
          >
            <Menu size={21} />
          </button>
          <div className="topbar-title">
            <span className="eyebrow">Indonesia</span>
            <strong>Economic Intelligence</strong>
          </div>
          <div className="live-status" title="Dashboard mengambil data dari API">
            <span /> Data API
          </div>
        </header>
        <GlobalFilters />
        <main className="page-content">{children}</main>
      </div>
    </div>
  );
}
