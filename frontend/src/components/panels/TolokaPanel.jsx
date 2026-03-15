import { useAppStore } from "../../stores/appStore"
import { Shield, Video, CheckCircle, XCircle, Loader2, Play } from "lucide-react"

export function TolokaPanel({ sendMessage }) {
  const homerResults = useAppStore((s) => s.homerResults)
  const securityEval = useAppStore((s) => s.securityEval)

  const runSecurityEval = () => {
    sendMessage({ type: "security_eval" })
  }

  const isRunning = securityEval?.status === "running"

  return (
    <div className="h-full flex flex-col overflow-hidden" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
      {/* Panel header */}
      <div className="wm-panel-header">
        <span className="wm-panel-title">Toloka</span>
        <div className="flex items-center gap-2">
          {homerResults.length > 0 && (
            <span className="wm-data-badge">{homerResults.length} demos</span>
          )}
          {securityEval?.status === "completed" && (
            <span
              className="wm-data-badge"
              style={{ color: securityEval.score >= 80 ? "var(--accent-green)" : "var(--accent-red, #ef4444)" }}
            >
              {securityEval.score}%
            </span>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-2" style={{ scrollbarWidth: "thin" }}>
        {/* Security Eval Section */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-1">
              <Shield size={11} style={{ color: "var(--text-dim)" }} />
              <span className="text-[10px] font-medium uppercase tracking-wider" style={{ color: "var(--text-dim)" }}>
                Security Eval
              </span>
            </div>
            <button
              onClick={runSecurityEval}
              disabled={isRunning}
              className="flex items-center gap-1 px-2 py-0.5 text-[9px] font-medium uppercase tracking-wider rounded"
              style={{
                background: isRunning ? "var(--border)" : "var(--accent-green, #22c55e)",
                color: isRunning ? "var(--text-dim)" : "#000",
                cursor: isRunning ? "not-allowed" : "pointer",
                border: "none",
              }}
            >
              {isRunning ? <Loader2 size={9} className="animate-spin" /> : <Play size={9} />}
              {isRunning ? "Running..." : "Run"}
            </button>
          </div>

          {securityEval && (
            <div className="space-y-1">
              {/* Progress / Summary */}
              <div
                className="p-1.5 rounded text-[10px]"
                style={{ background: "var(--bg)", border: "1px solid var(--border)" }}
              >
                <div className="flex justify-between items-center mb-1">
                  <span style={{ color: "var(--text-dim)" }}>{securityEval.message}</span>
                </div>
                {securityEval.status === "running" && (
                  <div className="w-full h-1 rounded overflow-hidden" style={{ background: "var(--border)" }}>
                    <div
                      className="h-full rounded"
                      style={{
                        width: `${((securityEval.completed || 0) / (securityEval.total || 1)) * 100}%`,
                        background: "var(--accent-green, #22c55e)",
                        transition: "width 0.3s ease",
                      }}
                    />
                  </div>
                )}
                {securityEval.status === "completed" && (
                  <div className="flex gap-3 mt-1">
                    <span style={{ color: "var(--accent-green, #22c55e)" }}>
                      {securityEval.passed} passed
                    </span>
                    <span style={{ color: "var(--accent-red, #ef4444)" }}>
                      {securityEval.failed} failed
                    </span>
                  </div>
                )}
              </div>

              {/* Individual results */}
              {securityEval.results?.map((r) => (
                <div
                  key={r.scenario_id}
                  className="p-1.5 rounded text-[9px]"
                  style={{
                    background: "var(--bg)",
                    border: `1px solid ${r.passed ? "var(--accent-green, #22c55e)" : "var(--accent-red, #ef4444)"}`,
                    borderLeftWidth: 2,
                  }}
                >
                  <div className="flex items-center gap-1">
                    {r.passed ? (
                      <CheckCircle size={10} style={{ color: "var(--accent-green, #22c55e)" }} />
                    ) : (
                      <XCircle size={10} style={{ color: "var(--accent-red, #ef4444)" }} />
                    )}
                    <span className="font-medium uppercase tracking-wider" style={{ color: "var(--text)" }}>
                      {r.category}
                    </span>
                    <span
                      className="ml-auto px-1 rounded"
                      style={{
                        background: r.risk_level === "high" ? "rgba(239,68,68,0.2)" : r.risk_level === "medium" ? "rgba(234,179,8,0.2)" : "rgba(34,197,94,0.2)",
                        color: r.risk_level === "high" ? "#ef4444" : r.risk_level === "medium" ? "#eab308" : "#22c55e",
                      }}
                    >
                      {r.risk_level}
                    </span>
                  </div>
                  <p className="mt-0.5" style={{ color: "var(--text-dim)" }}>{r.description}</p>
                  {r.findings?.length > 0 && (
                    <ul className="mt-0.5 space-y-0.5" style={{ color: "var(--accent-red, #ef4444)" }}>
                      {r.findings.map((f, i) => (
                        <li key={i}>{f}</li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </div>
          )}

          {!securityEval && (
            <p className="text-[9px] p-1.5 rounded" style={{ color: "var(--text-dim)", background: "var(--bg)", border: "1px solid var(--border)" }}>
              Run red-team eval to stress-test the reasoning agent against adversarial prompts.
            </p>
          )}
        </div>

        {/* HomER Demos Section */}
        <div>
          <div className="flex items-center gap-1 mb-1">
            <Video size={11} style={{ color: "var(--text-dim)" }} />
            <span className="text-[10px] font-medium uppercase tracking-wider" style={{ color: "var(--text-dim)" }}>
              HomER Demos
            </span>
          </div>

          {homerResults.length > 0 ? (
            <div className="space-y-1">
              {homerResults.map((result, i) => (
                <div
                  key={i}
                  className="p-1.5 rounded text-[9px]"
                  style={{ background: "var(--bg)", border: "1px solid var(--border)" }}
                >
                  <p style={{ color: "var(--text-dim)" }}>
                    {typeof result.demos === "string"
                      ? result.demos
                      : Array.isArray(result.demos)
                      ? result.demos.join("\n")
                      : JSON.stringify(result.demos)}
                  </p>
                  <span className="text-[8px]" style={{ color: "var(--accent-blue, #3b82f6)" }}>
                    {result.source}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-[9px] p-1.5 rounded" style={{ color: "var(--text-dim)", background: "var(--bg)", border: "1px solid var(--border)" }}>
              Egocentric demos from toloka/HomER will appear here when the agent reasons about a task.
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
