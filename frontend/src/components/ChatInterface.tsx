import { useState, useEffect, useRef } from 'react'
import { useWebSocket } from '../services/websocket'
import './ChatInterface.css'

interface ChatInterfaceProps {
  clientId: string
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({ clientId }) => {
  const [inputText, setInputText] = useState('')
  const [messages, setMessages] = useState<Array<{ type: 'user' | 'ai', text: string, timestamp: Date }>>([])
  const [isRecording, setIsRecording] = useState(false)
  const [status, setStatus] = useState<'idle' | 'thinking' | 'speaking'>('idle')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)

  const { 
    connected, 
    sendMessage, 
    currentExpression,
    onAudioChunk 
  } = useWebSocket(clientId, {
    onTextResponse: (text: string, emotion: string, expression: string) => {
      setMessages(prev => [...prev, {
        type: 'ai',
        text,
        timestamp: new Date()
      }])
      setStatus('speaking')
    },
    onStatusChange: (newStatus: string) => {
      if (newStatus === 'thinking') {
        setStatus('thinking')
      }
    },
    onAudioStart: () => {
      setStatus('speaking')
      if (!audioContextRef.current) {
        audioContextRef.current = new AudioContext()
      }
    },
    onAudioEnd: () => {
      setStatus('idle')
    }
  })

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSendText = () => {
    if (!inputText.trim() || !connected) return

    setMessages(prev => [...prev, {
      type: 'user',
      text: inputText,
      timestamp: new Date()
    }])

    sendMessage({
      type: 'text_input',
      text: inputText
    })

    setInputText('')
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendText()
    }
  }

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm'
      })

      const chunks: Blob[] = []
      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunks.push(e.data)
        }
      }

      mediaRecorder.onstop = () => {
        const blob = new Blob(chunks, { type: 'audio/webm' })
        blob.arrayBuffer().then(buffer => {
          // Send audio to backend via WebSocket
          // For now, we'll use browser's Web Speech API as fallback
          sendMessage({
            type: 'audio_data',
            audio: Array.from(new Uint8Array(buffer))
          })
        })
        stream.getTracks().forEach(track => track.stop())
      }

      mediaRecorder.start()
      mediaRecorderRef.current = mediaRecorder
      setIsRecording(true)
    } catch (error) {
      console.error('Failed to start recording:', error)
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
    }
  }

  // Handle audio chunks from backend
  useEffect(() => {
    if (onAudioChunk) {
      const handleAudio = async (chunk: ArrayBuffer) => {
        if (!audioContextRef.current) return

        try {
          const audioBuffer = await audioContextRef.current.decodeAudioData(chunk)
          const source = audioContextRef.current.createBufferSource()
          source.buffer = audioBuffer
          source.connect(audioContextRef.current.destination)
          source.start()

          // Trigger lip-sync
          const canvas = document.querySelector('.live2d-canvas') as HTMLCanvasElement
          if (canvas && (canvas as any).handleLipSync) {
            ;(canvas as any).handleLipSync(chunk)
          }
        } catch (error) {
          console.error('Audio playback error:', error)
        }
      }

      // This would be set up in the WebSocket service
      // For now, it's a placeholder
    }
  }, [onAudioChunk])

  return (
    <div className="chat-interface">
      <div className="chat-header">
        <h3>数字人陪伴</h3>
        <div className={`connection-status ${connected ? 'connected' : 'disconnected'}`}>
          {connected ? '● 已连接' : '○ 未连接'}
        </div>
      </div>

      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="empty-state">
            <p>开始与数字人对话吧！</p>
            <p className="hint">你可以打字或使用语音输入</p>
          </div>
        )}
        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.type}`}>
            <div className="message-content">{msg.text}</div>
            <div className="message-time">
              {msg.timestamp.toLocaleTimeString()}
            </div>
          </div>
        ))}
        {status === 'thinking' && (
          <div className="message ai thinking">
            <div className="message-content">
              <span className="typing-indicator">正在思考...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-area">
        <div className="input-controls">
          <textarea
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="输入消息..."
            rows={2}
            className="text-input"
          />
          <div className="button-group">
            <button
              onClick={isRecording ? stopRecording : startRecording}
              className={`record-button ${isRecording ? 'recording' : ''}`}
              disabled={!connected}
            >
              {isRecording ? '⏹ 停止' : '🎤 录音'}
            </button>
            <button
              onClick={handleSendText}
              className="send-button"
              disabled={!inputText.trim() || !connected}
            >
              发送
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ChatInterface
