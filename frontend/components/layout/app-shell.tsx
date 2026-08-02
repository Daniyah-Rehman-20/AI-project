"use client";

import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { useUIStore } from "@/store/ui-store";
import { cn } from "@/lib/utils";

interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const { sidebarCollapsed, sidebarOpen } = useUIStore();

  return (
    <div className="min-h-screen bg-background">
      <div className="fixed inset-0 bg-grid-pattern bg-grid opacity-[0.03] pointer-events-none" />
      <div className="fixed inset-0 bg-gradient-to-br from-cyan-accent/5 via-transparent to-steel-900/20 pointer-events-none" />

      <Sidebar />
      <Header />

      <main
        className={cn(
          "relative min-h-screen pt-16 transition-all duration-300",
          sidebarOpen ? (sidebarCollapsed ? "pl-16" : "pl-64") : "pl-0"
        )}
      >
        <div className="p-4 md:p-6 lg:p-8">{children}</div>
      </main>
    </div>
  );
}
