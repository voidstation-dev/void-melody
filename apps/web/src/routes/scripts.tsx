import { createFileRoute } from "@tanstack/react-router"
import { EmotionalScriptPage } from "@/components/emotional-script/emotional-script-page"

export const Route = createFileRoute("/scripts")({
  component: ScriptsRoute,
})

function ScriptsRoute() {
  return <EmotionalScriptPage />
}
