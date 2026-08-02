"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  AlertTriangle,
  FileText,
  BookOpen,
  BarChart3,
  Settings,
  Users,
  Cpu,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  Search,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useUIStore } from "@/store/ui-store";

const navItems = [
  { href: "/dashboard", label: "Command Center", icon: LayoutDashboard },
  { href: "/dashboard/incidents", label: "Incidents", icon: AlertTriangle },
  { href: "/dashboard/documents", label: "Documents", icon: FileText },
  { href: "/dashboard/knowledge", label: "Knowledge", icon: Search },
  { href: "/dashboard/reports", label: "Reports", icon: ClipboardList },
  { href: "/dashboard/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/dashboard/ai-usage", label: "AI Usage", icon: Cpu },
  { href: "/dashboard/admin", label: "Admin", icon: Users },
  { href: "/dashboard/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const { sidebarCollapsed, toggleSidebarCollapsed, sidebarOpen } = useUIStore();

  if (!sidebarOpen) return null;

  return (
    <aside
      className={cn(
        "fixed left-0 top-0 z-40 flex h-screen flex-col border-r border-border/60 bg-steel-950/95 backdrop-blur-xl transition-all duration-300",
        sidebarCollapsed ? "w-16" : "w-64"
      )}
    >
      <div className="flex h-16 items-center gap-3 border-b border-border/60 px-4">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-cyan-accent/10 border border-cyan-accent/30">
          <BookOpen className="h-4 w-4 text-cyan-accent" />
        </div>
        {!sidebarCollapsed && (
          <div className="overflow-hidden">
            <p className="text-sm font-bold tracking-tight text-foreground">AetherOps</p>
            <p className="text-[10px] uppercase tracking-widest text-muted-foreground">
              IncidentIQ
            </p>
          </div>
        )}
      </div>

      <nav className="flex-1 overflow-y-auto py-4 px-2 space-y-1">
        {navItems.map((item) => {
          const isActive =
            pathname === item.href ||
            (item.href !== "/dashboard" && pathname.startsWith(item.href));
          const Icon = item.icon;

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-all duration-200",
                isActive
                  ? "bg-cyan-accent/10 text-cyan-accent border border-cyan-accent/20"
                  : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
              )}
              title={sidebarCollapsed ? item.label : undefined}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {!sidebarCollapsed && <span>{item.label}</span>}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-border/60 p-2">
        <button
          onClick={toggleSidebarCollapsed}
          className="flex w-full items-center justify-center rounded-md p-2 text-muted-foreground hover:bg-muted/50 hover:text-foreground transition-colors"
          aria-label={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {sidebarCollapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
        </button>
      </div>
    </aside>
  );
}
