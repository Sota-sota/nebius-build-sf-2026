import { cn } from "../../lib/utils"

const base = "inline-flex items-center justify-center whitespace-nowrap font-mono text-[11px] transition-all duration-150 focus-visible:outline-none disabled:pointer-events-none disabled:opacity-40"

const variants = {
  default: "bg-[var(--border)] text-[var(--text)] hover:bg-[var(--border-strong)]",
  destructive: "text-[var(--semantic-critical)] border border-[rgba(255,68,68,0.3)] bg-[rgba(255,68,68,0.1)] hover:bg-[rgba(255,68,68,0.18)]",
  outline: "border border-[var(--border)] bg-transparent text-[var(--text-dim)] hover:bg-[var(--overlay-subtle)] hover:text-[var(--text)]",
  ghost: "bg-transparent text-[var(--text-dim)] hover:bg-[var(--overlay-subtle)] hover:text-[var(--text)]",
  success: "text-[var(--semantic-positive)] border border-[rgba(68,255,136,0.3)] bg-[rgba(68,255,136,0.1)] hover:bg-[rgba(68,255,136,0.18)]",
  glow: "text-[var(--semantic-low)] border border-[rgba(51,136,255,0.3)] bg-[rgba(51,136,255,0.1)] hover:bg-[rgba(51,136,255,0.18)]",
}

const sizes = {
  default: "h-7 px-3 py-1",
  sm: "h-6 px-2 py-0.5 text-[10px]",
  lg: "h-9 px-5 py-2",
  icon: "h-7 w-7",
}

export function Button({ className, variant = "default", size = "default", ...props }) {
  return (
    <button
      className={cn(base, variants[variant], sizes[size], className)}
      {...props}
    />
  )
}
