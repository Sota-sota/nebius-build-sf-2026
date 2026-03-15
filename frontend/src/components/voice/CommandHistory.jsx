import { useAppStore } from "../../stores/appStore"
import { History } from "lucide-react"

export function CommandHistory({ sendMessage }) {
  const commandHistory = useAppStore((s) => s.commandHistory)
  const resetPipeline = useAppStore((s) => s.resetPipeline)
  const addCommand = useAppStore((s) => s.addCommand)

  if (commandHistory.length === 0) return null

  const handleRerun = (text) => {
    resetPipeline()
    addCommand(text)
    sendMessage({ type: "command", text })
  }

  return (
    <div className="flex items-center gap-2 overflow-x-auto" style={{ scrollbarWidth: "none" }}>
      <History className="h-3 w-3 shrink-0" style={{ color: "var(--text-faint)" }} />
      {commandHistory.slice(0, 5).map((cmd, i) => (
        <button
          key={i}
          onClick={() => handleRerun(cmd.text)}
          className="shrink-0 px-2 py-0.5 text-[9px] font-mono transition-all"
          style={{
            background: "var(--overlay-subtle)",
            border: "1px solid var(--border)",
            color: "var(--text-muted)",
          }}
          onMouseEnter={(e) => { e.target.style.color = "var(--text)"; e.target.style.borderColor = "var(--border-strong)" }}
          onMouseLeave={(e) => { e.target.style.color = "var(--text-muted)"; e.target.style.borderColor = "var(--border)" }}
        >
          {cmd.text.length > 35 ? cmd.text.slice(0, 35) + "..." : cmd.text}
        </button>
      ))}
    </div>
  )
}
