import { Download, CheckCircle, Share2, RotateCcw, ExternalLink, Film } from 'lucide-react'
import toast from 'react-hot-toast'

interface VideoPlayerProps {
  videoUrl: string
  duration?: number
  jobId?: string
}

export const VideoPlayer = ({ videoUrl, duration, jobId }: VideoPlayerProps) => {
  const handleCopyLink = async () => {
    try {
      await navigator.clipboard.writeText(videoUrl)
      toast.success('Video link copied to clipboard!')
    } catch (err) {
      toast.error('Failed to copy link')
    }
  }

  return (
    <div className="space-y-4">
      {/* Success Header */}
      <div className="card bg-gradient-to-r from-green-900/20 to-emerald-900/20 border border-green-500/20">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-green-500/10 rounded-full">
            <CheckCircle className="w-8 h-8 text-green-400" />
          </div>
          <div>
            <h2 className="text-xl font-semibold text-green-300">Video Ready!</h2>
            <p className="text-gray-400 text-sm">Your AI-generated video has been created successfully</p>
          </div>
        </div>
      </div>

      {/* Video Player */}
      <div className="card p-0 overflow-hidden">
        <div className="relative bg-black">
          <video
            controls
            autoPlay
            className="w-full aspect-video"
            src={videoUrl}
            poster=""
          >
            Your browser does not support the video tag.
          </video>
        </div>
        
        {/* Video Info & Actions */}
        <div className="p-4 bg-gray-800/50">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div className="flex items-center gap-4 text-sm text-gray-400">
              <span className="flex items-center gap-2">
                <Film className="w-4 h-4" />
                {jobId ? `Job: ${jobId.slice(0, 8)}...` : 'Video'}
              </span>
              {duration && (
                <span>Duration: {duration.toFixed(1)}s</span>
              )}
            </div>
            
            <div className="flex items-center gap-2">
              <button
                onClick={handleCopyLink}
                className="btn-secondary flex items-center gap-2 text-sm"
                title="Copy video link"
              >
                <Share2 className="w-4 h-4" />
                Share
              </button>
              <a
                href={videoUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-secondary flex items-center gap-2 text-sm"
                title="Open in new tab"
              >
                <ExternalLink className="w-4 h-4" />
                Open
              </a>
              <a
                href={videoUrl}
                download="generated-video.mp4"
                className="btn-primary flex items-center gap-2 text-sm"
              >
                <Download className="w-4 h-4" />
                Download
              </a>
            </div>
          </div>
        </div>
      </div>

      {/* Next Steps */}
      <div className="card bg-gray-800/30">
        <h3 className="text-sm font-medium text-gray-300 mb-3">What's next?</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="flex items-start gap-3 p-3 bg-gray-800/50 rounded-lg hover:bg-gray-700/50 transition-colors cursor-pointer">
            <Download className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-gray-200">Download & Share</p>
              <p className="text-xs text-gray-500">Save the video to your device</p>
            </div>
          </div>
          <div className="flex items-start gap-3 p-3 bg-gray-800/50 rounded-lg hover:bg-gray-700/50 transition-colors cursor-pointer">
            <RotateCcw className="w-5 h-5 text-purple-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-gray-200">Create Another</p>
              <p className="text-xs text-gray-500">Start a new video project</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
