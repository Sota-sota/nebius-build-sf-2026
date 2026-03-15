import { useAppStore } from "../../stores/appStore"
import { Button } from "../ui/button"
import { ShieldAlert, AlertTriangle, Check, X } from "lucide-react"

export function ApprovalGate({ sendMessage }) {
  const pendingApproval = useAppStore((s) => s.pendingApproval)
  const setPendingApproval = useAppStore((s) => s.setPendingApproval)

  if (!pendingApproval) return null

  const isHigh = pendingApproval.risk_level === "high"

  const handleApprove = () => {
    sendMessage({ type: "approve", action_id: pendingApproval.action_id })
    setPendingApproval(null)
  }

  const handleReject = () => {
    sendMessage({ type: "reject", action_id: pendingApproval.action_id })
    setPendingApproval(null)
  }

  return (
    <div
      className="p-3 animate-fade-in"
      style={{
        background: isHigh ? "rgba(255,68,68,0.08)" : "rgba(255,170,0,0.08)",
        border: `1px solid ${isHigh ? "rgba(255,68,68,0.4)" : "rgba(255,170,0,0.3)"}`,
        animation: isHigh ? "glow-pulse-red 2s ease-in-out infinite" : undefined,
      }}
    >
      <div className="flex items-center gap-2 mb-1.5">
        {isHigh ? (
          <ShieldAlert className="h-3.5 w-3.5" style={{ color: "var(--semantic-critical)" }} />
        ) : (
          <AlertTriangle className="h-3.5 w-3.5" style={{ color: "var(--semantic-elevated)" }} />
        )}
        <span className="text-[11px] font-semibold uppercase tracking-[0.5px]" style={{ color: "var(--text)" }}>
          {isHigh ? "DANGER" : "Review Required"}
        </span>
        <span className={`wm-data-badge ${isHigh ? "danger" : "warning"}`}>
          {pendingApproval.risk_level?.toUpperCase()} RISK
        </span>
        <span className="ml-auto text-[9px]" style={{ color: "var(--text-muted)" }}>
          {pendingApproval.actions?.length || 0} actions
        </span>
      </div>

      {pendingApproval.risk_justification && (
        <p className="text-[10px] mb-2 leading-relaxed" style={{ color: "var(--text-dim)" }}>
          {pendingApproval.risk_justification}
        </p>
      )}

      <div className="flex gap-2">
        <Button variant="success" size="sm" onClick={handleApprove} className="flex-1">
          <Check className="h-3 w-3 mr-1" />
          Approve
        </Button>
        <Button variant="destructive" size="sm" onClick={handleReject} className="flex-1">
          <X className="h-3 w-3 mr-1" />
          Reject
        </Button>
      </div>
    </div>
  )
}
