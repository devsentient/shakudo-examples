// src/hooks/use-toast.ts
import { useState } from 'react'

export function useToast() {
  const toast = ({
    title,
    description,
  }: {
    title: string
    description: string
  }) => {
    // For now, we'll log it. We can add a fancy UI popup later.
    console.log(`Notification: ${title} - ${description}`)
  }
  return { toast }
}
