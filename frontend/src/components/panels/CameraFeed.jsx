import { memo } from "react"
import { useAppStore } from "../../stores/appStore"
import { Card, CardHeader, CardTitle, CardContent } from "../ui/card"
import { Camera, CameraOff, Crosshair } from "lucide-react"

const positionMap = {
  "far-left": "10%",
  "center-left": "30%",
  "center": "50%",
  "center-right": "70%",
  "far-right": "90%",
}

export const CameraFeed = memo(function CameraFeed() {
  const cameraFrame = useAppStore((s) => s.cameraFrame)
  const scene = useAppStore((s) => s.scene)

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Camera className="h-3 w-3" style={{ color: "var(--semantic-low)" }} />
          Camera
        </CardTitle>
        {cameraFrame ? (
          <span className="wm-data-badge live">LIVE</span>
        ) : (
          <span className="wm-data-badge offline">OFFLINE</span>
        )}
      </CardHeader>
      <CardContent>
        <div className="relative aspect-[4/3] w-full overflow-hidden" style={{ background: "var(--bg)", border: "1px solid var(--border)" }}>
          {cameraFrame ? (
            <>
              <img
                src={`data:image/jpeg;base64,${cameraFrame.frame_b64}`}
                alt="Camera feed"
                className="h-full w-full object-cover"
              />
              {scene?.objects?.map((obj) => (
                <div
                  key={obj.id}
                  className="absolute top-1/2 -translate-x-1/2 -translate-y-1/2 animate-fade-in"
                  style={{ left: positionMap[obj.position] || "50%" }}
                >
                  <Crosshair className="h-5 w-5" style={{ color: "var(--status-live)" }} />
                  <span className="absolute top-6 left-1/2 -translate-x-1/2 whitespace-nowrap text-[9px] px-1.5 py-0.5" style={{ background: "rgba(0,0,0,0.8)", color: "var(--status-live)" }}>
                    {obj.name}
                  </span>
                </div>
              ))}
            </>
          ) : (
            <div className="flex h-full flex-col items-center justify-center gap-2">
              <CameraOff className="h-6 w-6" style={{ color: "var(--text-faint)" }} />
              <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>No camera feed</p>
              <p className="text-[9px]" style={{ color: "var(--text-faint)" }}>Waiting for connection...</p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
})
