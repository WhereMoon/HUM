import { useState } from 'react'
import Live2DStage from './components/Live2DStage'
import ChatInterface from './components/ChatInterface'
import './App.css'

function App() {
  const [clientId] = useState(() => `client_${Date.now()}`)

  return (
    <div className="app">
      <div className="app-container">
        <Live2DStage clientId={clientId} />
        <ChatInterface clientId={clientId} />
      </div>
    </div>
  )
}

export default App
