import { cn } from "../../lib/utils"

export function Card({ className, ...props }) {
  return (
    <div
      className={cn("wm-panel", className)}
      {...props}
    />
  )
}

export function CardHeader({ className, ...props }) {
  return (
    <div
      className={cn("wm-panel-header", className)}
      {...props}
    />
  )
}

export function CardTitle({ className, ...props }) {
  return (
    <span
      className={cn("wm-panel-title", className)}
      {...props}
    />
  )
}

export function CardContent({ className, ...props }) {
  return <div className={cn("wm-panel-content", className)} {...props} />
}
