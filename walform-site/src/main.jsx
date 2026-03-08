import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import WalformSurfaces from './WalformSurfaces.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <WalformSurfaces />
  </StrictMode>
)