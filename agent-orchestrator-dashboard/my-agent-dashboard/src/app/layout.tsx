import type { Metadata } from 'next'
import { Geist, Geist_Mono } from 'next/font/google'
import './globals.css'
import { AppSidebar } from '@/components/app-sidebar'

const geistSans = Geist({ variable: '--font-geist-sans', subsets: ['latin'] })
const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
})

export const metadata: Metadata = {
  title: 'AgentOS | n8n Orchestrator',
  description: 'AI Agent Control Plane',
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        {/* Simple Flex Layout: Sidebar on left, Content on right */}
        <div className="flex h-screen w-full overflow-hidden bg-slate-950 text-slate-50">
          <AppSidebar />
          <main className="flex min-w-0 flex-1 flex-col overflow-hidden">
            <header className="flex h-14 items-center border-b border-slate-800 bg-slate-900/50 px-6">
              <span className="text-sm font-medium text-slate-400">
                Agent Command Center
              </span>
            </header>
            <div className="flex-1 overflow-y-auto p-6">{children}</div>
          </main>
        </div>
      </body>
    </html>
  )
}
