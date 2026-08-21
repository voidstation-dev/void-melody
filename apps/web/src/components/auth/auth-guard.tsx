"use client";

import React from "react";
import { useAuth } from "@/hooks/use-auth";
import { LoginScreen } from "./login-screen";
import { Radio, Loader2 } from "lucide-react";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex min-h-screen w-full flex-col items-center justify-center bg-background text-foreground">
        <div className="flex flex-col items-center gap-4">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 text-primary animate-pulse">
            <Radio className="h-7 w-7" />
          </div>
          <div className="flex items-center gap-2 text-xs font-semibold text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin text-primary" />
            <span>Void Melody</span>
          </div>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <LoginScreen />;
  }

  return <>{children}</>;
}
