import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide",
  {
    variants: {
      variant: {
        default:
          "border-slate-700 bg-slate-900/80 text-slate-100 shadow-sm shadow-slate-900/60",
        critical:
          "border-red-700 bg-red-950/80 text-red-100 shadow-sm shadow-red-900/60",
        warning:
          "border-amber-700 bg-amber-950/80 text-amber-100 shadow-sm shadow-amber-900/60",
        info: "border-sky-700 bg-sky-950/80 text-sky-100 shadow-sm shadow-sky-900/60"
      }
    },
    defaultVariants: {
      variant: "default"
    }
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div
      className={cn(badgeVariants({ variant }), className)}
      {...props}
    />
  );
}

