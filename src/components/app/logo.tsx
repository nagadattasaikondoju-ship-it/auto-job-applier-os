import Link from "next/link";
import { cn } from "@/lib/utils";

export function AppLogo({ className, href = "/dashboard" }: { className?: string; href?: string }) {
  return (
    <Link
      href={href}
      aria-label="Applyon home"
      className={cn(
        "inline-flex items-center gap-2 rounded-app-md text-app-ink outline-none focus-visible:ring-2 focus-visible:ring-app-accent",
        className
      )}
    >
      <span className="size-7 rounded-app-md bg-app-ink text-app-card flex items-center justify-center text-sm font-bold">
        A
      </span>
      <span className="text-base font-medium tracking-tight">Applyon</span>
    </Link>
  );
}
