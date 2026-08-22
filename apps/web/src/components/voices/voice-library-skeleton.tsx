export function VoiceLibrarySkeleton({ variant }: { variant: "custom" | "preset" }) {
  const count = variant === "custom" ? 2 : 4
  return (
    <div className={variant === "custom" ? "grid gap-3 sm:grid-cols-2" : "grid gap-3 lg:grid-cols-2"} aria-label="Loading voices" aria-busy="true">
      {Array.from({ length: count }, (_, index) => <div key={index} className="min-h-[172px] animate-pulse rounded-2xl border border-border/70 bg-card p-5"><div className="h-5 w-24 rounded-full bg-muted" /><div className="mt-6 h-5 w-2/3 rounded bg-muted" /><div className="mt-3 h-3 w-full rounded bg-muted" /><div className="mt-8 h-9 w-28 rounded-xl bg-muted" /></div>)}
    </div>
  )
}
