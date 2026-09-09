import type { ReactNode } from "react"

import { useFlashOnChange } from "@/lib/useFlashOnChange"
import { cn } from "@/lib/utils"

export function FlashValue({
  value,
  children,
  className,
}: {
  value: number | null | undefined
  children: ReactNode
  className?: string
}) {
  const { direction, replayKey } = useFlashOnChange(value)

  return (
    <span
      key={replayKey}
      className={cn(
        "inline-block rounded px-0.5 whitespace-nowrap",
        direction === "up" && "animate-flash-up",
        direction === "down" && "animate-flash-down",
        className
      )}
    >
      {children}
    </span>
  )
}
