import { type NextRequest } from 'next/server'
import { ChatClient } from 'dify-client'
import { v4 } from 'uuid'
import { API_KEY, API_URL, APP_ID } from '@/config'
import { jwtDecode } from 'jwt-decode';

const userPrefix = `user_${APP_ID}:`

export const getInfo = (request: NextRequest) => {
  const sessionId = request.cookies.get('session_id')?.value || v4()
  let user = userPrefix + sessionId
  const authHeader = request.headers.get('authorization')

  if (authHeader) {
    const token = authHeader.split(' ')[1]
    if (token) {
      const decodedToken: any = jwtDecode(token)
      if(decodedToken?.preferred_username) {
        user = decodedToken?.preferred_username  + ':' + sessionId;
      } else if(decodedToken?.email) {
        user = decodedToken?.email  + ':' + sessionId;
      }
    }
  }
  return {
    sessionId,
    user,
  }
}
export const setSession = (sessionId: string) => {
  return { 'Set-Cookie': `session_id=${sessionId}; SameSite=None; Secure` }
}

export const client = new ChatClient(API_KEY, API_URL || undefined)

export const cosntructClient = (specificCookies: string) => {
  // Ensure the cookie is included in fetch requests by the client
  const fetchWithCookie = (url: string, options: RequestInit = {}) => {
    return fetch(url, {
      ...options,
      credentials: 'include', // Ensure cookies are included
      headers: {
        ...options.headers,
        'Cookie': specificCookies, // Set specific cookies
      },
    })
  }
  const difyClient = new ChatClient({
    fetch: fetchWithCookie, // Use custom fetch function
    // Add any other initialization options if needed
  })

  return difyClient
}