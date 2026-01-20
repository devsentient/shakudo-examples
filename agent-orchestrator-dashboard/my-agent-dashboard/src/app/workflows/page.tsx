'use client'

import { useState, useEffect, useMemo } from 'react'
import { N8nWorkflowCard } from '@/components/n8n-workflow-card'
import { Loader2, AlertCircle, RefreshCw, Search, Zap } from 'lucide-react'

export default function WorkflowsPage() {
  const [workflows, setWorkflows] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')

  // Fetch all workflows (This triggers the loop in your API route)
  async function fetchWorkflows() {
    setLoading(true)
    setError(false)
    try {
      const res = await fetch('/api/n8n')
      if (!res.ok) throw new Error('Failed to fetch')
      const data = await res.json()
      setWorkflows(data)
    } catch (err) {
      console.error('Fetch Error:', err)
      setError(true)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchWorkflows()
  }, [])

  // Optimized Search Filter
  const filteredWorkflows = useMemo(() => {
    return workflows.filter(
      (wf) =>
        wf.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        wf.id.toString().includes(searchQuery)
    )
  }, [searchQuery, workflows])

  return (
    <div className="mx-auto max-w-7xl space-y-8">
      {/* Header Section */}
      <div className="flex flex-col items-start justify-between gap-6 border-b border-slate-800 pb-8 md:flex-row md:items-center">
        <div>
          <h1 className="flex items-center gap-3 text-3xl font-bold tracking-tight text-white">
            Live Orchestrator
            {!loading && (
              <span className="rounded-full bg-indigo-600 px-2 py-1 text-[10px] font-bold tracking-tighter text-white uppercase">
                {workflows.length} Total
              </span>
            )}
          </h1>
          <p className="mt-1 flex items-center gap-2 text-slate-400">
            <Zap size={14} className="text-indigo-400" />
            Managing agent configurations from hyperplane.dev
          </p>
        </div>

        <div className="flex w-full items-center gap-3 md:w-auto">
          {/* Enhanced Search Input */}
          <div className="relative w-full md:w-96">
            <Search className="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              placeholder="Filter by agent name or ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-lg border border-slate-800 bg-slate-900 py-2.5 pr-4 pl-10 text-sm text-slate-200 shadow-inner transition-all placeholder:text-slate-600 focus:ring-2 focus:ring-indigo-500/50 focus:outline-none"
            />
          </div>

          <button
            onClick={fetchWorkflows}
            disabled={loading}
            className="rounded-lg border border-slate-800 bg-slate-900 p-2.5 text-slate-400 shadow-sm transition-all hover:bg-slate-800 hover:text-white disabled:opacity-50"
            title="Refresh Agents"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      {loading ? (
        <div className="flex h-96 flex-col items-center justify-center gap-4">
          <div className="relative flex items-center justify-center">
            <Loader2 className="h-12 w-12 animate-spin text-indigo-500" />
            <div className="absolute inset-0 h-12 w-12 rounded-full border-4 border-indigo-500/20"></div>
          </div>
          <p className="animate-pulse font-mono text-xs text-slate-500">
            PAGINATING DATABASE: RETRIEVING ALL AGENTS...
          </p>
        </div>
      ) : error ? (
        <div className="flex flex-col items-center gap-4 rounded-2xl border border-red-500/20 bg-red-500/5 p-8 text-center text-red-400">
          <AlertCircle size={48} />
          <div>
            <h3 className="text-xl font-bold">Connection to n8n Failed</h3>
            <p className="mt-1 max-w-md text-sm opacity-80">
              The system could not retrieve workflows. Please verify your n8n
              API Key and Instance URL.
            </p>
          </div>
          <button
            onClick={fetchWorkflows}
            className="rounded-full border border-red-500/40 bg-red-500/10 px-6 py-2 text-xs font-bold transition-all hover:bg-red-500/20"
          >
            Retry Connection
          </button>
        </div>
      ) : (
        <>
          {filteredWorkflows.length === 0 ? (
            <div className="rounded-3xl border-2 border-dashed border-slate-900 py-32 text-center">
              <p className="font-medium text-slate-500">
                No agents match "{searchQuery}"
              </p>
              <button
                onClick={() => setSearchQuery('')}
                className="mt-2 text-xs text-indigo-400 hover:underline"
              >
                Clear search filter
              </button>
            </div>
          ) : (
            <div className="grid gap-6 sm:grid-cols-1 md:grid-cols-2 xl:grid-cols-3">
              {filteredWorkflows.map((wf) => (
                <N8nWorkflowCard
                  key={wf.id}
                  workflow={{
                    id: wf.id,
                    name: wf.name,
                    description: `v${wf.version || '1.0'} · Updated ${new Date(wf.updatedAt).toLocaleDateString()}`,
                    isActive: wf.active,
                  }}
                />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
