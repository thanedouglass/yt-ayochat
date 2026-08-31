import { cn } from "@/lib/utils";
import { ReactNode } from "react";

interface GlassCardProps {
  children: ReactNode;
  className?: string;
  shiny?: boolean;
  glow?: boolean;
}

export function GlassCard({ children, className, shiny = false, glow = false }: GlassCardProps) {
  return (
    <div
      className={cn(
        "glass-card relative overflow-hidden rounded-xl",
        shiny && "shiny-edge",
        glow && "luminescent-glow",
        className
      )}
    >
      {children}
    </div>
  );
}