import { NextResponse } from "next/server";

// Using the non-null assertion (!) or providing a fallback string ('') 
// fixes the "string | undefined is not assignable to string" error.
const N8N_BASE_URL = process.env.N8N_BASE_URL || "";
const N8N_API_KEY = process.env.N8N_API_KEY || "";

export async function GET() {
  // Guard clause to catch configuration issues early
  if (!N8N_BASE_URL || !N8N_API_KEY) {
    console.error("CRITICAL ERROR: Environment variables N8N_BASE_URL or N8N_API_KEY are missing.");
    return NextResponse.json({ error: "Server configuration missing" }, { status: 500 });
  }
  try {
    let allWorkflows: any[] = []
    let nextCursor: string | null = null
    let hasMore = true

    while (hasMore) {
      // Construct URL - Only add cursor if we have one
      const url = new URL(`${N8N_BASE_URL}/workflows`)
      url.searchParams.append('limit', '100')
      if (nextCursor) {
        url.searchParams.append('cursor', nextCursor)
      }

      const response = await fetch(url.toString(), {
        method: 'GET',
        headers: {
          'X-N8N-API-KEY': N8N_API_KEY,
          Accept: 'application/json',
        },
        cache: 'no-store',
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        console.error(`n8n API Error:`, errorData)
        throw new Error(`n8n error: ${response.status}`)
      }

      const result = await response.json()

      // n8n Cursor logic: result.data contains the list, result.nextCursor contains the pointer
      const workflows = result.data || []
      allWorkflows = [...allWorkflows, ...workflows]

      // Update cursor for next loop
      nextCursor = result.nextCursor || null

      // If there's no nextCursor, we are finished
      if (!nextCursor) {
        hasMore = false
      }

      // Safety limit to prevent runaway loops
      if (allWorkflows.length > 2000) break
    }

    return NextResponse.json(allWorkflows)
  } catch (error: any) {
    console.error('Pagination Error:', error.message)
    return NextResponse.json({ error: error.message }, { status: 500 })
  }
}

export async function POST(req: Request) {
  try {
    const { workflowId, action, activeState } = await req.json()

    // 1. Triggering an execution
    if (action === 'trigger') {
      const response = await fetch(
        `${N8N_BASE_URL}/workflows/${workflowId}/execute`,
        {
          method: 'POST',
          headers: {
            'X-N8N-API-KEY': N8N_API_KEY,
            'Content-Type': 'application/json',
          },
        }
      )
      return NextResponse.json({ success: response.ok })
    }

    // 2. Activating or Deactivating
    if (action === 'toggle') {
      // n8n v1 uses specialized endpoints for status changes
      const toggleAction = activeState ? 'activate' : 'deactivate'
      const url = `${N8N_BASE_URL}/workflows/${workflowId}/${toggleAction}`

      console.log(`Sending ${toggleAction} request to: ${url}`)

      const response = await fetch(url, {
        method: 'POST', // Status changes in n8n are usually POST actions to these sub-resources
        headers: {
          'X-N8N-API-KEY': N8N_API_KEY,
          Accept: 'application/json',
        },
      })

      if (!response.ok) {
        const errorText = await response.text()
        console.error(`n8n Toggle Error (${response.status}):`, errorText)
        // Return the actual status so the frontend knows it failed
        return NextResponse.json(
          { error: 'n8n rejected status change' },
          { status: response.status }
        )
      }

      return NextResponse.json({ success: true })
    }

    return NextResponse.json({ error: 'Invalid action' }, { status: 400 })
  } catch (error) {
    console.error('Internal API Error:', error)
    return NextResponse.json({ error: 'Server Error' }, { status: 500 })
  }
}
