"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/cn";
import { DateSwitcher } from "@/components/layout/DateSwitcher";

const LINKS = [
  { href: "/", label: "Home" },
  { href: "/explore", label: "Explore" },
  { href: "/share", label: "Share" },
  { href: "/live", label: "Live" },
  { href: "/debug", label: "Debug" },
] as const;

export function Navbar() {
  const pathname = usePathname();
  const isHome = pathname === "/";

  return (
    <header
      className={cn(
        "fixed inset-x-0 top-0 z-50 min-h-20",
        isHome
          ? "border-b border-white/5 bg-bg/35 backdrop-blur-xl"
          : "border-b border-line bg-bg/80 backdrop-blur-md",
      )}
    >
      <nav className="mx-auto flex min-h-20 max-w-[1500px] flex-wrap items-center justify-between gap-x-8 gap-y-4 px-6 py-5 md:px-12">
        <Link
          href="/"
          className="font-serif text-[1.6rem] tracking-[0.12em] text-fg"
        >
          MemoryPalace
        </Link>
        <div className="flex flex-wrap items-center justify-end gap-4 md:gap-7">
          <ul className="flex items-center gap-5 sm:gap-8 md:gap-10">
            {LINKS.map((link) => {
            const active =
              link.href === "/"
                ? pathname === "/"
                : pathname.startsWith(link.href);
            return (
              <li key={link.href}>
                <Link
                  href={link.href}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "relative py-2 text-sm transition-colors",
                    active ? "text-fg" : "text-fg-dim hover:text-fg",
                  )}
                >
                  {link.label}
                  {active ? (
                    <span className="absolute -bottom-2 left-0 h-px w-full bg-accent" />
                  ) : null}
                </Link>
              </li>
            );
            })}
          </ul>
          <DateSwitcher />
        </div>
      </nav>
    </header>
  );
}
