"use client";

import { useQuery } from "@tanstack/react-query";
import { formatDistanceToNow } from "date-fns";
import { Bell, Moon, Sun, Shield } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import { useUIStore } from "@/store/ui-store";
import { useAuth } from "@/hooks/use-auth";
import { notificationsService } from "@/services/notifications";

export default function SettingsPage() {
  const { darkMode, toggleDarkMode } = useUIStore();
  const { user } = useAuth();

  const { data: notifications, isLoading } = useQuery({
    queryKey: ["notifications"],
    queryFn: () => notificationsService.list({ limit: 20 }),
    retry: false,
  });

  return (
    <div className="space-y-6 animate-fade-in max-w-3xl">
      <div>
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Platform preferences and notification history
        </p>
      </div>

      <div className="ops-panel p-6 space-y-6">
        <div>
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            <Shield className="h-4 w-4 text-cyan-accent" />
            Appearance
          </h3>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">Theme</p>
              <p className="text-xs text-muted-foreground">
                {darkMode ? "Dark industrial mode" : "Light mode"}
              </p>
            </div>
            <Button variant="outline" onClick={toggleDarkMode}>
              {darkMode ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
              {darkMode ? "Light" : "Dark"}
            </Button>
          </div>
        </div>

        <div className="border-t border-border/60 pt-6">
          <h3 className="font-semibold mb-2">Account</h3>
          <div className="text-sm space-y-1">
            <p>
              <span className="text-muted-foreground">Email:</span> {user?.email}
            </p>
            <p>
              <span className="text-muted-foreground">Role:</span>{" "}
              <span className="capitalize">{user?.role}</span>
            </p>
          </div>
        </div>
      </div>

      <div className="ops-panel">
        <div className="flex items-center gap-2 p-5 border-b border-border/60">
          <Bell className="h-4 w-4 text-cyan-accent" />
          <h3 className="font-semibold">Notifications</h3>
          {notifications?.unread_count ? (
            <Badge variant="info" className="ml-auto">
              {notifications.unread_count} unread
            </Badge>
          ) : null}
        </div>
        <div className="divide-y divide-border/40">
          {isLoading ? (
            <div className="flex justify-center py-8">
              <Spinner />
            </div>
          ) : (notifications?.items ?? []).length === 0 ? (
            <p className="p-5 text-sm text-muted-foreground">No notifications</p>
          ) : (
            notifications?.items.map((n) => (
              <div key={n.id} className="p-4">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="text-sm font-medium">{n.subject}</p>
                    <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">{n.body}</p>
                  </div>
                  <Badge variant={n.status === "read" ? "outline" : "info"}>{n.status}</Badge>
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  {formatDistanceToNow(new Date(n.created_at), { addSuffix: true })} · {n.channel}
                </p>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
