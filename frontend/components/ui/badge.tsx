import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary text-primary-foreground shadow",
        secondary: "border-transparent bg-secondary text-secondary-foreground",
        destructive: "border-transparent bg-destructive text-destructive-foreground",
        outline: "text-foreground border-border",
        success: "border-transparent bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
        warning: "border-transparent bg-amber-500/15 text-amber-400 border-amber-500/30",
        critical: "border-transparent bg-red-500/15 text-red-400 border-red-500/30",
        info: "border-transparent bg-cyan-accent/15 text-cyan-accent border-cyan-accent/30",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };

export function severityBadgeVariant(
  severity: string
): VariantProps<typeof badgeVariants>["variant"] {
  switch (severity) {
    case "critical":
      return "critical";
    case "high":
      return "warning";
    case "medium":
      return "info";
    case "low":
      return "secondary";
    default:
      return "outline";
  }
}

export function statusBadgeVariant(
  status: string
): VariantProps<typeof badgeVariants>["variant"] {
  switch (status) {
    case "resolved":
    case "closed":
      return "success";
    case "open":
      return "critical";
    case "investigating":
    case "mitigating":
      return "warning";
    default:
      return "info";
  }
}
