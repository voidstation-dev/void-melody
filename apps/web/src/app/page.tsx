import { Suspense } from "react"
import { PageContainer } from "@/components/app-shell/page-container"
import { TTSStudio } from "@/components/tts/tts-studio"

export default function HomePage() {
  return (
    <PageContainer>
      <Suspense fallback={<div className="p-6 text-sm text-muted-foreground">Loading Studio…</div>}>
        <TTSStudio />
      </Suspense>
    </PageContainer>
  )
}
