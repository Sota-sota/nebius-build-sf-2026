export function DashboardLayout({ children }) {
  return (
    <div className="grid h-full grid-cols-2 grid-rows-2 gap-3 p-3 overflow-hidden">
      {children}
    </div>
  )
}
