"use client";

import { format } from "date-fns";
import { User, Mail, Shield, Calendar } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/hooks/use-auth";
import { PageLoader } from "@/components/ui/spinner";

export default function ProfilePage() {
  const { user, isLoading } = useAuth();

  if (isLoading || !user) return <PageLoader />;

  return (
    <div className="space-y-6 animate-fade-in max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold">Profile</h1>
        <p className="text-muted-foreground text-sm mt-1">Your account information</p>
      </div>

      <div className="ops-panel p-6">
        <div className="flex items-center gap-4 mb-6">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-cyan-accent/10 border-2 border-cyan-accent/30">
            <User className="h-8 w-8 text-cyan-accent" />
          </div>
          <div>
            <h2 className="text-xl font-semibold">{user.full_name}</h2>
            <Badge variant="info" className="capitalize mt-1">
              {user.role}
            </Badge>
          </div>
        </div>

        <div className="space-y-4">
          <div className="flex items-center gap-3 text-sm">
            <Mail className="h-4 w-4 text-muted-foreground" />
            <span className="text-muted-foreground w-24">Email</span>
            <span>{user.email}</span>
          </div>
          <div className="flex items-center gap-3 text-sm">
            <Shield className="h-4 w-4 text-muted-foreground" />
            <span className="text-muted-foreground w-24">Status</span>
            <span>
              {user.is_active ? (
                <Badge variant="success">Active</Badge>
              ) : (
                <Badge variant="critical">Inactive</Badge>
              )}
              {user.is_verified && (
                <Badge variant="outline" className="ml-2">
                  Verified
                </Badge>
              )}
            </span>
          </div>
          <div className="flex items-center gap-3 text-sm">
            <Calendar className="h-4 w-4 text-muted-foreground" />
            <span className="text-muted-foreground w-24">Joined</span>
            <span>{format(new Date(user.created_at), "PPP")}</span>
          </div>
          {user.last_login_at && (
            <div className="flex items-center gap-3 text-sm">
              <Calendar className="h-4 w-4 text-muted-foreground" />
              <span className="text-muted-foreground w-24">Last login</span>
              <span>{format(new Date(user.last_login_at), "PPp")}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
