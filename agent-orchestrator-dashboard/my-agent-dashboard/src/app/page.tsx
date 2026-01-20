// app/page.tsx
import { N8nTriggerCard } from '@/components/n8n-trigger-card'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Activity, Cpu, Globe, Zap } from 'lucide-react'

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      {/* Header Section */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">
          Agent Command Center
        </h1>
        <p className="text-muted-foreground mt-1">
          Monitor and dispatch your n8n autonomous workflows.
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatsCard
          title="Active Agents"
          value="12"
          icon={<BotIcon />}
          description="+2 since last hour"
        />
        <StatsCard
          title="Total Executions"
          value="1,284"
          icon={<ZapIcon />}
          description="99.8% success rate"
        />
        <StatsCard
          title="System Load"
          value="24%"
          icon={<CpuIcon />}
          description="Optimized"
        />
        <StatsCard
          title="Data Points"
          value="45.2k"
          icon={<GlobeIcon />}
          description="Synced across 4 nodes"
        />
      </div>

      {/* Orchestrator Section */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <h2 className="mb-4 flex items-center gap-2 text-xl font-semibold">
            <Zap className="h-5 w-5 text-yellow-500" /> Available Workflows
          </h2>
          <div className="grid gap-4 sm:grid-cols-2">
            <N8nTriggerCard
              name="Content Researcher"
              desc="Scrapes web data and generates SEO briefs via n8n."
              workflowId="wf_001"
            />
            <N8nTriggerCard
              name="Customer Support Bot"
              desc="Analyzes Zendesk tickets and suggests AI replies."
              workflowId="wf_002"
            />
          </div>
        </div>

        {/* System Logs / Feed Sidebar */}
        <Card className="bg-muted/30 border-none">
          <CardHeader>
            <CardTitle className="text-sm font-medium">
              Live Execution Logs
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4 font-mono text-[11px]">
              <div className="flex gap-2 text-emerald-500">
                <span className="opacity-50">[14:20:01]</span> Workflow wf_001
                started
              </div>
              <div className="flex gap-2 text-blue-500">
                <span className="opacity-50">[14:20:05]</span> Scraping target:
                google.com
              </div>
              <div className="text-muted-foreground flex gap-2">
                <span className="opacity-50">[14:21:10]</span> Processing AI
                Summary...
              </div>
              <div className="flex animate-pulse gap-2 text-yellow-500">
                <span className="opacity-50">[14:22:15]</span> Waiting for n8n
                callback...
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

// Small helper for Stats
function StatsCard({ title, value, icon, description }: any) {
  return (
    <Card className="border-border/50">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <div className="text-muted-foreground">{icon}</div>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        <p className="text-muted-foreground mt-1 text-xs">{description}</p>
      </CardContent>
    </Card>
  )
}

function BotIcon() {
  return <Activity className="h-4 w-4" />
}
function ZapIcon() {
  return <Zap className="h-4 w-4" />
}
function CpuIcon() {
  return <Cpu className="h-4 w-4" />
}
function GlobeIcon() {
  return <Globe className="h-4 w-4" />
}
