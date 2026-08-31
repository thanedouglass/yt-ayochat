import { cn } from "@/lib/utils";
import { ReactNode } from "react";

interface M3ButtonProps {
  children: ReactNode;
  onClick?: () => void;
  className?: string;
  variant?: "filled" | "outlined" | "text";
  size?: "small" | "medium" | "large";
  disabled?: boolean;
}

export function M3Button({ 
  children, 
  onClick, 
  className, 
  variant = "filled",
  size = "medium",
  disabled = false
}: M3ButtonProps) {
  const variantStyles = {
    filled: "bg-[var(--m3-primary)] text-[var(--m3-on-primary)] hover:bg-[var(--m3-primary-container)] hover:text-[var(--m3-on-primary-container)]",
    outlined: "border-2 border-[var(--m3-primary)] text-[var(--m3-primary)] hover:bg-[var(--m3-primary)] hover:text-[var(--m3-on-primary)]",
    text: "text-[var(--m3-primary)] hover:bg-[var(--m3-primary)] hover:text-[var(--m3-on-primary)]"
  };

  const sizeStyles = {
    small: "px-3 py-1.5 text-sm",
    medium: "px-4 py-2 text-base",
    large: "px-6 py-3 text-lg"
  };

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "m3-button transition-all duration-150 ease-out disabled:opacity-50 disabled:cursor-not-allowed",
        variantStyles[variant],
        sizeStyles[size],
        className
      )}
    >
      {children}
    </button>
  );
}