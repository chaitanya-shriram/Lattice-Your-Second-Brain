import { useState } from 'react'
import { api } from './api'
import { useAppStore } from '../stores/useAppStore'

/** Shared file-upload flow (Dashboard drop zone + Files page both had their own copy). */
export function useFileUpload(onDone) {
  const [uploading, setUploading] = useState(false)
  const { addToast } = useAppStore()

  const upload = async (fileList) => {
    const files = Array.from(fileList || [])
    if (!files.length) return
    setUploading(true)
    for (const file of files) {
      try {
        await api.fileUpload(file)
        addToast(`Queued: ${file.name}`, 'success')
      } catch (e) {
        addToast(`Failed: ${file.name}`, 'error')
      }
    }
    setUploading(false)
    onDone?.()
  }

  return { uploading, upload }
}
