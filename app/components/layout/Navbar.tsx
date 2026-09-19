"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/cn";

const LINKS = [
  { href: "/", label: "Home" },
  { href: "/explore", label: "Explore" },
  { href: "/live", label: "Live" },
  { href: "/debug", label: "Debug" },
] as const;

export function Navbar() {
  const pathname = usePathname();
  const isHome = pathname === "/";

  return (
    <header
      className={cn(
        "fixed inset-x-0 top-0 z-50 h-16",
        isHome
          ? "bg-gradient-to-b from-black/55 to-transparent"
          : "border-b border-line bg-bg/80 backdrop-blur-md",
      )}
    >
      <nav className="mx-auto flex h-full max-w-[1500px] items-center justify-between px-5 md:px-8">
        <Link
          href="/"
          className="font-serif text-[1.35rem] tracking-[0.14em] text-fg"
        >
          MEMORYPALACE
        </Link>
        <ul className="flex items-center gap-7 md:gap-10">
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
                    "relative text-[11px] tracking-[0.16em] uppercase transition-colors",
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
      </nav>
    </header>
  );
}
