"use client";

import Link from "next/link";
import { Bell, Menu, Moon, Sun, User } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/hooks/use-auth";
import { useUIStore } from "@/store/ui-store";
import { notificationsService } from "@/services/notifications";
import { cn } from "@/lib/utils";

export function Header() {
  const { user, logout } = useAuth();
  const { sidebarCollapsed, sidebarOpen, toggleSidebar, darkMode, toggleDarkMode } =
    useUIStore();

  const { data: notifications } = useQuery({
    queryKey: ["notifications", "unread"],
    queryFn: () => notificationsService.list({ limit: 5 }),
    staleTime: 60 * 1000,
    retry: false,
  });

  const unreadCount = notifications?.unread_count ?? 0;

  return (
    <header
      className={cn(
        "fixed top-0 right-0 z-30 flex h-16 items-center justify-between border-b border-border/60 bg-background/80 backdrop-blur-xl px-4 md:px-6 transition-all duration-300",
        sidebarOpen ? (sidebarCollapsed ? "left-16" : "left-64") : "left-0"
      )}
    >
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" onClick={toggleSidebar} className="md:hidden">
          <Menu className="h-5 w-5" />
        </Button>
        <div className="hidden md:block">
          <p className="text-xs uppercase tracking-widest text-muted-foreground">
            Operations Console
          </p>
          <p className="text-sm font-medium">
            Welcome back, {user?.full_name?.split(" ")[0] ?? "Operator"}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Button variant="ghost" size="icon" onClick={toggleDarkMode} aria-label="Toggle theme">
          {darkMode ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </Button>

        <Button variant="ghost" size="icon" className="relative" asChild>
          <Link href="/dashboard/settings">
            <Bell className="h-4 w-4" />
            {unreadCount > 0 && (
              <Badge
                variant="critical"
                className="absolute -right-1 -top-1 h-4 min-w-4 px-1 text-[10px] flex items-center justify-center"
              >
                {unreadCount > 9 ? "9+" : unreadCount}
              </Badge>
            )}
          </Link>
        </Button>

        <div className="hidden sm:flex items-center gap-2 pl-2 border-l border-border/60">
          <Link
            href="/dashboard/profile"
            className="flex items-center gap-2 rounded-md px-2 py-1 hover:bg-muted/50 transition-colors"
          >
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-cyan-accent/10 border border-cyan-accent/30">
              <User className="h-4 w-4 text-cyan-accent" />
            </div>
            <div className="text-left">
              <p className="text-sm font-medium leading-none">{user?.full_name}</p>
              <p className="text-xs text-muted-foreground capitalize">{user?.role}</p>
            </div>
          </Link>
          <Button variant="ghost" size="sm" onClick={() => logout()}>
            Sign out
          </Button>
        </div>
      </div>
    </header>
  );
}
