import { AppHeader } from "./app-header";
import { AppSidebar } from "./app-sidebar";

export function PageContainer({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-dvh min-h-0 flex-col bg-background text-foreground font-sans overflow-hidden">
      <div className="shrink-0">
        <AppHeader />
      </div>
      <div className="flex min-h-0 flex-1 overflow-hidden">
        <AppSidebar />
        <main className="min-h-0 min-w-0 flex-1 bg-muted/30 p-4 sm:p-6 overflow-y-auto overflow-x-hidden flex flex-col">{children}</main>
      </div>
    </div>
  );
}
