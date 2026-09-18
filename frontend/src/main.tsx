import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './styles/nocturne.css'
import App from './App.tsx'
import { WatchlistProvider } from './hooks/useWatchlist'
import { ToastProvider } from './contexts/ToastContext'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <WatchlistProvider>
      <ToastProvider>
        <App />
      </ToastProvider>
    </WatchlistProvider>
  </StrictMode>,
)
