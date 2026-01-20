import { LayoutDashboard, Zap, Bot, Settings } from 'lucide-react'
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarMenu,
  SidebarMenuButton,
} from './ui/sidebar'
import Link from 'next/link'

export function AppSidebar() {
  return (
    <Sidebar className="w-64 border-r border-slate-800 bg-slate-950">
      <SidebarContent>
        <SidebarGroup>
          <div className="flex items-center gap-2 px-4 py-6 text-xl font-bold tracking-tight text-white">
            <Bot className="text-indigo-500" /> AgentOS
          </div>
          <SidebarMenu>
            <SidebarMenuButton className="bg-slate-900 text-white">
              <LayoutDashboard size={18} /> Dashboard
            </SidebarMenuButton>
            <SidebarMenuButton>
              <Bot size={18} /> Orchestrator
            </SidebarMenuButton>
            <Link href="/workflows">
              <SidebarMenuButton>
                <Zap size={18} className="text-yellow-500" /> N8N Agents
              </SidebarMenuButton>
            </Link>
            <SidebarMenuButton>
              <Settings size={18} /> Settings
            </SidebarMenuButton>
          </SidebarMenu>
        </SidebarGroup>
      </SidebarContent>
    </Sidebar>
  )
}
