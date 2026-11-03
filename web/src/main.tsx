import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { Landing } from './components/Landing'
import { Setup } from './components/Setup'

// The bare address opens the front page; ?new opens the Setup page (a scrolling page like the front
// page); any other parameter (?replay, ?report, ?ads, ?backtest, ?day, ...) opens the stage
const q = new URLSearchParams(location.search)
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {q.has('new') ? <Setup /> : location.search ? <App /> : <Landing />}
  </StrictMode>,
)
