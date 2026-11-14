import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { HashRouter } from 'react-router-dom'
import './index.css'
import App from './App.tsx'

// 只有 Chromium 支援以 SVG 濾鏡作為 backdrop-filter，其他瀏覽器使用一般模糊玻璃
if (/Chrome\//.test(navigator.userAgent)) {
  document.documentElement.classList.add('lg-refract')
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <HashRouter>
      <App />
    </HashRouter>
  </StrictMode>,
)
