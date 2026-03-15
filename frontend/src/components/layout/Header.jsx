import { useAppStore } from "../../stores/appStore"
import { Activity, Wifi, WifiOff, Zap } from "lucide-react"

const STATUS_CONFIG = {
  idle: { label: "READY", cls: "" },
  connected: { label: "CONNECTED", cls: "success" },
  perceiving: { label: "PERCEIVING", cls: "info" },
  searching: { label: "SEARCHING", cls: "warning" },
  planning: { label: "PLANNING", cls: "info" },
  awaiting_approval: { label: "AWAITING APPROVAL", cls: "warning" },
  executing: { label: "EXECUTING", cls: "success" },
  completed: { label: "COMPLETE", cls: "success" },
  error: { label: "ERROR", cls: "danger" },
}

export function Header() {
  const connected = useAppStore((s) => s.connected)
  const pipelineStatus = useAppStore((s) => s.pipelineStatus)
  const statusCfg = STATUS_CONFIG[pipelineStatus] || STATUS_CONFIG.idle

  return (
    <header className="flex items-center justify-between px-4 h-10 shrink-0" style={{ background: "var(--surface)", borderBottom: "1px solid var(--border)" }}>
      <div className="flex items-center gap-3">
        <Zap className="h-3.5 w-3.5" style={{ color: "var(--semantic-low)" }} />
        <span className="text-[11px] font-semibold uppercase tracking-[1px]" style={{ color: "var(--text)" }}>
          ArmPilot
        </span>
        <span className="text-[10px]" style={{ color: "var(--text-muted)" }}>Mission Control</span>
      </div>

      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5">
          <Activity className="h-3 w-3" style={{ color: "var(--text-dim)" }} />
          <span className={`wm-data-badge ${statusCfg.cls}`}>{statusCfg.label}</span>
        </div>

        <div className="h-4 w-px" style={{ background: "var(--border)" }} />

        <div className="flex items-center gap-1.5">
          {connected ? (
            <>
              <span className="inline-block h-[6px] w-[6px] rounded-full" style={{ background: "var(--status-live)", animation: "pulse-dot 2s infinite" }} />
              <Wifi className="h-3 w-3" style={{ color: "var(--status-live)" }} />
              <span className="wm-data-badge live">LIVE</span>
            </>
          ) : (
            <>
              <span className="inline-block h-[6px] w-[6px] rounded-full" style={{ background: "var(--semantic-critical)" }} />
              <WifiOff className="h-3 w-3" style={{ color: "var(--semantic-critical)" }} />
              <span className="wm-data-badge offline">OFFLINE</span>
            </>
          )}
        </div>
      </div>
    </header>
  )
}
