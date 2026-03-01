import { useState, useEffect, useRef, useCallback } from 'react'

interface WebSocketCallbacks {
  onTextResponse?: (text: string, emotion: string, expression: string) => void
  onStatusChange?: (status: string) => void
  onAudioStart?: (text: string) => void
  onAudioEnd?: () => void
  onError?: (error: string) => void
}

// Global state attached to window to survive HMR and component remounts
declare global {
    interface Window {
        _globalWs: WebSocket | null;
        _globalClientId: string | null;
        _globalAudioContext: AudioContext | null;
        _audioQueue: AudioBuffer[];
        _isPlaying: boolean;
    }
}

// Initialize global state if not exists
if (typeof window !== 'undefined') {
    window._globalWs = window._globalWs || null;
    window._globalClientId = window._globalClientId || null;
    window._globalAudioContext = window._globalAudioContext || null;
    window._audioQueue = window._audioQueue || [];
    window._isPlaying = window._isPlaying || false;
}

const getAudioContext = () => {
    if (!window._globalAudioContext) {
        const AudioContextClass = (window.AudioContext || (window as any).webkitAudioContext);
        window._globalAudioContext = new AudioContextClass();
    }
    if (window._globalAudioContext.state === 'suspended') {
        window._globalAudioContext.resume();
    }
    return window._globalAudioContext;
};

export const useWebSocket = (clientId: string, callbacks: WebSocketCallbacks = {}) => {
  const [connected, setConnected] = useState(false)
  const [currentExpression, setCurrentExpression] = useState('idle')
  
  // Use a ref to store callbacks so they don't trigger re-connection when they change
  const callbacksRef = useRef(callbacks)
  useEffect(() => {
    callbacksRef.current = callbacks
  }, [callbacks])

  const reconnectTimeoutRef = useRef<number | null>(null)

  const connect = useCallback(() => {
    // If we have a global connection for the same client ID, reuse it
    if (window._globalWs && window._globalClientId === clientId) {
        if (window._globalWs.readyState === WebSocket.OPEN) {
            setConnected(true);
            return;
        } else if (window._globalWs.readyState === WebSocket.CONNECTING) {
            return;
        }
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    let hostname = window.location.hostname
    if (hostname === 'localhost') hostname = '127.0.0.1'
    
    const wsUrl = `${protocol}//${hostname}:8000/ws/${clientId}`
    console.log(`Connecting to WebSocket: ${wsUrl}`)
    
    // Close existing connection if any
    if (window._globalWs) {
        window._globalWs.close();
    }

    const ws = new WebSocket(wsUrl)
    window._globalWs = ws;
    window._globalClientId = clientId;

    ws.onopen = () => {
      console.log('WebSocket connected')
      setConnected(true)
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
        reconnectTimeoutRef.current = null
      }
    }

    ws.onmessage = (event) => {
      if (typeof event.data === 'string') {
        try {
          const message = JSON.parse(event.data)
          handleMessage(message)
        } catch (error) {
          console.error('Failed to parse message:', error)
        }
      } else if (event.data instanceof Blob) {
        event.data.arrayBuffer().then(handleAudioData)
      } else if (event.data instanceof ArrayBuffer) {
        handleAudioData(event.data)
      }
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
      callbacksRef.current.onError?.('连接错误')
    }

    ws.onclose = (event) => {
      console.log('WebSocket disconnected', event.code, event.reason)
      setConnected(false)
      if (window._globalWs === ws) {
          window._globalWs = null;
      }
      
      if (event.code !== 1000) {
        console.log('Attempting to reconnect in 3s...')
        reconnectTimeoutRef.current = window.setTimeout(connect, 3000)
      }
    }
  }, [clientId])

  // Initial connection
  useEffect(() => {
    connect()
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      // Don't close global connection on unmount, let it persist
    }
  }, [connect])

  const handleMessage = (message: any) => {
    const cbs = callbacksRef.current
    switch (message.type) {
      case 'status':
        cbs.onStatusChange?.(message.status)
        break
      case 'text_response':
        cbs.onTextResponse?.(
          message.text,
          message.emotion || 'neutral',
          message.expression || 'idle'
        )
        setCurrentExpression(message.expression || 'idle')
        break
      case 'audio_start':
        cbs.onAudioStart?.(message.text)
        // Reset queue on new audio start
        window._audioQueue = [];
        window._isPlaying = false;
        break
      case 'audio_end':
        cbs.onAudioEnd?.()
        break
      case 'error':
        cbs.onError?.(message.message)
        break
    }
  }

  const handleAudioData = (buffer: ArrayBuffer) => {
    playAudioChunk(buffer)
  }

  const playAudioChunk = async (chunk: ArrayBuffer) => {
    try {
      const ctx = getAudioContext();
      // Decode the audio data (assuming it's a complete WAV segment now)
      const audioBuffer = await ctx.decodeAudioData(chunk.slice(0));
      
      window._audioQueue.push(audioBuffer);
      processAudioQueue();

      // Trigger lip-sync
      const canvas = document.querySelector('.live2d-canvas') as HTMLCanvasElement
      if (canvas && (canvas as any).handleLipSync) {
        ;(canvas as any).handleLipSync(chunk)
      }
    } catch (error) {
      console.error('Audio playback error:', error);
    }
  }

  const processAudioQueue = () => {
      if (window._isPlaying || window._audioQueue.length === 0) return;
      
      window._isPlaying = true;
      const buffer = window._audioQueue.shift()!;
      const ctx = getAudioContext();
      const source = ctx.createBufferSource();
      source.buffer = buffer;
      source.connect(ctx.destination);
      
      source.onended = () => {
          window._isPlaying = false;
          processAudioQueue(); // Play next chunk
      };
      
      source.start();
  };

  const sendMessage = useCallback((message: any) => {
    // Always use the globalWs instance
    if (window._globalWs && window._globalWs.readyState === WebSocket.OPEN) {
      window._globalWs.send(JSON.stringify(message))
    } else {
      console.warn('WebSocket not connected, cannot send message. ReadyState:', window._globalWs?.readyState)
      // Trigger reconnect if needed
      if (!window._globalWs || window._globalWs.readyState === WebSocket.CLOSED) {
          connect();
      }
    }
  }, [connect])

  return {
    connected,
    currentExpression,
    sendMessage
  }
}
