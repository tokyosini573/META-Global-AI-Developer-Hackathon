import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { Landing } from './components/Landing'

// The bare address opens the front page; any parameter (?replay, ?new, ?backtest, ?day, ...) opens the stage
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {location.search ? <App /> : <Landing />}
  </StrictMode>,
)
