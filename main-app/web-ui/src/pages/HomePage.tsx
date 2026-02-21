import { useState, useEffect, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Video, RefreshCw, Plus, RotateCcw, AlertCircle, CheckCircle2, Clock, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'
import {
  createJob,
  getJobs,
  getJob,
  deleteJob,
  generateScript,
  updateScript,
  regenerateScene,
  approveAndGenerate,
  retryJob,
  resetJob,
  Job,
  Scene,
} from '../api/client'
import {
  PromptForm,
  ScriptEditor,
  ProgressDisplay,
  VideoPlayer,
  JobHistory,
} from '../components'
import { useStore } from '../store'
import { useWebSocket } from '../hooks/useWebSocket'

export const HomePage = () => {
  const queryClient = useQueryClient()
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null)
  const { jobProgress, jobStatus, setCurrentJob } = useStore()
  
  useWebSocket(selectedJobId)

  // Jobs list: no polling. Refetched via WebSocket-triggered invalidation.
  const { data: jobs = [], isLoading: loadingJobs } = useQuery({
    queryKey: ['jobs'],
    queryFn: getJobs,
  })

  // Current job: no polling during processing (WebSocket handles real-time updates).
  // Only polls slowly for script_pending (since WebSocket may not be connected yet for new jobs).
  const { data: currentJob, refetch: refetchJob, isLoading: loadingJob } = useQuery({
    queryKey: ['job', selectedJobId],
    queryFn: () => selectedJobId ? getJob(selectedJobId) : null,
    enabled: !!selectedJobId,
    refetchInterval: (query) => {
      const data = query.state.data as Job | null | undefined
      if (!data) return false
      // Only poll for script_pending (WebSocket may not be connected yet)
      return data.status === 'script_pending' ? 5000 : false
    },
  })

  useEffect(() => {
    if (currentJob) {
      setCurrentJob(currentJob)
    }
  }, [currentJob, setCurrentJob])

  const createJobMutation = useMutation({
    mutationFn: async (prompt: string) => {
      const job = await createJob(prompt)
      await generateScript(job.id)
      return job
    },
    onSuccess: (job) => {
      setSelectedJobId(job.id)
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      toast.success('Video creation started!')
    },
    onError: (error: Error) => {
      toast.error(`Failed to create video: ${error.message}`)
    },
  })

  const deleteJobMutation = useMutation({
    mutationFn: deleteJob,
    onSuccess: () => {
      if (selectedJobId) {
        setSelectedJobId(null)
        setCurrentJob(null)
      }
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      toast.success('Job deleted')
    },
    onError: (error: Error) => {
      toast.error(`Failed to delete: ${error.message}`)
    },
  })

  const updateScriptMutation = useMutation({
    mutationFn: async ({ jobId, scenes }: { jobId: string; scenes: Scene[] }) => {
      return updateScript(jobId, { scenes })
    },
    onSuccess: () => {
      refetchJob()
      toast.success('Script updated')
    },
    onError: (error: Error) => {
      toast.error(`Failed to update script: ${error.message}`)
    },
  })

  const regenerateSceneMutation = useMutation({
    mutationFn: async ({ jobId, sceneId, feedback }: { jobId: string; sceneId: number; feedback?: string }) => {
      return regenerateScene(jobId, sceneId, feedback)
    },
    onSuccess: () => {
      refetchJob()
      toast.success('Scene regenerated')
    },
    onError: (error: Error) => {
      toast.error(`Failed to regenerate scene: ${error.message}`)
    },
  })

  const approveMutation = useMutation({
    mutationFn: (jobId: string) => approveAndGenerate(jobId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      toast.success('Video generation started!')
    },
    onError: (error: Error) => {
      toast.error(`Failed to start generation: ${error.message}`)
    },
  })

  const retryMutation = useMutation({
    mutationFn: (jobId: string) => retryJob(jobId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      refetchJob()
      toast.success('Retrying job...')
    },
    onError: (error: Error) => {
      toast.error(`Failed to retry: ${error.message}`)
    },
  })

  const resetMutation = useMutation({
    mutationFn: (jobId: string) => resetJob(jobId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      refetchJob()
      toast.success('Job reset to draft')
    },
    onError: (error: Error) => {
      toast.error(`Failed to reset: ${error.message}`)
    },
  })

  const handleUpdateScene = useCallback((sceneId: number, updates: Partial<Scene>) => {
    if (!currentJob?.script?.scenes) return
    
    const updatedScenes = currentJob.script.scenes.map((scene) =>
      scene.id === sceneId ? { ...scene, ...updates } : scene
    )
    
    updateScriptMutation.mutate({
      jobId: currentJob.id,
      scenes: updatedScenes,
    })
  }, [currentJob, updateScriptMutation])

  const handleRegenerateScene = useCallback((sceneId: number, feedback?: string) => {
    if (!currentJob) return
    regenerateSceneMutation.mutate({
      jobId: currentJob.id,
      sceneId,
      feedback,
    })
  }, [currentJob, regenerateSceneMutation])

  const handleApprove = useCallback(() => {
    if (!currentJob) return
    approveMutation.mutate(currentJob.id)
  }, [currentJob, approveMutation])

  const handleRetry = useCallback(() => {
    if (!currentJob) return
    retryMutation.mutate(currentJob.id)
  }, [currentJob, retryMutation])

  const handleReset = useCallback(() => {
    if (!currentJob) return
    if (confirm('Reset this job to draft? This will clear all progress.')) {
      resetMutation.mutate(currentJob.id)
    }
  }, [currentJob, resetMutation])

  const handleSelectJob = useCallback((job: Job) => {
    setSelectedJobId(job.id)
  }, [])

  const handleDeleteJob = useCallback((jobId: string) => {
    deleteJobMutation.mutate(jobId)
  }, [deleteJobMutation])

  const handleNewVideo = useCallback(() => {
    setSelectedJobId(null)
    setCurrentJob(null)
  }, [setCurrentJob])

  const currentStatus = selectedJobId ? (jobStatus[selectedJobId] || currentJob?.status) : null
  const currentProgress = selectedJobId ? jobProgress[selectedJobId] : undefined

  // Determine if job can be retried
  const canRetry = currentJob && ['failed', 'processing', 'script_pending', 'approved'].includes(currentJob.status)
  const canReset = currentJob && currentJob.status !== 'draft'

  const renderMainContent = () => {
    // Loading state
    if (loadingJob && selectedJobId) {
      return (
        <div className="card flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-blue-400" />
          <span className="ml-3 text-gray-400">Loading job...</span>
        </div>
      )
    }

    if (!currentJob) {
      return (
        <PromptForm
          onSubmit={(prompt) => createJobMutation.mutate(prompt)}
          isLoading={createJobMutation.isPending}
        />
      )
    }

    switch (currentStatus) {
      case 'script_ready':
        return currentJob.script ? (
          <ScriptEditor
            script={currentJob.script}
            onUpdateScene={handleUpdateScene}
            onRegenerateScene={handleRegenerateScene}
            onApprove={handleApprove}
            isRegenerating={regenerateSceneMutation.isPending}
            isApproving={approveMutation.isPending}
          />
        ) : null

      case 'approved':
      case 'processing':
        return (
          <ProgressDisplay
            status={currentStatus}
            progress={currentProgress}
            steps={currentJob.steps}
          />
        )

      case 'completed':
        return currentJob.output_url ? (
          <VideoPlayer videoUrl={currentJob.output_url} jobId={currentJob.id} />
        ) : (
          <div className="card text-center py-8">
            <CheckCircle2 className="w-12 h-12 mx-auto mb-3 text-green-400" />
            <h2 className="text-xl font-semibold mb-2">Video Completed</h2>
            <p className="text-gray-400">Video is ready but URL not available. Try refreshing.</p>
          </div>
        )

      case 'failed':
        return (
          <div className="card">
            <div className="flex items-start gap-4 mb-6">
              <div className="p-3 bg-red-500/10 rounded-full">
                <AlertCircle className="w-8 h-8 text-red-400" />
              </div>
              <div className="flex-1">
                <h2 className="text-xl font-semibold text-red-400 mb-2">Generation Failed</h2>
                <p className="text-gray-400 text-sm mb-4">
                  {currentJob.error_message || 'An unknown error occurred'}
                </p>
                
                {/* Show completed steps */}
                {currentJob.steps && currentJob.steps.length > 0 && (
                  <div className="mb-4">
                    <h3 className="text-sm font-medium text-gray-300 mb-2">Progress before failure:</h3>
                    <div className="space-y-1">
                      {currentJob.steps.map((step) => (
                        <div key={step.id} className="flex items-center gap-2 text-sm">
                          {step.status === 'completed' ? (
                            <CheckCircle2 className="w-4 h-4 text-green-400" />
                          ) : step.status === 'failed' ? (
                            <AlertCircle className="w-4 h-4 text-red-400" />
                          ) : (
                            <Clock className="w-4 h-4 text-gray-500" />
                          )}
                          <span className={step.status === 'completed' ? 'text-green-400' : step.status === 'failed' ? 'text-red-400' : 'text-gray-500'}>
                            {step.step_name.replace(/_/g, ' ')}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
            
            <div className="flex gap-3">
              <button
                onClick={handleRetry}
                disabled={retryMutation.isPending}
                className="btn-primary flex-1 flex items-center justify-center gap-2"
              >
                {retryMutation.isPending ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <RotateCcw className="w-4 h-4" />
                )}
                Retry from Last Step
              </button>
              <button
                onClick={handleReset}
                disabled={resetMutation.isPending}
                className="btn-secondary flex items-center justify-center gap-2"
              >
                Reset to Draft
              </button>
            </div>
          </div>
        )

      case 'script_pending':
        return (
          <div className="card">
            <div className="flex items-center gap-4 mb-6">
              <div className="p-3 bg-blue-500/10 rounded-full">
                <RefreshCw className="w-8 h-8 animate-spin text-blue-400" />
              </div>
              <div>
                <h2 className="text-xl font-semibold">Generating Script</h2>
                <p className="text-gray-400 text-sm">Our AI is creating a detailed script for your video...</p>
              </div>
            </div>
            
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <div className="w-6 h-6 rounded-full bg-blue-500 flex items-center justify-center">
                  <Loader2 className="w-4 h-4 animate-spin text-white" />
                </div>
                <span className="text-sm">Enhancing your prompt...</span>
              </div>
              <div className="flex items-center gap-3 opacity-50">
                <div className="w-6 h-6 rounded-full bg-gray-600 flex items-center justify-center">
                  <span className="text-xs">2</span>
                </div>
                <span className="text-sm text-gray-400">Generating scene-by-scene script</span>
              </div>
            </div>
            
            <p className="text-xs text-gray-500 mt-6">
              This usually takes 30-90 seconds depending on the complexity...
            </p>
          </div>
        )

      case 'draft':
        return (
          <div className="card">
            <div className="flex items-center gap-4 mb-4">
              <div className="p-3 bg-gray-700 rounded-full">
                <Clock className="w-6 h-6 text-gray-400" />
              </div>
              <div>
                <h2 className="text-xl font-semibold">Draft Job</h2>
                <p className="text-gray-400 text-sm">This job hasn't started yet</p>
              </div>
            </div>
            <button
              onClick={handleRetry}
              disabled={retryMutation.isPending}
              className="btn-primary w-full flex items-center justify-center gap-2"
            >
              {retryMutation.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <RefreshCw className="w-4 h-4" />
              )}
              Start Script Generation
            </button>
          </div>
        )

      default:
        return (
          <PromptForm
            onSubmit={(prompt) => createJobMutation.mutate(prompt)}
            isLoading={createJobMutation.isPending}
          />
        )
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-900 to-gray-800">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-900/80 backdrop-blur-lg sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-500/10 rounded-xl">
                <Video className="w-7 h-7 text-blue-400" />
              </div>
              <div>
                <h1 className="text-xl font-bold">Video Creator</h1>
                <p className="text-xs text-gray-500">AI-Powered Video Generation</p>
              </div>
            </div>
            <button
              onClick={handleNewVideo}
              className="btn-primary flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              New Video
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Panel */}
          <div className="lg:col-span-2 space-y-4">
            {/* Current Job Actions Bar */}
            {currentJob && (
              <div className="flex items-center justify-between bg-gray-800/50 rounded-lg px-4 py-2">
                <div className="flex items-center gap-2">
                  <span className="text-sm text-gray-400">Job:</span>
                  <span className="text-sm font-mono text-gray-300">{currentJob.id.slice(0, 8)}...</span>
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                    currentJob.status === 'completed' ? 'bg-green-500/20 text-green-400' :
                    currentJob.status === 'failed' ? 'bg-red-500/20 text-red-400' :
                    currentJob.status === 'processing' ? 'bg-yellow-500/20 text-yellow-400' :
                    'bg-gray-500/20 text-gray-400'
                  }`}>
                    {currentJob.status.replace(/_/g, ' ')}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  {canRetry && currentJob.status !== 'processing' && (
                    <button
                      onClick={handleRetry}
                      disabled={retryMutation.isPending}
                      className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1"
                      title="Retry from last step"
                    >
                      <RotateCcw className="w-3 h-3" />
                      Retry
                    </button>
                  )}
                </div>
              </div>
            )}
            
            {/* Main Content */}
            {renderMainContent()}
          </div>
          
          {/* Sidebar */}
          <div className="space-y-4">
            <JobHistory
              jobs={jobs}
              onSelectJob={handleSelectJob}
              onDeleteJob={handleDeleteJob}
              onRetryJob={(jobId) => retryMutation.mutate(jobId)}
              selectedJobId={selectedJobId || undefined}
              isLoading={loadingJobs}
            />
          </div>
        </div>
      </main>
    </div>
  )
}
