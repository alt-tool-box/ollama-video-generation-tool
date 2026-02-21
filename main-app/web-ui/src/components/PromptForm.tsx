import { useState } from 'react'
import { Sparkles, Loader2, Lightbulb, Wand2 } from 'lucide-react'

interface PromptFormProps {
  onSubmit: (prompt: string) => void
  isLoading: boolean
}

const EXAMPLE_PROMPTS = [
  "A cat floating in space, looking at Earth through a window",
  "A magical forest where the trees glow with bioluminescence at night",
  "A time-lapse of a flower blooming in a futuristic city",
  "An underwater adventure with colorful coral reefs and exotic fish",
  "A robot learning to paint in an art studio",
]

export const PromptForm = ({ onSubmit, isLoading }: PromptFormProps) => {
  const [prompt, setPrompt] = useState('')
  const [showExamples, setShowExamples] = useState(false)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (prompt.trim() && !isLoading) {
      onSubmit(prompt.trim())
    }
  }

  const useExample = (example: string) => {
    setPrompt(example)
    setShowExamples(false)
  }

  return (
    <div className="space-y-4">
      {/* Main Form Card */}
      <form onSubmit={handleSubmit} className="card">
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2 bg-gradient-to-br from-blue-500/20 to-purple-500/20 rounded-xl">
            <Wand2 className="w-6 h-6 text-blue-400" />
          </div>
          <div>
            <h2 className="text-xl font-semibold">Create New Video</h2>
            <p className="text-sm text-gray-500">Powered by AI</p>
          </div>
        </div>
        
        <p className="text-gray-400 text-sm mb-4 mt-4">
          Describe your video idea. Don't worry about the details — our AI will enhance your prompt 
          and create a detailed scene-by-scene script for you to review.
        </p>
        
        <div className="relative">
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="e.g., A cat floating in space, looking at Earth through a window..."
            className="textarea h-36 mb-2 pr-12"
            disabled={isLoading}
          />
          <div className="absolute right-3 bottom-5 text-xs text-gray-500">
            {prompt.length}/500
          </div>
        </div>

        {/* Example Prompts Toggle */}
        <button
          type="button"
          onClick={() => setShowExamples(!showExamples)}
          className="text-sm text-blue-400 hover:text-blue-300 flex items-center gap-1 mb-4 transition-colors"
        >
          <Lightbulb className="w-4 h-4" />
          {showExamples ? 'Hide examples' : 'Need inspiration? See examples'}
        </button>

        {/* Example Prompts */}
        {showExamples && (
          <div className="mb-4 p-3 bg-gray-800/50 rounded-lg space-y-2">
            <p className="text-xs text-gray-400 mb-2">Click an example to use it:</p>
            {EXAMPLE_PROMPTS.map((example, index) => (
              <button
                key={index}
                type="button"
                onClick={() => useExample(example)}
                className="block w-full text-left text-sm text-gray-300 hover:text-white hover:bg-gray-700/50 p-2 rounded transition-colors"
              >
                "{example}"
              </button>
            ))}
          </div>
        )}
        
        <button
          type="submit"
          disabled={!prompt.trim() || isLoading}
          className="btn-primary w-full flex items-center justify-center gap-2 h-12 text-base font-medium disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Creating your video...
            </>
          ) : (
            <>
              <Sparkles className="w-5 h-5" />
              Generate Script
            </>
          )}
        </button>
      </form>

      {/* How it works */}
      <div className="card bg-gray-800/30">
        <h3 className="text-sm font-medium text-gray-300 mb-3">How it works</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="flex items-start gap-3">
            <div className="w-6 h-6 rounded-full bg-blue-600 flex items-center justify-center text-xs font-bold flex-shrink-0">
              1
            </div>
            <div>
              <p className="text-sm font-medium text-gray-200">Describe</p>
              <p className="text-xs text-gray-500">Enter a simple idea for your video</p>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <div className="w-6 h-6 rounded-full bg-purple-600 flex items-center justify-center text-xs font-bold flex-shrink-0">
              2
            </div>
            <div>
              <p className="text-sm font-medium text-gray-200">Review</p>
              <p className="text-xs text-gray-500">AI creates a script you can edit</p>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <div className="w-6 h-6 rounded-full bg-green-600 flex items-center justify-center text-xs font-bold flex-shrink-0">
              3
            </div>
            <div>
              <p className="text-sm font-medium text-gray-200">Generate</p>
              <p className="text-xs text-gray-500">Approve and get your video</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
