import { lazy, Suspense } from "react"
import { useWebSocket } from "./hooks/useWebSocket"
import { Header } from "./components/layout/Header"
import { Sidebar } from "./components/layout/Sidebar"
import { CameraFeed } from "./components/panels/CameraFeed"
import { SceneViewer } from "./components/panels/SceneViewer"
import { ReasoningTrace } from "./components/panels/ReasoningTrace"
import { TavilyResults } from "./components/panels/TavilyResults"
import { ArmStatus } from "./components/panels/ArmStatus"
import { ApprovalGate } from "./components/panels/ApprovalGate"
import { VoiceButton } from "./components/voice/VoiceButton"
import { CommandHistory } from "./components/voice/CommandHistory"
import { TolokaPanel } from "./components/panels/TolokaPanel"

const ArmSimulation = lazy(() =>
  import("./components/panels/ArmSimulation").then((m) => ({ default: m.ArmSimulation }))
)

export default function App() {
  const { sendMessage } = useWebSocket()

  return (
    <div className="flex h-screen w-screen overflow-hidden" style={{ background: "var(--bg)" }}>
      <Sidebar />

      <div className="flex flex-1 flex-col overflow-hidden">
        <Header />

        {/* Panels grid — worldmonitor style: tight 4px gap, auto-fill */}
        <main className="flex-1 grid grid-cols-[1fr_1.2fr_1fr] grid-rows-[1fr_1fr] gap-1 p-1 overflow-hidden">
          {/* Left column: Camera + Scene */}
          <div className="flex flex-col gap-1 overflow-hidden">
            <div className="flex-[1.2] min-h-0">
              <CameraFeed />
            </div>
            <div className="flex-1 min-h-0">
              <SceneViewer />
            </div>
          </div>

          {/* Center column: 3D Arm Simulation (spans 2 rows) */}
          <div className="row-span-2 flex flex-col gap-1 overflow-hidden">
            <div className="flex-1 min-h-0 overflow-hidden relative" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
              {/* Panel header */}
              <div className="wm-panel-header absolute top-0 left-0 right-0 z-10" style={{ background: "rgba(20,20,20,0.85)", backdropFilter: "blur(4px)" }}>
                <span className="wm-panel-title">SO-101 Live</span>
                <span className="wm-data-badge live">ACTIVE</span>
              </div>
              <Suspense fallback={
                <div className="flex h-full items-center justify-center" style={{ background: "var(--bg)" }}>
                  <div className="text-center">
                    <div className="mx-auto h-6 w-6 rounded-full border-2 border-[var(--border)] border-t-[var(--text)]" style={{ animation: "spin 0.8s linear infinite" }} />
                    <p className="mt-2 text-[10px]" style={{ color: "var(--text-dim)" }}>Loading 3D...</p>
                  </div>
                </div>
              }>
                <ArmSimulation />
              </Suspense>
              {/* Approval gate overlay at bottom */}
              <div className="absolute bottom-0 left-0 right-0 p-2 z-10">
                <ApprovalGate sendMessage={sendMessage} />
              </div>
            </div>
          </div>

          {/* Right column: Reasoning + Tavily */}
          <div className="flex flex-col gap-1 overflow-hidden">
            <div className="flex-1 min-h-0">
              <ReasoningTrace />
            </div>
          </div>

          {/* Bottom-left: Arm telemetry */}
          <div className="overflow-hidden">
            <ArmStatus />
          </div>

          {/* Bottom-right: Tavily + Toloka stacked */}
          <div className="flex flex-col gap-1 overflow-hidden">
            <div className="flex-1 min-h-0">
              <TavilyResults />
            </div>
            <div className="flex-1 min-h-0">
              <TolokaPanel sendMessage={sendMessage} />
            </div>
          </div>
        </main>

        {/* Bottom bar — command input */}
        <footer className="px-3 py-2 space-y-1" style={{ background: "var(--surface)", borderTop: "1px solid var(--border)" }}>
          <CommandHistory sendMessage={sendMessage} />
          <VoiceButton sendMessage={sendMessage} />
        </footer>
      </div>
    </div>
  )
}
