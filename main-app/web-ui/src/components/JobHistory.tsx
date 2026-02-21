import { Clock, CheckCircle, XCircle, Loader2, FileText, Trash2, RotateCcw, Film } from 'lucide-react'
import { Job } from '../api/client'

interface JobHistoryProps {
  jobs: Job[]
  onSelectJob: (job: Job) => void
  onDeleteJob: (jobId: string) => void
  onRetryJob?: (jobId: string) => void
  selectedJobId?: string
  isLoading?: boolean
}

const statusConfig: Record<string, { icon: typeof Clock; color: string; bgColor: string; label: string }> = {
  draft: { icon: FileText, color: 'text-gray-400', bgColor: 'bg-gray-500/10', label: 'Draft' },
  script_pending: { icon: Loader2, color: 'text-blue-400', bgColor: 'bg-blue-500/10', label: 'Generating Script' },
  script_ready: { icon: FileText, color: 'text-blue-400', bgColor: 'bg-blue-500/10', label: 'Script Ready' },
  approved: { icon: Loader2, color: 'text-yellow-400', bgColor: 'bg-yellow-500/10', label: 'Starting...' },
  processing: { icon: Loader2, color: 'text-yellow-400', bgColor: 'bg-yellow-500/10', label: 'Processing' },
  completed: { icon: CheckCircle, color: 'text-green-400', bgColor: 'bg-green-500/10', label: 'Completed' },
  failed: { icon: XCircle, color: 'text-red-400', bgColor: 'bg-red-500/10', label: 'Failed' },
}

export const JobHistory = ({ 
  jobs, 
  onSelectJob, 
  onDeleteJob, 
  onRetryJob,
  selectedJobId,
  isLoading 
}: JobHistoryProps) => {
  if (isLoading) {
    return (
      <div className="card">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Film className="w-5 h-5 text-gray-400" />
          Recent Videos
        </h2>
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
        </div>
      </div>
    )
  }

  if (!jobs || !Array.isArray(jobs) || jobs.length === 0) {
    return (
      <div className="card">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Film className="w-5 h-5 text-gray-400" />
          Recent Videos
        </h2>
        <div className="text-center py-8">
          <FileText className="w-12 h-12 mx-auto mb-3 text-gray-600" />
          <p className="text-gray-400">No videos created yet</p>
          <p className="text-gray-500 text-sm mt-1">Create your first video above</p>
        </div>
      </div>
    )
  }

  return (
    <div className="card">
      <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
        <Film className="w-5 h-5 text-gray-400" />
        Recent Videos
        <span className="text-xs text-gray-500 font-normal">({jobs.length})</span>
      </h2>
      
      <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
        {jobs.map((job) => {
          const config = statusConfig[job.status] || statusConfig.draft
          const Icon = config.icon
          const isSelected = job.id === selectedJobId
          const isAnimating = job.status === 'processing' || job.status === 'script_pending' || job.status === 'approved'
          const canRetry = ['failed', 'script_pending', 'processing'].includes(job.status)
          
          return (
            <div
              key={job.id}
              onClick={() => onSelectJob(job)}
              className={`
                group relative p-3 rounded-lg cursor-pointer transition-all duration-200
                ${isSelected 
                  ? 'bg-blue-600/20 border border-blue-500/50 shadow-lg shadow-blue-500/10' 
                  : 'bg-gray-800/50 hover:bg-gray-700/50 border border-transparent'
                }
              `}
            >
              <div className="flex items-start gap-3">
                {/* Status Icon */}
                <div className={`p-2 rounded-lg ${config.bgColor}`}>
                  <Icon className={`w-4 h-4 ${config.color} ${isAnimating ? 'animate-spin' : ''}`} />
                </div>
                
                {/* Content */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate pr-8">
                    {job.original_prompt.length > 50 
                      ? job.original_prompt.slice(0, 50) + '...' 
                      : job.original_prompt
                    }
                  </p>
                  <div className="flex items-center gap-2 mt-1">
                    <span className={`text-xs ${config.color}`}>{config.label}</span>
                    <span className="text-gray-600">•</span>
                    <span className="text-xs text-gray-500">
                      {formatDate(job.created_at)}
                    </span>
                  </div>
                </div>
              </div>
              
              {/* Action Buttons */}
              <div className="absolute top-2 right-2 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                {canRetry && onRetryJob && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      onRetryJob(job.id)
                    }}
                    className="p-1.5 hover:bg-blue-600/20 rounded text-gray-400 hover:text-blue-400 transition-colors"
                    title="Retry job"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                  </button>
                )}
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    if (confirm('Delete this job?')) {
                      onDeleteJob(job.id)
                    }
                  }}
                  className="p-1.5 hover:bg-red-600/20 rounded text-gray-400 hover:text-red-400 transition-colors"
                  title="Delete job"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
              
              {/* Processing indicator */}
              {isAnimating && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gray-700 rounded-full overflow-hidden">
                  <div className="h-full bg-blue-500 animate-progress" />
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

function formatDate(dateString: string): string {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMins / 60)
  const diffDays = Math.floor(diffHours / 24)
  
  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  
  return date.toLocaleDateString()
}
