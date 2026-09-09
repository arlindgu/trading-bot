import { useEffect, useRef, useState } from "react"

export type FlashDirection = "up" | "down" | null

/**
 * Tracks a polled numeric value and reports a one-shot direction + replay
 * key whenever it changes, so a consumer can retrigger a CSS animation via
 * `key={replayKey}` (remounting is what makes the keyframe animation replay
 * reliably, since polling ticks are seconds apart -- nowhere near frequent
 * enough to need transition-based retargeting).
 */
export function useFlashOnChange(value: number | null | undefined) {
  const [replayKey, setReplayKey] = useState(0)
  const [direction, setDirection] = useState<FlashDirection>(null)
  const previous = useRef(value)

  useEffect(() => {
    if (value == null || previous.current == null || value === previous.current) {
      previous.current = value
      return
    }
    setDirection(value > previous.current ? "up" : "down")
    setReplayKey((k) => k + 1)
    previous.current = value
  }, [value])

  return { direction, replayKey }
}
