import Link from 'next/link'
import { ArrowLeft, BookOpen, Sparkles } from 'lucide-react'

export default function TemplatesPage() {
  return (
    <main className="min-h-screen bg-studio-950 px-6 py-12 text-white">
      <div className="mx-auto max-w-6xl rounded-[2rem] bg-studio-850/96 p-8 shadow-chrome">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="obsidian-kicker">Templates</p>
            <h1 className="mt-2 text-3xl font-semibold">Executive formats</h1>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-studio-200/72">
              This route holds the reusable output structures. The flagship board memo experience is already integrated into the main drafting canvas.
            </p>
          </div>
          <Link href="/" className="obsidian-secondary-button">
            <ArrowLeft className="h-4 w-4" />
            Return to studio
          </Link>
        </div>
        <div className="mt-8 grid gap-4 md:grid-cols-2">
          <div className="rounded-[1rem] bg-studio-820/95 p-6 shadow-panel">
            <BookOpen className="h-5 w-5 text-primary" />
            <h2 className="mt-4 text-xl font-semibold">Board memo</h2>
            <p className="mt-2 text-sm leading-7 text-studio-200/72">Executive summary, background, analysis, recommendation, and risk assessment.</p>
          </div>
          <div className="rounded-[1rem] bg-studio-820/95 p-6 shadow-panel">
            <Sparkles className="h-5 w-5 text-accent-violet" />
            <h2 className="mt-4 text-xl font-semibold">Strategic brief</h2>
            <p className="mt-2 text-sm leading-7 text-studio-200/72">Condensed leadership format for quick alignment and follow-up action.</p>
          </div>
        </div>
      </div>
    </main>
  )
}
