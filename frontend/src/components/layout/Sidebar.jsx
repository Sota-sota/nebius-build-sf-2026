import { LayoutDashboard, ScrollText, Settings, Bot, Cpu, Search } from "lucide-react"

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

      {/* Sponsor badges */}
      <div className="mt-auto flex flex-col items-center gap-1.5 pb-1">
        <div className="flex flex-col items-center gap-0.5" title="Powered by Nebius Token Factory">
          <Cpu className="h-3 w-3" style={{ color: "var(--text-faint)" }} />
          <span className="text-[7px] leading-tight text-center" style={{ color: "var(--text-faint)" }}>Nebius</span>
        </div>
        <div className="flex flex-col items-center gap-0.5" title="Search by Tavily">
          <Search className="h-3 w-3" style={{ color: "var(--semantic-high)" }} />
          <span className="text-[7px] leading-tight text-center" style={{ color: "var(--text-faint)" }}>Tavily</span>
        </div>
      </div>
    </aside>
  )
}
