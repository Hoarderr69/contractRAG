import { useState } from 'react'
import {
  Plus, MessageSquare, FileText, ChevronDown, ChevronRight,
  Upload, CheckCircle2,
} from 'lucide-react'
import type { ChatSession, Contract } from '../types'

interface Props {
  sessions: ChatSession[]
  activeSessionId: string | null
  contracts: Contract[]
  contractFilter: string | null
  onNewChat: () => void
  onSelectSession: (id: string) => void
  onSelectContract: (id: string | null) => void
  onOpenUpload: () => void
}

function formatDate(iso: string) {
  const d = new Date(iso)
  const now = new Date()
  const diff = now.getTime() - d.getTime()
  if (diff < 86400000) return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  if (diff < 604800000) return d.toLocaleDateString([], { weekday: 'short' })
  return d.toLocaleDateString([], { month: 'short', day: 'numeric' })
}

export default function Sidebar({
  sessions, activeSessionId, contracts, contractFilter,
  onNewChat, onSelectSession, onSelectContract, onOpenUpload,
}: Props) {
  const [contractsExpanded, setContractsExpanded] = useState(true)

  return (
    <aside className="w-72 flex flex-col bg-ey-dark border-r border-ey-border flex-shrink-0 h-full">

      {/* ── Logo ── */}
      <div className="flex items-center gap-3 px-5 py-4 border-b border-ey-border">
        <div className="w-8 h-8 bg-ey-yellow flex items-center justify-center flex-shrink-0">
          <span className="text-ey-dark font-bold text-sm leading-none">EY</span>
        </div>
        <div>
          <p className="text-white font-semibold text-sm leading-tight">Contract360</p>
          <p className="text-ey-muted text-xs">Intelligence Platform</p>
        </div>
      </div>

      {/* ── New Chat button ── */}
      <div className="px-3 py-3">
        <button
          onClick={onNewChat}
          className="w-full flex items-center justify-center gap-2 px-3 py-2.5
                     bg-ey-yellow text-ey-dark font-semibold text-sm rounded
                     hover:bg-ey-yellow-dim transition-colors"
        >
          <Plus size={15} />
          New Conversation
        </button>
      </div>

      {/* ── Sessions ── */}
      <div className="flex-1 overflow-y-auto min-h-0">
        <p className="px-4 pt-1 pb-2 text-xs font-medium text-ey-muted uppercase tracking-wider">
          Recent
        </p>

        {sessions.length === 0 ? (
          <p className="px-4 py-3 text-xs text-ey-muted">No conversations yet.</p>
        ) : (
          <div className="space-y-0.5 px-2">
            {sessions.map(session => {
              const isActive = session.id === activeSessionId
              return (
                <button
                  key={session.id}
                  onClick={() => onSelectSession(session.id)}
                  className={`w-full text-left px-3 py-2.5 rounded group transition-colors ${
                    isActive
                      ? 'bg-ey-card border border-ey-border'
                      : 'hover:bg-ey-surface'
                  }`}
                >
                  <div className="flex items-start gap-2">
                    <MessageSquare
                      size={13}
                      className={`mt-0.5 flex-shrink-0 ${isActive ? 'text-ey-yellow' : 'text-ey-muted'}`}
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-1">
                        <p className={`text-xs font-medium truncate ${isActive ? 'text-white' : 'text-ey-light'}`}>
                          {session.title}
                        </p>
                        <span className="text-ey-muted text-[10px] flex-shrink-0">
                          {formatDate(session.updatedAt)}
                        </span>
                      </div>
                      <p className="text-ey-muted text-[11px] truncate mt-0.5">
                        {session.previewText}
                      </p>
                    </div>
                  </div>
                </button>
              )
            })}
          </div>
        )}

        {/* ── Contracts section ── */}
        <div className="mt-4 border-t border-ey-border pt-3">
          <button
            onClick={() => setContractsExpanded(v => !v)}
            className="w-full flex items-center justify-between px-4 py-1"
          >
            <p className="text-xs font-medium text-ey-muted uppercase tracking-wider">
              Contracts
            </p>
            {contractsExpanded
              ? <ChevronDown size={12} className="text-ey-muted" />
              : <ChevronRight size={12} className="text-ey-muted" />}
          </button>

          {contractsExpanded && (
            <div className="mt-1 space-y-0.5 px-2 animate-fade-in">

              {/* All contracts option */}
              <button
                onClick={() => onSelectContract(null)}
                className={`w-full text-left px-3 py-2 rounded transition-colors flex items-center gap-2 ${
                  contractFilter === null
                    ? 'bg-ey-card border border-ey-border'
                    : 'hover:bg-ey-surface'
                }`}
              >
                <div className="w-1.5 h-1.5 rounded-full bg-ey-yellow flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-ey-light font-medium">All Contracts</p>
                </div>
                {contractFilter === null && (
                  <CheckCircle2 size={12} className="text-ey-yellow flex-shrink-0" />
                )}
              </button>

              {contracts.map(contract => (
                <button
                  key={contract.id}
                  onClick={() => onSelectContract(contract.id)}
                  className={`w-full text-left px-3 py-2 rounded transition-colors ${
                    contractFilter === contract.id
                      ? 'bg-ey-card border border-ey-border'
                      : 'hover:bg-ey-surface'
                  }`}
                >
                  <div className="flex items-start gap-2">
                    <FileText size={12} className="text-ey-muted mt-0.5 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-ey-light font-medium truncate leading-snug">
                        {contract.displayName}
                      </p>
                      <p className="text-[10px] text-ey-muted mt-0.5">
                        {contract.pageCount > 0 ? `${contract.pageCount}p · ` : ''}{contract.fileSize}
                      </p>
                    </div>
                    {contractFilter === contract.id && (
                      <CheckCircle2 size={12} className="text-ey-yellow flex-shrink-0 mt-0.5" />
                    )}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* ── Upload button ── */}
      <div className="px-3 pb-4 pt-2 border-t border-ey-border">
        <button
          onClick={onOpenUpload}
          className="w-full flex items-center justify-center gap-2 px-3 py-2.5
                     border border-ey-border text-ey-light text-sm rounded
                     hover:border-ey-yellow hover:text-ey-yellow transition-colors"
        >
          <Upload size={14} />
          Upload Contract
        </button>
      </div>
    </aside>
  )
}
