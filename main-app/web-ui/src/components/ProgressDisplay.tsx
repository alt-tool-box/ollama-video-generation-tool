import { Loader2, CheckCircle, XCircle, Image, Volume2, Film, Clock } from 'lucide-react'
import { JobStep } from '../api/client'

interface ProgressDisplayProps {
  status: string
  progress?: {
    step: string
    progress: number
    message?: string
  }
  error?: string
  steps?: JobStep[]
}

const STEPS = [
  { key: 'clip_generation', label: 'Generating Motion Clips', icon: Image, description: 'Creating animated video clips using AnimateDiff' },
  { key: 'tts_generation', label: 'Creating Audio', icon: Volume2, description: 'Converting narration to speech' },
  { key: 'video_rendering', label: 'Rendering Video', icon: Film, description: 'Combining clips and audio into final video' },
]

export const ProgressDisplay = ({ status, progress, error, steps }: ProgressDisplayProps) => {
  // Use database steps if available, otherwise use progress from websocket
  const getStepStatus = (stepKey: string) => {
    // Check database steps first
    if (steps && steps.length > 0) {
      let dbStep = steps.find(s => s.step_name === stepKey)
      // Backwards compatibility: old jobs used "image_generation", new ones use "clip_generation"
      if (!dbStep && stepKey === 'clip_generation') {
        dbStep = steps.find(s => s.step_name === 'image_generation')
      }
      if (dbStep) {
        return dbStep.status
      }
    }
    
    // Fallback to progress-based calculation
    if (!progress) return 'pending'
    
    const currentIndex = STEPS.findIndex(s => s.key === progress.step)
    const stepIndex = STEPS.findIndex(s => s.key === stepKey)
    
    if (stepIndex < currentIndex) return 'completed'
    if (stepIndex === currentIndex) {
      if (progress.progress === 100) return 'completed'
      return 'in_progress'
    }
    return 'pending'
  }

  const getStepProgress = (stepKey: string) => {
    if (steps && steps.length > 0) {
      let dbStep = steps.find(s => s.step_name === stepKey)
      // Backwards compatibility
      if (!dbStep && stepKey === 'clip_generation') {
        dbStep = steps.find(s => s.step_name === 'image_generation')
      }
      if (dbStep) return dbStep.progress
    }
    if (progress?.step === stepKey) return progress.progress
    return 0
  }

  // Calculate overall progress
  const completedSteps = STEPS.filter(s => getStepStatus(s.key) === 'completed').length
  const overallProgress = Math.round((completedSteps / STEPS.length) * 100)

  if (status === 'failed') {
    return (
      <div className="card border border-red-500/30">
        <div className="flex items-start gap-4">
          <div className="p-3 bg-red-500/10 rounded-full">
            <XCircle className="w-6 h-6 text-red-400" />
          </div>
          <div>
            <h3 className="font-semibold text-red-400">Generation Failed</h3>
            <p className="text-sm text-gray-400 mt-1">{error || 'An error occurred during video generation'}</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="card">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-semibold">Generating Your Video</h2>
          <p className="text-sm text-gray-400 mt-1">This may take a few minutes...</p>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold text-blue-400">{overallProgress}%</div>
          <div className="text-xs text-gray-500">Overall Progress</div>
        </div>
      </div>
      
      {/* Overall Progress Bar */}
      <div className="w-full bg-gray-700 rounded-full h-2 mb-8">
        <div
          className="bg-gradient-to-r from-blue-600 to-blue-400 h-2 rounded-full transition-all duration-500"
          style={{ width: `${overallProgress}%` }}
        />
      </div>
      
      {/* Steps */}
      <div className="space-y-6">
        {STEPS.map((step, index) => {
          const stepStatus = getStepStatus(step.key)
          const stepProgress = getStepProgress(step.key)
          const Icon = step.icon
          const isActive = stepStatus === 'in_progress'
          const isCompleted = stepStatus === 'completed'
          const isPending = stepStatus === 'pending'
          
          return (
            <div key={step.key} className="relative">
              {/* Connector Line */}
              {index < STEPS.length - 1 && (
                <div className={`absolute left-5 top-12 w-0.5 h-8 ${
                  isCompleted ? 'bg-green-500' : 'bg-gray-700'
                }`} />
              )}
              
              <div className="flex items-start gap-4">
                {/* Step Icon */}
                <div className={`
                  relative w-10 h-10 rounded-full flex items-center justify-center transition-all duration-300
                  ${isCompleted ? 'bg-green-500 shadow-lg shadow-green-500/30' : 
                    isActive ? 'bg-blue-600 shadow-lg shadow-blue-500/30' : 'bg-gray-700'}
                `}>
                  {isCompleted ? (
                    <CheckCircle className="w-5 h-5 text-white" />
                  ) : isActive ? (
                    <Loader2 className="w-5 h-5 text-white animate-spin" />
                  ) : (
                    <Icon className="w-5 h-5 text-gray-400" />
                  )}
                  
                  {/* Pulse animation for active step */}
                  {isActive && (
                    <div className="absolute inset-0 rounded-full bg-blue-500 animate-ping opacity-30" />
                  )}
                </div>
                
                {/* Step Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1">
                    <div>
                      <span className={`font-medium ${
                        isPending ? 'text-gray-500' : 'text-gray-200'
                      }`}>
                        {step.label}
                      </span>
                      {isActive && (
                        <span className="ml-2 text-xs text-blue-400 animate-pulse">In Progress</span>
                      )}
                      {isCompleted && (
                        <span className="ml-2 text-xs text-green-400">Complete</span>
                      )}
                    </div>
                    {(isActive || isCompleted) && (
                      <span className={`text-sm ${isCompleted ? 'text-green-400' : 'text-gray-400'}`}>
                        {stepProgress}%
                      </span>
                    )}
                  </div>
                  
                  <p className={`text-xs ${isPending ? 'text-gray-600' : 'text-gray-500'}`}>
                    {step.description}
                  </p>
                  
                  {/* Progress Bar for Active Step */}
                  {isActive && (
                    <div className="mt-3">
                      <div className="w-full bg-gray-700 rounded-full h-1.5 overflow-hidden">
                        <div
                          className="bg-blue-500 h-1.5 rounded-full transition-all duration-300 relative"
                          style={{ width: `${stepProgress}%` }}
                        >
                          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-shimmer" />
                        </div>
                      </div>
                      {progress?.message && (
                        <p className="text-xs text-gray-400 mt-2 flex items-center gap-2">
                          <Clock className="w-3 h-3" />
                          {progress.message}
                        </p>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>
      
      {/* Tip */}
      <div className="mt-8 p-3 bg-gray-800/50 rounded-lg border border-gray-700/50">
        <p className="text-xs text-gray-400">
          <strong className="text-gray-300">Tip:</strong> You can close this tab and come back later. 
          Your video will continue processing in the background.
        </p>
      </div>
    </div>
  )
}
