"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, ArrowLeftRight, UserCheck, BarChart3, ShieldCheck } from "lucide-react";
import { cn } from "@/lib/utils";

const navigationItems = [
  {
    name: "Panel",
    href: "/",
    icon: LayoutDashboard,
  },
  {
    name: "Transacciones",
    href: "/transactions",
    icon: ArrowLeftRight,
  },
  {
    name: "Cola HITL",
    href: "/hitl",
    icon: UserCheck,
  },
  {
    name: "Políticas",
    href: "/policies",
    icon: ShieldCheck,
  },
  {
    name: "Analíticas",
    href: "/analytics",
    icon: BarChart3,
  },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside
      className="hidden lg:flex lg:flex-col lg:w-60 lg:fixed lg:inset-y-0 bg-slate-900 text-white border-r border-slate-800"
      aria-label="Main navigation"
    >
      {/* Logo and Title */}
      <div className="flex items-center gap-3 h-16 px-6 border-b border-slate-800">
        <span className="text-2xl">🛡️</span>
        <span className="font-semibold text-lg">FraudGuard</span>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {navigationItems.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                "hover:bg-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400",
                isActive
                  ? "bg-slate-800 text-white"
                  : "text-slate-300 hover:text-white"
              )}
              aria-current={isActive ? "page" : undefined}
            >
              <Icon className="h-5 w-5" aria-hidden="true" />
              <span>{item.name}</span>
            </Link>
          );
        })}
      </nav>

      {/* Footer (optional, can add version info later) */}
      <div className="px-6 py-4 border-t border-slate-800">
        <p className="text-xs text-slate-400">v1.0.0</p>
      </div>
    </aside>
  );
}
