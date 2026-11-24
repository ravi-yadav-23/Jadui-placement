'use client'

import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { Loader2, Upload } from 'lucide-react'

import { cn } from '@/lib/utils'
import { useUploadResume } from '../hooks'
import { ErrorBox } from './ui'

const ACCEPT = {
  'application/pdf': ['.pdf'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
}

/** Drop a PDF/DOCX -> upload -> go to the resume page, which polls until processing is done. */
export default function UploadDropzone() {
  const router = useRouter()
  const upload = useUploadResume()
  const [title, setTitle] = useState('')

  const { getRootProps, getInputProps, isDragActive, fileRejections } = useDropzone({
    accept: ACCEPT,
    maxFiles: 1,
    maxSize: 5 * 1024 * 1024,
    disabled: upload.isPending,
    onDropAccepted: ([file]) =>
      upload.mutate({ file, title: title.trim() || undefined }, {
        onSuccess: (resume) => router.push(`/dashboard/resume/${resume.id}`),
      }),
  })

  return (
    <div className="card-base space-y-4">
      <input
        className="input-base"
        placeholder="Version name (optional), e.g. SDE resume v2"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
      />
      <div
        {...getRootProps()}
        data-testid="upload-dropzone"
        className={cn('cursor-pointer rounded-xl border-2 border-dashed p-8 text-center transition-colors',
          isDragActive ? 'border-primary bg-primary/10' : 'border-border hover:border-primary/50')}
      >
        <input {...getInputProps()} />
        {upload.isPending ? (
          <Loader2 className="mx-auto h-8 w-8 animate-spin text-primary" />
        ) : (
          <Upload className="mx-auto h-8 w-8 text-primary" />
        )}
        <p className="mt-3 font-medium text-white">{upload.isPending ? 'Uploading…' : 'Drop your resume here'}</p>
        <p className="mt-1 text-sm text-muted">PDF or DOCX · max 5 MB · max 3 pages</p>
      </div>
      {fileRejections.length > 0 && <ErrorBox error={new Error('Only PDF or DOCX files up to 5 MB.')} />}
      {upload.error && <ErrorBox error={upload.error} />}
    </div>
  )
}
