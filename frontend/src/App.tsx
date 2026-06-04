import { useState, useCallback } from 'react'
import type { ChatSession, Contract, Message } from './types'
import { MOCK_CONTRACTS, MOCK_SESSIONS, getMockResponse } from './data/mockData'
import Sidebar from './components/Sidebar'
import ChatArea from './components/ChatArea'
import UploadPanel from './components/UploadPanel'

function generateId() {
  return `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
}

function sessionTitle(question: string): string {
  const q = question.trim()
  if (q.length <= 48) return q
  return q.slice(0, 45) + '…'
}

export default function App() {
  const [sessions, setSessions]             = useState<ChatSession[]>(MOCK_SESSIONS)
  const [activeSessionId, setActiveSession] = useState<string | null>(MOCK_SESSIONS[0].id)
  const [contracts, setContracts]           = useState<Contract[]>(MOCK_CONTRACTS)
  const [contractFilter, setContractFilter] = useState<string | null>(MOCK_SESSIONS[0].contractFilter)
  const [isLoading, setIsLoading]           = useState(false)
  const [uploadOpen, setUploadOpen]         = useState(false)

  const activeSession = sessions.find(s => s.id === activeSessionId) ?? null

  // ── Create new session ──────────────────────────────────────────────────────
  const handleNewChat = useCallback(() => {
    const id = generateId()
    const session: ChatSession = {
      id,
      title: 'New Conversation',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      messages: [],
      contractFilter,
      previewText: '',
    }
    setSessions(prev => [session, ...prev])
    setActiveSession(id)
  }, [contractFilter])

  // ── Select session ──────────────────────────────────────────────────────────
  const handleSelectSession = useCallback((id: string) => {
    setActiveSession(id)
    const session = sessions.find(s => s.id === id)
    if (session) setContractFilter(session.contractFilter)
  }, [sessions])

  // ── Select contract filter ──────────────────────────────────────────────────
  const handleSelectContract = useCallback((id: string | null) => {
    setContractFilter(id)
  }, [])

  // ── Send message ────────────────────────────────────────────────────────────
  const handleSendMessage = useCallback(async (text: string) => {
    if (isLoading) return

    let sessionId = activeSessionId

    // If no session, create one on first message
    if (!sessionId) {
      sessionId = generateId()
      const newSession: ChatSession = {
        id: sessionId,
        title: sessionTitle(text),
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        messages: [],
        contractFilter,
        previewText: '',
      }
      setSessions(prev => [newSession, ...prev])
      setActiveSession(sessionId)
    }

    const userMsg: Message = {
      id: `msg_${generateId()}`,
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    }

    // Append user message
    setSessions(prev => prev.map(s =>
      s.id === sessionId
        ? {
            ...s,
            title: s.messages.length === 0 ? sessionTitle(text) : s.title,
            messages: [...s.messages, userMsg],
            updatedAt: new Date().toISOString(),
          }
        : s
    ))

    setIsLoading(true)

    // Simulate network delay
    const delay = 1200 + Math.random() * 1000
    await new Promise(r => setTimeout(r, delay))

    const responseTemplate = getMockResponse(text, contractFilter)

    // Stream the response word by word
    const words = responseTemplate.content.split(' ')
    const streamingId = `msg_${generateId()}`
    let streamedContent = ''

    const streamingMsg: Message = {
      ...responseTemplate,
      id: streamingId,
      content: '',
      isStreaming: true,
      timestamp: new Date().toISOString(),
    }

    setSessions(prev => prev.map(s =>
      s.id === sessionId ? { ...s, messages: [...s.messages, streamingMsg] } : s
    ))
    setIsLoading(false)

    // Stream words
    await new Promise<void>(resolve => {
      let idx = 0
      const interval = setInterval(() => {
        const chunkSize = Math.floor(Math.random() * 3) + 1
        idx = Math.min(idx + chunkSize, words.length)
        streamedContent = words.slice(0, idx).join(' ')

        setSessions(prev => prev.map(s =>
          s.id === sessionId
            ? {
                ...s,
                messages: s.messages.map(m =>
                  m.id === streamingId ? { ...m, content: streamedContent } : m
                ),
              }
            : s
        ))

        if (idx >= words.length) {
          clearInterval(interval)
          resolve()
        }
      }, 28)
    })

    // Finalise — remove streaming flag, add citations/meta
    setSessions(prev => prev.map(s =>
      s.id === sessionId
        ? {
            ...s,
            messages: s.messages.map(m =>
              m.id === streamingId
                ? { ...responseTemplate, id: streamingId, content: streamedContent, isStreaming: false }
                : m
            ),
            previewText: streamedContent.slice(0, 80) + (streamedContent.length > 80 ? '…' : ''),
            updatedAt: new Date().toISOString(),
          }
        : s
    ))
  }, [activeSessionId, contractFilter, isLoading])

  // ── Contract added via upload ────────────────────────────────────────────────
  const handleContractAdded = useCallback((contractId: string, fileName: string) => {
    setContracts(prev => {
      if (prev.find(c => c.id === contractId)) return prev
      const newContract: Contract = {
        id: contractId,
        displayName: fileName.replace(/\.[^.]+$/, '').replace(/_/g, ' '),
        fileName,
        status: 'search_only',
        uploadedAt: new Date().toISOString().split('T')[0],
        pageCount: 0,
        fileSize: '',
        graphReady: false,
      }
      return [...prev, newContract]
    })
  }, [])

  return (
    <div className="flex h-screen bg-ey-darker overflow-hidden">

      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        contracts={contracts}
        contractFilter={contractFilter}
        onNewChat={handleNewChat}
        onSelectSession={handleSelectSession}
        onSelectContract={handleSelectContract}
        onOpenUpload={() => setUploadOpen(true)}
      />

      <ChatArea
        session={activeSession}
        contracts={contracts}
        contractFilter={contractFilter}
        isLoading={isLoading}
        onSendMessage={handleSendMessage}
      />

      {uploadOpen && (
        <UploadPanel
          onClose={() => setUploadOpen(false)}
          onContractAdded={handleContractAdded}
        />
      )}
    </div>
  )
}
