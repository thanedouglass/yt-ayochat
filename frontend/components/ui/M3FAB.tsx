import { cn } from "@/lib/utils";
import { ReactNode } from "react";

interface M3FABProps {
  children: ReactNode;
  onClick?: () => void;
  className?: string;
  variant?: "primary" | "secondary" | "tertiary";
  size?: "medium" | "large";
  extended?: boolean;
}

export function M3FAB({ 
  children, 
  onClick, 
  className, 
  variant = "primary",
  size = "medium",
  extended = false
}: M3FABProps) {
  const variantStyles = {
    primary: "bg-[var(--m3-primary)] text-[var(--m3-on-primary)] hover:bg-[var(--m3-primary-container)] hover:text-[var(--m3-on-primary-container)]",
    secondary: "bg-[var(--m3-secondary)] text-[var(--m3-on-secondary)] hover:bg-[var(--m3-secondary-container)] hover:text-[var(--m3-on-secondary-container)]",
    tertiary: "bg-[var(--m3-tertiary)] text-[var(--m3-on-tertiary)] hover:bg-[var(--m3-tertiary-container)] hover:text-[var(--m3-on-tertiary-container)]"
  };

  const sizeStyles = {
    medium: "w-14 h-14",
    large: "w-20 h-20"
  };

  return (
    <button
      onClick={onClick}
      className={cn(
        "m3-fab flex items-center justify-center transition-all duration-250 ease-out",
        variantStyles[variant],
        extended ? "px-6 rounded-full" : sizeStyles[size],
        className
      )}
    >
      {children}
    </button>
  );
}