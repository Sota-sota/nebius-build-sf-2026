import { memo } from "react"
import { useAppStore } from "../../stores/appStore"
import { Card, CardHeader, CardTitle, CardContent } from "../ui/card"
import { ScrollArea } from "../ui/scroll-area"
import { Scan, GripHorizontal, Ban } from "lucide-react"

const colorMap = {
  red: "#ff4444", blue: "#3388ff", green: "#44ff88", yellow: "#ffaa00",
  white: "#e8e8e8", black: "#555", silver: "#a1a1aa", orange: "#ff8800",
  pink: "#ec4899", purple: "#aa55ff", brown: "#a16207",
}

export const SceneViewer = memo(function SceneViewer() {
  const scene = useAppStore((s) => s.scene)

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Scan className="h-3 w-3" style={{ color: "var(--semantic-info)" }} />
          Scene
        </CardTitle>
        {scene?.objects && (
          <span className="wm-panel-count">{scene.objects.length}</span>
        )}
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-full">
          {scene?.objects?.length > 0 ? (
            <div className="space-y-1">
              {scene.objects.map((obj, i) => (
                <div
                  key={obj.id}
                  className="flex items-start gap-2 p-2 animate-fade-in"
                  style={{ background: "var(--overlay-subtle)", borderBottom: "1px solid var(--border)", animationDelay: `${i * 60}ms` }}
                >
                  <div
                    className="mt-1 h-2 w-2 rounded-full shrink-0"
                    style={{ backgroundColor: colorMap[obj.color] || "#888" }}
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] font-semibold" style={{ color: "var(--text)" }}>{obj.name}</span>
                      <span className="wm-panel-count">{obj.estimated_size}</span>
                    </div>
                    <div className="mt-0.5 flex items-center gap-2 text-[10px]" style={{ color: "var(--text-muted)" }}>
                      <span>{obj.material_guess}</span>
                      <span style={{ color: "var(--text-faint)" }}>|</span>
                      <span>{obj.position}</span>
                      <span style={{ color: "var(--text-faint)" }}>|</span>
                      {obj.graspable ? (
                        <span className="flex items-center gap-0.5" style={{ color: "var(--semantic-positive)" }}>
                          <GripHorizontal className="h-2.5 w-2.5" /> OK
                        </span>
                      ) : (
                        <span className="flex items-center gap-0.5" style={{ color: "var(--semantic-critical)" }}>
                          <Ban className="h-2.5 w-2.5" /> No
                        </span>
                      )}
                    </div>
                    {/* Confidence bar */}
                    <div className="mt-1 flex items-center gap-2">
                      <div className="flex-1 h-[3px]" style={{ background: "var(--border)" }}>
                        <div
                          className="h-full transition-all duration-300"
                          style={{
                            width: `${(obj.confidence * 100).toFixed(0)}%`,
                            background: obj.confidence > 0.8 ? "var(--semantic-positive)" : obj.confidence > 0.5 ? "var(--semantic-elevated)" : "var(--semantic-critical)",
                          }}
                        />
                      </div>
                      <span className="text-[9px] font-mono tabular-nums" style={{ color: "var(--text-dim)" }}>
                        {(obj.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex h-20 items-center justify-center">
              <span className="text-[10px]" style={{ color: "var(--text-muted)" }}>Point camera at workspace</span>
            </div>
          )}
        </ScrollArea>
      </CardContent>
    </Card>
  )
})
