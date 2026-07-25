import { ApiDashboard } from "./components/ApiDashboard"
import { SpacePlaceholder } from "./components/SpacePlaceholder"
import { VideoFeed } from "./components/VideoFeed"

export function App() {
  if (window.location.pathname.startsWith("/dashboard")) return <ApiDashboard />
  if (window.location.pathname.startsWith("/space")) return <SpacePlaceholder />
  return <VideoFeed />
}
