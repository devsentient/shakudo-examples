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
import { Play, Loader2, Terminal, CheckCircle } from 'lucide-react'
import { useToast } from '@/hooks/use-toast'

interface Props {
  name: string
  desc: string
  workflowId: string
}

export function N8nTriggerCard({ name, desc, workflowId }: Props) {
  const [status, setStatus] = useState<'idle' | 'loading' | 'success'>('idle')
  const { toast } = useToast()

  const handleTrigger = async () => {
    setStatus('loading')
    try {
      const response = await fetch('/api/n8n', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ workflowId, action: 'trigger' }),
      })
      if (!response.ok) throw new Error('Trigger failed')
      setStatus('success')
      toast({
        title: 'Workflow Dispatched',
        description: `${name} is now executing.`,
      })
    } catch (error) {
      setStatus('idle')
      toast({ title: 'Error', description: 'Failed to connect to n8n.' })
    } finally {
      setTimeout(() => setStatus('idle'), 3000)
    }
  }

  // Define colors manually to ensure they bypass global CSS
  const buttonStyle = {
    backgroundColor: status === 'success' ? '#10b981' : '#4f46e5', // Emerald-600 or Indigo-600
    color: '#ffffff',
    border: 'none',
    padding: '10px 16px',
    borderRadius: '6px',
    fontWeight: 'bold',
    fontSize: '12px',
    cursor: status === 'idle' ? 'pointer' : 'not-allowed',
    width: '100%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '8px',
    opacity: status === 'idle' ? 1 : 0.7,
    transition: 'background-color 0.2s',
  }

  return (
    <Card className="overflow-hidden border-slate-800 bg-slate-900/60 shadow-2xl backdrop-blur-md">
      <CardHeader className="pb-3 text-left">
        <div className="mb-2 flex items-start justify-between">
          <Badge
            variant="outline"
            className="border-indigo-500/20 bg-indigo-500/10 font-mono text-[10px] text-indigo-400"
          >
            {workflowId}
          </Badge>
          <div className="h-2 w-2 rounded-full bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.8)]" />
        </div>
        <CardTitle className="text-left text-lg font-bold text-white">
          {name}
        </CardTitle>
        <CardDescription className="mt-1 line-clamp-2 text-left text-xs text-slate-400 italic">
          {desc}
        </CardDescription>
      </CardHeader>

      <CardContent>
        <div className="flex items-center gap-2 rounded border border-slate-800/50 bg-black/50 p-2 font-mono text-[10px] text-slate-400">
          <Terminal size={12} className="text-indigo-400" />
          <span>STATUS: READY</span>
        </div>
      </CardContent>

      <CardFooter className="pt-2">
        <button
          onClick={handleTrigger}
          disabled={status !== 'idle'}
          style={buttonStyle}
        >
          {status === 'loading' ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : status === 'success' ? (
            <CheckCircle className="h-4 w-4" />
          ) : (
            <Play size={14} style={{ fill: 'white' }} />
          )}

          <span style={{ color: 'white' }}>
            {status === 'loading'
              ? 'Executing...'
              : status === 'success'
                ? 'Dispatched'
                : 'Run Workflow'}
          </span>
        </button>
      </CardFooter>
    </Card>
  )
}
