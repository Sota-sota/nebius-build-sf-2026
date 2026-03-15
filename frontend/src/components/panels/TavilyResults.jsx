import { memo } from "react"
import { useAppStore } from "../../stores/appStore"
import { Card, CardHeader, CardTitle, CardContent } from "../ui/card"
import { ScrollArea } from "../ui/scroll-area"
import { Search, ExternalLink, Globe } from "lucide-react"

export const TavilyResults = memo(function TavilyResults() {
  const tavilyResults = useAppStore((s) => s.tavilyResults)

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Globe className="h-3 w-3" style={{ color: "var(--semantic-high)" }} />
          Tavily Search
        </CardTitle>
        {tavilyResults.length > 0 && (
          <span className="wm-panel-count">{tavilyResults.length}</span>
        )}
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-full">
          {tavilyResults.length > 0 ? (
            <div className="space-y-2">
              {tavilyResults.map((search, i) => (
                <div
                  key={i}
                  className="p-2 animate-slide-in"
                  style={{ background: "rgba(255,136,0,0.04)", border: "1px solid rgba(255,136,0,0.15)", animationDelay: `${i * 80}ms` }}
                >
                  <div className="flex items-center gap-1.5 mb-1.5">
                    <Search className="h-2.5 w-2.5 shrink-0" style={{ color: "var(--semantic-high)" }} />
                    <span className="text-[10px] font-semibold truncate" style={{ color: "var(--semantic-high)" }}>
                      {search.query}
                    </span>
                  </div>
                  <div className="space-y-1">
                    {search.results?.map((result, j) => (
                      <div
                        key={j}
                        className="p-1.5 transition-all"
                        style={{ background: "var(--overlay-subtle)", borderBottom: "1px solid var(--border)" }}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <span className="text-[10px] font-medium" style={{ color: "var(--text)" }}>
                            {result.title}
                          </span>
                          {result.url && (
                            <a
                              href={result.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="shrink-0"
                              style={{ color: "var(--text-faint)" }}
                            >
                              <ExternalLink className="h-2.5 w-2.5" />
                            </a>
                          )}
                        </div>
                        <p className="mt-0.5 text-[9px] leading-relaxed line-clamp-2" style={{ color: "var(--text-muted)" }}>
                          {result.content}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex h-full items-center justify-center">
              <div className="text-center">
                <Globe className="mx-auto h-6 w-6 mb-1" style={{ color: "var(--text-faint)" }} />
                <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>No searches yet</p>
              </div>
            </div>
          )}
        </ScrollArea>
      </CardContent>
    </Card>
  )
})
