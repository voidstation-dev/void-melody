"use client";
import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { PageContainer } from "@/components/app-shell/page-container";
import { VieneuPage } from "@/components/vieneu/vieneu-page";

function VieneuRoute() {
  const searchParams = useSearchParams();
  return <VieneuPage initialVoiceId={searchParams.get("voice")} />
}

export default function Page() {
  return <PageContainer><Suspense fallback={<div className="p-6 text-sm text-muted-foreground">Loading Voice Lab…</div>}><VieneuRoute /></Suspense></PageContainer>
}
