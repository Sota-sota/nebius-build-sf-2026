import { LayoutDashboard, ScrollText, Settings, Bot, Cpu } from "lucide-react"

const navItems = [
  { icon: LayoutDashboard, label: "Dashboard", active: true },
  { icon: ScrollText, label: "Logs" },
  { icon: Settings, label: "Config" },
]

export function Sidebar() {
  return (
    <aside
      className="flex w-11 flex-col items-center py-2 gap-1"
      style={{ background: "var(--surface)", borderRight: "1px solid var(--border)" }}
    >
      <div className="mb-2 flex h-7 w-7 items-center justify-center" style={{ color: "var(--semantic-low)" }}>
        <Bot className="h-4 w-4" />
      </div>

      <div className="h-px w-5" style={{ background: "var(--border)" }} />

      {navItems.map((item) => (
        <button
          key={item.label}
          className="wm-icon-btn"
          style={item.active ? { background: "var(--overlay-light)", color: "var(--text)" } : undefined}
          title={item.label}
        >
          <item.icon className="h-3.5 w-3.5" />
        </button>
      ))}

      <div className="mt-auto flex flex-col items-center gap-0.5">
        <Cpu className="h-3 w-3" style={{ color: "var(--text-faint)" }} />
        <span className="text-[8px]" style={{ color: "var(--text-faint)" }}>Nebius</span>
      </div>
    </aside>
  )
}
