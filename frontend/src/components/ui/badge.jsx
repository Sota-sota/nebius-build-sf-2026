import { cn } from "../../lib/utils"

const variantMap = {
  default: "",
  secondary: "",
  outline: "",
  success: "success",
  warning: "warning",
  danger: "danger",
  info: "info",
  live: "live",
}

export function Badge({ className, variant = "default", pulse, children, ...props }) {
  const badgeCls = variantMap[variant] || ""

  if (badgeCls) {
    return (
      <span
        className={cn("wm-data-badge", badgeCls, className)}
        {...props}
      >
        {children}
      </span>
    )
  }

  return (
    <span
      className={cn("wm-panel-count", className)}
      {...props}
    >
      {children}
    </span>
  )
}
