"use client";

import { usePathname } from "next/navigation";
import { Plus } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { MobileSidebar } from "./MobileSidebar";
import { useSystemHealth } from "@/hooks/useSystemHealth";

const BREADCRUMBS: Record<string, string> = {
  "/": "Dashboard",
  "/transactions": "Transactions",
  "/hitl": "Human Review Queue",
  "/analytics": "Analytics & Reports",
};

export function Header() {
  const pathname = usePathname();
  const { isOnline } = useSystemHealth(30000);

  // Get breadcrumb title for current path
  const breadcrumb = BREADCRUMBS[pathname] || "Dashboard";

  return (
    <header className="sticky top-0 z-40 border-b backdrop-blur bg-background/95 supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-16 items-center gap-4 px-6">
        {/* Mobile Menu (visible only on mobile) */}
        <MobileSidebar />

        {/* Breadcrumb Title */}
        <h2 className="text-lg font-semibold">{breadcrumb}</h2>

        {/* Spacer */}
        <div className="flex-1" />

        {/* System Status Badge */}
        <Badge
          variant={isOnline ? "default" : "destructive"}
          className="gap-1.5"
        >
          <span className="relative flex h-2 w-2">
            {isOnline && (
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75" />
            )}
            <span
              className={`relative inline-flex h-2 w-2 rounded-full ${
                isOnline ? "bg-green-500" : "bg-red-500"
              }`}
            />
          </span>
          <span>{isOnline ? "Online" : "Offline"}</span>
        </Badge>

        {/* Analyze New Button */}
        <Button
          size="sm"
          className="gap-2"
          onClick={() => alert("Analyze New Transaction modal - Coming soon!")}
        >
          <Plus className="h-4 w-4" />
          <span className="hidden sm:inline">Analyze New</span>
        </Button>
      </div>
    </header>
  );
}
