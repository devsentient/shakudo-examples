import * as React from 'react'
import { cn } from '@/lib/utils'

export const Sidebar = ({
  className,
  children,
}: {
  className?: string
  children: React.ReactNode
}) => (
  <aside
    className={cn(
      'flex h-full w-64 flex-col border-r bg-slate-950 text-slate-300',
      className
    )}
  >
    {children}
  </aside>
)

export const SidebarContent = ({ children }: { children: React.ReactNode }) => (
  <div className="flex flex-1 flex-col overflow-y-auto p-4">{children}</div>
)

export const SidebarGroup = ({ children }: { children: React.ReactNode }) => (
  <div className="space-y-4">{children}</div>
)

export const SidebarMenu = ({ children }: { children: React.ReactNode }) => (
  <nav className="space-y-1">{children}</nav>
)

export const SidebarMenuButton = ({ children, className }: any) => (
  <button
    className={cn(
      'flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors hover:bg-slate-900 hover:text-white',
      className
    )}
  >
    {children}
  </button>
)
