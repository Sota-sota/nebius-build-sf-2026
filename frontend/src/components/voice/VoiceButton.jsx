import { useState, useCallback } from "react"
import { useVoice } from "../../hooks/useVoice"
import { useAppStore } from "../../stores/appStore"
import { Mic, MicOff, Loader2, Send, Command } from "lucide-react"

export function VoiceButton({ sendMessage }) {
  const [textInput, setTextInput] = useState("")
  const addCommand = useAppStore((s) => s.addCommand)
  const resetPipeline = useAppStore((s) => s.resetPipeline)
  const pipelineStatus = useAppStore((s) => s.pipelineStatus)

  const handleCommand = useCallback(
    (text) => {
      if (!text.trim()) return
      resetPipeline()
      addCommand(text)
      sendMessage({ type: "command", text })
    },
    [sendMessage, addCommand, resetPipeline]
  )

  const { isListening, interimTranscript, startListening, stopListening, isSupported } =
    useVoice({ onResult: handleCommand })

  const isProcessing = ["perceiving", "searching", "planning", "executing"].includes(pipelineStatus)

  const handleTextSubmit = (e) => {
    e.preventDefault()
    if (textInput.trim()) {
      handleCommand(textInput.trim())
      setTextInput("")
    }
  }

  return (
    <div className="flex flex-col items-center gap-1.5">
      {(isListening || interimTranscript) && (
        <div className="text-[10px] font-mono" style={{ color: "var(--semantic-low)", animation: "pulse-dot 1.5s infinite" }}>
          {interimTranscript || "Listening..."}
        </div>
      )}

      <div className="flex items-center gap-2 w-full">
        {isSupported && (
          <button
            onMouseDown={startListening}
            onMouseUp={stopListening}
            onMouseLeave={stopListening}
            disabled={isProcessing}
            className="wm-icon-btn"
            style={{
              width: 28, height: 28,
              background: isListening ? "rgba(255,68,68,0.2)" : "var(--overlay-subtle)",
              border: `1px solid ${isListening ? "rgba(255,68,68,0.4)" : "var(--border)"}`,
              color: isListening ? "var(--semantic-critical)" : isProcessing ? "var(--text-faint)" : "var(--text-dim)",
            }}
          >
            {isProcessing ? (
              <Loader2 className="h-3.5 w-3.5" style={{ animation: "spin 0.8s linear infinite" }} />
            ) : isListening ? (
              <Mic className="h-3.5 w-3.5" />
            ) : (
              <MicOff className="h-3.5 w-3.5" />
            )}
          </button>
        )}

        <form onSubmit={handleTextSubmit} className="flex flex-1 gap-1.5">
          <div className="relative flex-1">
            <Command className="absolute left-2 top-1/2 -translate-y-1/2 h-3 w-3" style={{ color: "var(--text-faint)" }} />
            <input
              type="text"
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              placeholder='Try "pick up the red cup" or "sort by weight"'
              disabled={isProcessing}
              className="w-full pl-7 pr-3 py-1.5 text-[11px] font-mono outline-none disabled:opacity-40"
              style={{
                background: "var(--bg)",
                border: "1px solid var(--border)",
                color: "var(--text)",
              }}
            />
          </div>
          <button
            type="submit"
            disabled={isProcessing || !textInput.trim()}
            className="wm-icon-btn disabled:opacity-40"
            style={{
              width: 28, height: 28,
              background: "rgba(51,136,255,0.1)",
              border: "1px solid rgba(51,136,255,0.3)",
              color: "var(--semantic-low)",
            }}
          >
            <Send className="h-3 w-3" />
          </button>
        </form>
      </div>
    </div>
  )
}
