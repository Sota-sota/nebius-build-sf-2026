import { memo, useRef, useEffect } from "react"
import { useAppStore } from "../../stores/appStore"
import { Card, CardHeader, CardTitle, CardContent } from "../ui/card"
import { ScrollArea } from "../ui/scroll-area"
import {
  Eye, Search, Brain, Clock, Play, CheckCircle2, XCircle, Sparkles, Plug,
} from "lucide-react"

const STEP_CONFIG = {
  connected: { icon: Plug, label: "CONNECTED", color: "var(--semantic-positive)" },
  perceiving: { icon: Eye, label: "PERCEIVING", color: "var(--semantic-low)" },
  searching: { icon: Search, label: "SEARCHING", color: "var(--semantic-high)" },
  planning: { icon: Brain, label: "PLANNING", color: "#aa55ff" },
  awaiting_approval: { icon: Clock, label: "APPROVAL", color: "var(--semantic-elevated)" },
  executing: { icon: Play, label: "EXECUTING", color: "var(--semantic-positive)" },
  completed: { icon: CheckCircle2, label: "DONE", color: "var(--semantic-positive)" },
  error: { icon: XCircle, label: "ERROR", color: "var(--semantic-critical)" },
}

export const ReasoningTrace = memo(function ReasoningTrace() {
  const reasoningSteps = useAppStore((s) => s.reasoningSteps)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [reasoningSteps.length])

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Sparkles className="h-3 w-3" style={{ color: "#aa55ff" }} />
          Reasoning
        </CardTitle>
        <span className="wm-panel-count">{reasoningSteps.length}</span>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-full">
          {reasoningSteps.length > 0 ? (
            <div className="relative ml-2">
              {/* Timeline line */}
              <div className="absolute left-0 top-0 bottom-0 w-px" style={{ background: "var(--border)" }} />

              {reasoningSteps.map((step, i) => {
                const config = STEP_CONFIG[step.step] || STEP_CONFIG.error
                const Icon = config.icon
                const isLast = i === reasoningSteps.length - 1

                return (
                  <div key={i} className="relative pl-4 pb-2 animate-fade-in">
                    {/* Dot on timeline */}
                    <div className="absolute left-0 top-1.5 -translate-x-1/2">
                      <div
                        className="h-[6px] w-[6px] rounded-full"
                        style={{
                          background: config.color,
                          boxShadow: isLast ? `0 0 8px ${config.color}` : "none",
                          animation: isLast ? "pulse-dot 2s infinite" : "none",
                        }}
                      />
                    </div>

                    {/* Content */}
                    <div className="p-1.5" style={{ borderBottom: "1px solid var(--border)" }}>
                      <div className="flex items-center gap-2 mb-0.5">
                        <Icon className="h-3 w-3" style={{ color: config.color }} />
                        <span className="text-[9px] font-semibold uppercase tracking-[0.5px]" style={{ color: config.color }}>
                          {config.label}
                        </span>
                        {step.timestamp && (
                          <span className="ml-auto text-[9px] font-mono" style={{ color: "var(--text-faint)" }}>
                            {new Date(step.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                          </span>
                        )}
                      </div>
                      <p className="text-[11px] leading-relaxed" style={{ color: "var(--text-secondary)" }}>{step.detail}</p>
                      {step.tavily_query && (
                        <div className="mt-1 flex items-center gap-1.5 px-1.5 py-0.5" style={{ background: "rgba(255,136,0,0.08)", border: "1px solid rgba(255,136,0,0.2)" }}>
                          <Search className="h-2.5 w-2.5 shrink-0" style={{ color: "var(--semantic-high)" }} />
                          <span className="text-[9px] font-mono truncate" style={{ color: "var(--semantic-high)" }}>{step.tavily_query}</span>
                        </div>
                      )}
                    </div>
                  </div>
                )
              })}
              <div ref={bottomRef} />
            </div>
          ) : (
            <div className="flex h-full items-center justify-center">
              <div className="text-center">
                <Brain className="mx-auto h-6 w-6 mb-1" style={{ color: "var(--text-faint)" }} />
                <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>Waiting for command...</p>
              </div>
            </div>
          )}
        </ScrollArea>
      </CardContent>
    </Card>
  )
})
