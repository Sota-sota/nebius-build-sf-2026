import { memo } from "react"
import { useAppStore } from "../../stores/appStore"
import { Card, CardHeader, CardTitle, CardContent } from "../ui/card"
import { Cog, Hand } from "lucide-react"

const JOINTS = [
  { label: "Base", short: "J1" },
  { label: "Shoulder", short: "J2" },
  { label: "Elbow", short: "J3" },
  { label: "Wrist Pitch", short: "J4" },
  { label: "Wrist Roll", short: "J5" },
]

const JOINT_MAX = 2.0

function jointColor(value) {
  const ratio = Math.abs(value) / JOINT_MAX
  if (ratio > 0.9) return "var(--semantic-critical)"
  if (ratio > 0.75) return "var(--semantic-elevated)"
  return "var(--semantic-positive)"
}

function gripperLabel(v) {
  if (v < 0.1) return { text: "OPEN", cls: "success" }
  if (v < 0.6) return { text: "CLOSING", cls: "warning" }
  return { text: "CLOSED", cls: "danger" }
}

export const ArmStatus = memo(function ArmStatus() {
  const armStatus = useAppStore((s) => s.armStatus)

  const positions = armStatus?.joint_positions || [0, 0, 0, 0, 0, 0]
  const gripperVal = positions[5] || 0
  const status = armStatus?.status || "idle"
  const grip = gripperLabel(gripperVal)

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Cog className="h-3 w-3" style={{ color: "var(--semantic-positive)" }} />
          Arm Telemetry
        </CardTitle>
        <span className={`wm-data-badge ${status === "executing" ? "warning" : status === "completed" ? "success" : status === "failed" ? "danger" : ""}`}>
          {status.toUpperCase()}
        </span>
      </CardHeader>
      <CardContent>
        <div className="space-y-1.5">
          {JOINTS.map((joint, i) => {
            const val = positions[i] || 0
            const pct = ((val + JOINT_MAX) / (JOINT_MAX * 2)) * 100

            return (
              <div key={i}>
                <div className="flex items-center justify-between mb-0.5">
                  <div className="flex items-center gap-1.5">
                    <span className="text-[9px] font-bold w-4" style={{ color: "var(--text-muted)" }}>{joint.short}</span>
                    <span className="text-[10px]" style={{ color: "var(--text-dim)" }}>{joint.label}</span>
                  </div>
                  <span className="text-[10px] font-mono tabular-nums" style={{ color: "var(--text-dim)" }}>
                    {val >= 0 ? "+" : ""}{val.toFixed(2)}
                  </span>
                </div>
                <div className="h-[3px] w-full" style={{ background: "var(--border)" }}>
                  <div
                    className="h-full transition-all duration-300"
                    style={{ width: `${Math.max(1, Math.min(100, pct))}%`, background: jointColor(val) }}
                  />
                </div>
              </div>
            )
          })}

          {/* Gripper */}
          <div className="mt-1 p-2 flex items-center gap-2" style={{ background: "var(--overlay-subtle)", border: "1px solid var(--border)" }}>
            <Hand
              className="h-4 w-4"
              style={{ color: gripperVal < 0.1 ? "var(--semantic-positive)" : gripperVal < 0.6 ? "var(--semantic-elevated)" : "var(--semantic-critical)" }}
            />
            <div className="flex-1">
              <div className="flex items-center justify-between mb-0.5">
                <span className="text-[10px]" style={{ color: "var(--text-dim)" }}>Gripper</span>
                <span className={`wm-data-badge ${grip.cls}`}>{grip.text}</span>
              </div>
              <div className="h-[3px] w-full" style={{ background: "var(--border)" }}>
                <div
                  className="h-full transition-all duration-300"
                  style={{ width: `${(gripperVal / 1.0) * 100}%`, background: "var(--semantic-low)" }}
                />
              </div>
            </div>
          </div>

          {/* Step counter */}
          {armStatus?.current_step != null && (
            <div className="flex items-center justify-center gap-1 pt-1">
              {Array.from({ length: armStatus.total_steps }, (_, i) => (
                <div
                  key={i}
                  className="h-[3px] transition-all duration-300"
                  style={{
                    width: i <= armStatus.current_step ? "20px" : "10px",
                    background: i < armStatus.current_step
                      ? "var(--semantic-positive)"
                      : i === armStatus.current_step
                        ? "var(--semantic-low)"
                        : "var(--border)",
                  }}
                />
              ))}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
})
