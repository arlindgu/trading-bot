import { StrictMode } from "react"
import { createRoot } from "react-dom/client"

import "./index.css"
import App from "./App.tsx"
import Leaderboard from "./Leaderboard.tsx"
import { ThemeProvider } from "@/components/theme-provider.tsx"

// No router library for what's a 2-page dashboard -- Flask already serves
// index.html for any path (SPA fallback), so a plain pathname check here
// is enough. Full navigation (<a href>) between the two, not client-side.
const page = window.location.pathname === "/leaderboard" ? <Leaderboard /> : <App />

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider>{page}</ThemeProvider>
  </StrictMode>
)
