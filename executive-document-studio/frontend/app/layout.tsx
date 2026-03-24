import type { Metadata } from 'next'
import { Inter, JetBrains_Mono } from 'next/font/google'

import './globals.css'

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
})

const mono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
})

export const metadata: Metadata = {
  title: 'GWL Memo Creation Studio',
  description: 'Premium enterprise drafting workspace for live AI-assisted GWL memo creation.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.variable} ${mono.variable} bg-studio-950 font-sans text-white antialiased`}>
        {children}
      </body>
    </html>
  )
}
