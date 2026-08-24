import React from "react"
import { cn } from "@/lib/utils"

interface BrandLogoProps extends React.ImgHTMLAttributes<HTMLImageElement> {
  className?: string
  alt?: string
}

export function BrandMark({ className, alt = "Melody", ...props }: BrandLogoProps) {
  return (
    <span className={cn("inline-flex items-center justify-center shrink-0", className)}>
      <img
        src="/melody-mark-black.png"
        alt={alt}
        className="h-full w-full object-contain dark:hidden"
        {...props}
      />
      <img
        src="/melody-mark-white.png"
        alt={alt}
        className="hidden h-full w-full object-contain dark:block"
        {...props}
      />
    </span>
  )
}

export function BrandBadge({ className, alt = "Melody", ...props }: BrandLogoProps) {
  return (
    <span className={cn("inline-flex items-center justify-center shrink-0", className)}>
      <img
        src="/app-icon.png"
        alt={alt}
        className="h-full w-full object-contain shadow-xs rounded-xl"
        {...props}
      />
    </span>
  )
}

export function BrandWordmark({ className, alt = "Melody", ...props }: BrandLogoProps) {
  return (
    <span className={cn("inline-flex items-center shrink-0", className)}>
      <img
        src="/melody-logo-header-black.png"
        alt={alt}
        className="h-full w-auto object-contain dark:hidden"
        {...props}
      />
      <img
        src="/melody-logo-header-white.png"
        alt={alt}
        className="hidden h-full w-auto object-contain dark:block"
        {...props}
      />
    </span>
  )
}
