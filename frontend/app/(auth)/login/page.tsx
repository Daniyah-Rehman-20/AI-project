"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Shield, Zap, Activity } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { useAuth } from "@/hooks/use-auth";
import { useAuthStore } from "@/store/auth-store";
import { authService } from "@/services/auth";

const loginSchema = z.object({
  email: z.string().email("Enter a valid email address"),
  password: z.string().min(8, "Password must be at least 8 characters"),
});

type LoginForm = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const router = useRouter();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const { login, isLoggingIn, loginError } = useAuth();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  useEffect(() => {
    if (isAuthenticated) {
      router.replace("/dashboard");
    }
  }, [isAuthenticated, router]);

  const onSubmit = (data: LoginForm) => {
    login(data);
  };

  return (
    <div className="relative min-h-screen flex">
      <div className="fixed inset-0 bg-grid-pattern bg-grid opacity-[0.04] pointer-events-none" />
      <div className="fixed inset-0 bg-gradient-to-br from-steel-950 via-background to-steel-900 pointer-events-none" />

      {/* Hero panel */}
      <div className="hidden lg:flex lg:w-1/2 relative flex-col justify-center px-16">
        <div className="absolute inset-0 bg-gradient-to-r from-cyan-accent/5 to-transparent" />
        <div className="relative z-10 max-w-lg animate-fade-in">
          <div className="flex items-center gap-3 mb-8">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-cyan-accent/10 border border-cyan-accent/30 glow-cyan">
              <Shield className="h-6 w-6 text-cyan-accent" />
            </div>
            <div>
              <h1 className="text-3xl font-bold tracking-tight">AetherOps</h1>
              <p className="text-sm uppercase tracking-[0.2em] text-muted-foreground">
                IncidentIQ Platform
              </p>
            </div>
          </div>

          <h2 className="text-4xl font-bold leading-tight mb-4">
            Enterprise AI
            <br />
            <span className="text-gradient-cyan">Incident Intelligence</span>
          </h2>

          <p className="text-muted-foreground text-lg mb-10 leading-relaxed">
            Real-time incident correlation, AI-powered root cause analysis, and
            operational knowledge at the speed of your infrastructure.
          </p>

          <div className="space-y-4">
            <div className="flex items-center gap-3 text-sm text-muted-foreground">
              <Zap className="h-4 w-4 text-cyan-accent shrink-0" />
              <span>Sub-second semantic search across runbooks and postmortems</span>
            </div>
            <div className="flex items-center gap-3 text-sm text-muted-foreground">
              <Activity className="h-4 w-4 text-cyan-accent shrink-0" />
              <span>Automated triage with confidence-scored classifications</span>
            </div>
          </div>
        </div>
      </div>

      {/* Login form */}
      <div className="flex w-full lg:w-1/2 items-center justify-center p-6 md:p-12">
        <div className="w-full max-w-md animate-fade-in">
          <div className="lg:hidden mb-8 text-center">
            <h1 className="text-2xl font-bold">AetherOps</h1>
            <p className="text-sm text-muted-foreground">IncidentIQ Platform</p>
          </div>

          <div className="ops-panel p-8">
            <h2 className="text-xl font-semibold mb-1">Sign in</h2>
            <p className="text-sm text-muted-foreground mb-6">
              Access your operations command center
            </p>

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              <div>
                <label htmlFor="email" className="text-sm font-medium mb-1.5 block">
                  Email
                </label>
                <Input
                  id="email"
                  type="email"
                  placeholder="operator@company.com"
                  autoComplete="email"
                  {...register("email")}
                />
                {errors.email && (
                  <p className="text-xs text-red-400 mt-1">{errors.email.message}</p>
                )}
              </div>

              <div>
                <label htmlFor="password" className="text-sm font-medium mb-1.5 block">
                  Password
                </label>
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  autoComplete="current-password"
                  {...register("password")}
                />
                {errors.password && (
                  <p className="text-xs text-red-400 mt-1">{errors.password.message}</p>
                )}
              </div>

              {loginError && (
                <p className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-md px-3 py-2">
                  Invalid credentials. Please try again.
                </p>
              )}

              <Button type="submit" className="w-full" disabled={isLoggingIn}>
                {isLoggingIn ? <Spinner size="sm" /> : "Sign in"}
              </Button>
            </form>

            <div className="mt-6 pt-6 border-t border-border/60">
              <Button
                variant="outline"
                className="w-full"
                onClick={() => window.location.assign(authService.getGoogleOAuthUrl())}
              >
                Continue with Google
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
