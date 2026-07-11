"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth";
import BrandMark from "@/components/BrandMark";

const NAV_LINKS = [
  { href: "/", label: "Projects" },
  { href: "/team", label: "Team" },
] as const;

export default function AppShell({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const pathname = usePathname();

  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-40 border-b border-line bg-white/90 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-6">
          <Link href="/" className="flex items-center gap-2.5">
            <BrandMark size={40} />
            <span className="flex items-baseline gap-3">
              <span className="font-display text-2xl font-semibold tracking-tight">
                <span className="text-forest">Labora</span>
                <span className="text-leaf">tree</span>
              </span>
              <span className="hidden text-[11px] font-medium uppercase tracking-[0.25em] text-leaf sm:inline">
                Grow · Innovate · Impact
              </span>
            </span>
          </Link>
          {user ? (
            <div className="flex items-center gap-1.5 text-sm">
              {NAV_LINKS.map((l) => {
                const active =
                  l.href === "/" ? pathname === "/" || pathname.startsWith("/projects") : pathname.startsWith(l.href);
                return (
                  <Link
                    key={l.href}
                    href={l.href}
                    className={`rounded-full px-3 py-1.5 font-medium transition ${
                      active
                        ? "bg-forest text-white"
                        : "text-forest hover:bg-leaf/10"
                    }`}
                  >
                    {l.label}
                  </Link>
                );
              })}
              <span className="mx-2 hidden h-5 w-px bg-line md:inline-block" />
              <span className="hidden items-center gap-2 md:flex">
                <span className="flex h-7 w-7 items-center justify-center rounded-full bg-forest text-[11px] font-bold text-white">
                  {(user.email[0] ?? "?").toUpperCase()}
                </span>
                <span className="rounded-full bg-sprout/30 px-2 py-0.5 text-xs font-medium text-forest">
                  {user.role}
                </span>
              </span>
              <button
                onClick={logout}
                className="ml-2 rounded-full border border-line px-3 py-1.5 text-forest transition hover:bg-bg"
              >
                Sign out
              </button>
            </div>
          ) : null}
        </div>
      </header>
      <main className="mx-auto w-full max-w-7xl flex-1 px-6 py-8">{children}</main>
      <footer className="border-t border-line py-4 text-center text-xs text-muted">
        <span className="font-display text-forest">Laboratree</span> · provenance-locked research,
        end to end · v0.1
      </footer>
    </div>
  );
}
