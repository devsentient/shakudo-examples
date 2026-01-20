'use client'
import { useState } from 'react'
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  Play,
  Power,
  PowerOff,
  Loader2,
  Terminal,
  Activity,
} from 'lucide-react'
import { useToast } from '@/hooks/use-toast'

export function N8nWorkflowCard({ workflow }: { workflow: any }) {
  const [isTriggering, setIsTriggering] = useState(false)
  const [isDeploying, setIsDeploying] = useState(false)
  const [isActive, setIsActive] = useState(workflow.isActive)
  const { toast } = useToast()

  const handleTrigger = async () => {
    setIsTriggering(true)
    try {
      const res = await fetch('/api/n8n', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ workflowId: workflow.id, action: 'trigger' }),
      })
      if (res.ok) toast({ title: 'Success', description: 'Workflow executed!' })
    } catch (e) {
      toast({ title: 'Error', description: 'Failed to trigger.' })
    } finally {
      setIsTriggering(false)
    }
  }

  const handleToggleStatus = async () => {
    setIsDeploying(true)
    const newState = !isActive
    try {
      const res = await fetch('/api/n8n', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          workflowId: workflow.id,
          action: 'toggle',
          activeState: newState,
        }),
      })
      if (res.ok) {
        setIsActive(newState)
        toast({
          title: newState ? 'Deployed' : 'Stopped',
          description: 'Workflow updated.',
        })
      }
    } catch (e) {
      toast({ title: 'Error', description: 'Update failed.' })
    } finally {
      setIsDeploying(false)
    }
  }

  const baseBtnStyle = {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '12px',
    fontWeight: 'bold',
    borderRadius: '6px',
    padding: '8px 12px',
    border: 'none',
    cursor: 'pointer',
    transition: 'all 0.2s',
    width: '100%',
  }

  return (
    <Card
      className={`border-slate-800 bg-slate-900/50 transition-all ${isActive ? 'ring-1 ring-indigo-500/30' : 'opacity-70'}`}
    >
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <Badge
            variant="outline"
            className={
              isActive
                ? 'border-indigo-500/20 bg-indigo-500/10 text-indigo-400'
                : 'border-slate-700 bg-slate-800 text-slate-400'
            }
          >
            {isActive ? 'Deployed' : 'Paused'}
          </Badge>
          <span className="font-mono text-[10px] text-slate-500 uppercase">
            {workflow.id}
          </span>
        </div>

        <div className="mt-2 flex items-center gap-2">
          {/* THE LIVE SIGNAL PULSE */}
          {isActive && (
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-indigo-400 opacity-75"></span>
              <span className="relative inline-flex h-2 w-2 rounded-full bg-indigo-500"></span>
            </span>
          )}
          <CardTitle className="truncate text-lg text-white">
            {workflow.name}
          </CardTitle>
        </div>

        <CardDescription className="text-xs text-slate-400">
          {workflow.description}
        </CardDescription>
      </CardHeader>

      <CardContent>
        <div className="flex items-center gap-2 rounded bg-black/30 p-2 font-mono text-[11px] text-slate-500">
          <Terminal
            size={12}
            className={isActive ? 'text-indigo-400' : 'text-slate-600'}
          />
          <span>System ID: {workflow.id}</span>
        </div>
      </CardContent>

      <CardFooter className="grid grid-cols-2 gap-3">
        <button
          onClick={handleTrigger}
          disabled={!isActive || isTriggering}
          style={{
            ...baseBtnStyle,
            backgroundColor: !isActive || isTriggering ? '#1e293b' : '#4f46e5',
            color: !isActive || isTriggering ? '#64748b' : '#ffffff',
          }}
        >
          {isTriggering ? (
            <Loader2 className="mr-2 animate-spin" size={14} />
          ) : (
            <Play size={14} className="mr-2" style={{ fill: 'currentColor' }} />
          )}
          Trigger
        </button>

        <button
          onClick={handleToggleStatus}
          disabled={isDeploying}
          style={{
            ...baseBtnStyle,
            backgroundColor: isActive ? '#9f1239' : '#10b981',
            color: '#ffffff',
          }}
        >
          {isDeploying ? (
            <Loader2 className="mr-2 animate-spin" size={14} />
          ) : isActive ? (
            <>
              <PowerOff size={14} className="mr-2" /> Stop
            </>
          ) : (
            <>
              <Power size={14} className="mr-2" /> Deploy
            </>
          )}
        </button>
      </CardFooter>
    </Card>
  )
}
