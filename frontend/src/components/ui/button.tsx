import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center whitespace-nowrap rounded-md text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500/60 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-60 ring-offset-slate-950",
  {
    variants: {
      variant: {
        default: "bg-sky-500 text-slate-950 hover:bg-sky-400",
        secondary: "bg-slate-800 text-slate-50 hover:bg-slate-700",
        outline:
          "border border-slate-700 bg-transparent text-slate-100 hover:bg-slate-900",
        ghost: "text-slate-200 hover:bg-slate-900/60",
        destructive: "bg-red-600 text-slate-50 hover:bg-red-500"
      },
      size: {
        sm: "h-7 px-3 py-1",
        md: "h-8 px-3.5 py-1.5",
        lg: "h-9 px-4 py-2",
        icon: "h-8 w-8"
      }
    },
    defaultVariants: {
      variant: "default",
      size: "md"
    }
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(buttonVariants({ variant, size }), className)}
        {...props}
      />
    );
  }
);

Button.displayName = "Button";

