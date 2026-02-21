import { useState } from 'react'
import { Edit3, RefreshCw, Check, X, Clock, Image, Volume2, Sparkles, Play, Loader2, ChevronDown, ChevronUp } from 'lucide-react'
import { Scene } from '../api/client'

interface ScriptEditorProps {
  script: {
    enhanced_prompt: string
    scenes: Scene[]
    total_duration: number
    style: string
  }
  onUpdateScene: (sceneId: number, updates: Partial<Scene>) => void
  onRegenerateScene: (sceneId: number, feedback?: string) => void
  onApprove: () => void
  isRegenerating: boolean
  isApproving?: boolean
}

export const ScriptEditor = ({
  script,
  onUpdateScene,
  onRegenerateScene,
  onApprove,
  isRegenerating,
  isApproving = false,
}: ScriptEditorProps) => {
  const [editingScene, setEditingScene] = useState<number | null>(null)
  const [editedScene, setEditedScene] = useState<Scene | null>(null)
  const [feedback, setFeedback] = useState('')
  const [showFeedback, setShowFeedback] = useState<number | null>(null)
  const [expandedScenes, setExpandedScenes] = useState<Set<number>>(new Set(script.scenes.map(s => s.id)))

  const handleEdit = (scene: Scene) => {
    setEditingScene(scene.id)
    setEditedScene({ ...scene })
  }

  const handleSave = () => {
    if (editedScene && editingScene !== null) {
      onUpdateScene(editingScene, editedScene)
      setEditingScene(null)
      setEditedScene(null)
    }
  }

  const handleCancel = () => {
    setEditingScene(null)
    setEditedScene(null)
  }

  const handleRegenerate = (sceneId: number) => {
    onRegenerateScene(sceneId, feedback || undefined)
    setShowFeedback(null)
    setFeedback('')
  }

  const toggleExpanded = (sceneId: number) => {
    const newExpanded = new Set(expandedScenes)
    if (newExpanded.has(sceneId)) {
      newExpanded.delete(sceneId)
    } else {
      newExpanded.add(sceneId)
    }
    setExpandedScenes(newExpanded)
  }

  return (
    <div className="space-y-4">
      {/* Header Card */}
      <div className="card">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <Sparkles className="w-5 h-5 text-purple-400" />
              <h2 className="text-xl font-semibold">Script Ready for Review</h2>
            </div>
            <p className="text-gray-400 text-sm">
              Your AI-generated script is ready. Review each scene and make any adjustments before generating the video.
            </p>
          </div>
          <button 
            onClick={onApprove} 
            disabled={isApproving}
            className="btn-success flex items-center gap-2 whitespace-nowrap"
          >
            {isApproving ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Play className="w-5 h-5" />
            )}
            {isApproving ? 'Starting...' : 'Approve & Generate'}
          </button>
        </div>
      </div>

      {/* Enhanced Prompt */}
      <div className="card bg-gradient-to-r from-purple-900/20 to-blue-900/20 border border-purple-500/20">
        <div className="flex items-start gap-3">
          <div className="p-2 bg-purple-500/10 rounded-lg">
            <Sparkles className="w-5 h-5 text-purple-400" />
          </div>
          <div className="flex-1">
            <h3 className="text-sm font-medium text-purple-300 mb-1">Enhanced Prompt</h3>
            <p className="text-gray-300 text-sm leading-relaxed">{script.enhanced_prompt}</p>
          </div>
        </div>
      </div>

      {/* Stats Bar */}
      <div className="flex items-center gap-6 px-4 py-3 bg-gray-800/50 rounded-lg">
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-gray-400" />
          <span className="text-sm">
            <strong className="text-gray-200">{script.total_duration}s</strong>
            <span className="text-gray-500 ml-1">total</span>
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Image className="w-4 h-4 text-gray-400" />
          <span className="text-sm">
            <strong className="text-gray-200">{script.scenes.length}</strong>
            <span className="text-gray-500 ml-1">scenes</span>
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500">Style:</span>
          <span className="text-sm text-gray-300 bg-gray-700 px-2 py-0.5 rounded">{script.style}</span>
        </div>
      </div>

      {/* Scenes */}
      <div className="space-y-3">
        {script.scenes.map((scene, index) => {
          const isExpanded = expandedScenes.has(scene.id)
          const isEditing = editingScene === scene.id
          
          return (
            <div 
              key={scene.id} 
              className={`card transition-all duration-200 ${
                isEditing ? 'ring-2 ring-blue-500/50' : ''
              }`}
            >
              {/* Scene Header */}
              <div 
                className="flex items-center justify-between cursor-pointer"
                onClick={() => !isEditing && toggleExpanded(scene.id)}
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 bg-gradient-to-br from-blue-600 to-purple-600 rounded-lg flex items-center justify-center text-sm font-bold">
                    {index + 1}
                  </div>
                  <div>
                    <h3 className="font-medium text-gray-200">Scene {index + 1}</h3>
                    <div className="flex items-center gap-2 text-xs text-gray-500">
                      <Clock className="w-3 h-3" />
                      {scene.duration_seconds}s
                      {!isExpanded && (
                        <>
                          <span>•</span>
                          <span className="truncate max-w-[200px]">{scene.description}</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>
                
                <div className="flex items-center gap-2">
                  {isEditing ? (
                    <>
                      <button onClick={handleSave} className="p-2 hover:bg-green-600/20 rounded-lg transition-colors">
                        <Check className="w-4 h-4 text-green-400" />
                      </button>
                      <button onClick={handleCancel} className="p-2 hover:bg-red-600/20 rounded-lg transition-colors">
                        <X className="w-4 h-4 text-red-400" />
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        onClick={(e) => { e.stopPropagation(); handleEdit(scene) }}
                        className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
                        title="Edit scene"
                      >
                        <Edit3 className="w-4 h-4 text-gray-400" />
                      </button>
                      <button
                        onClick={(e) => { e.stopPropagation(); setShowFeedback(showFeedback === scene.id ? null : scene.id) }}
                        className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
                        title="Regenerate scene"
                        disabled={isRegenerating}
                      >
                        <RefreshCw className={`w-4 h-4 text-gray-400 ${isRegenerating ? 'animate-spin' : ''}`} />
                      </button>
                      <button
                        onClick={(e) => { e.stopPropagation(); toggleExpanded(scene.id) }}
                        className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
                      >
                        {isExpanded ? (
                          <ChevronUp className="w-4 h-4 text-gray-400" />
                        ) : (
                          <ChevronDown className="w-4 h-4 text-gray-400" />
                        )}
                      </button>
                    </>
                  )}
                </div>
              </div>

              {/* Scene Content */}
              {isExpanded && (
                <div className="mt-4 pt-4 border-t border-gray-700/50">
                  {isEditing && editedScene ? (
                    <div className="space-y-4">
                      <div>
                        <label className="text-xs text-gray-400 block mb-2 font-medium">Description</label>
                        <textarea
                          value={editedScene.description}
                          onChange={(e) => setEditedScene({ ...editedScene, description: e.target.value })}
                          className="textarea text-sm"
                          rows={2}
                        />
                      </div>
                      <div>
                        <label className="text-xs text-gray-400 block mb-2 font-medium">Image Prompt</label>
                        <textarea
                          value={editedScene.image_prompt}
                          onChange={(e) => setEditedScene({ ...editedScene, image_prompt: e.target.value })}
                          className="textarea text-sm"
                          rows={3}
                        />
                      </div>
                      <div>
                        <label className="text-xs text-gray-400 block mb-2 font-medium">Narration</label>
                        <textarea
                          value={editedScene.narration}
                          onChange={(e) => setEditedScene({ ...editedScene, narration: e.target.value })}
                          className="textarea text-sm"
                          rows={2}
                        />
                      </div>
                      <div>
                        <label className="text-xs text-gray-400 block mb-2 font-medium">Duration (seconds)</label>
                        <input
                          type="number"
                          value={editedScene.duration_seconds}
                          onChange={(e) => setEditedScene({ ...editedScene, duration_seconds: parseFloat(e.target.value) })}
                          className="input text-sm w-24"
                          min="1"
                          max="30"
                        />
                      </div>
                    </div>
                  ) : (
                    <>
                      <p className="text-gray-300 text-sm mb-4">{scene.description}</p>
                      
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        <div className="bg-gray-800/50 rounded-lg p-4">
                          <div className="flex items-center gap-2 text-xs text-gray-400 mb-2 font-medium">
                            <Image className="w-3.5 h-3.5" />
                            Image Prompt
                          </div>
                          <p className="text-sm text-gray-300 leading-relaxed">{scene.image_prompt}</p>
                        </div>
                        <div className="bg-gray-800/50 rounded-lg p-4">
                          <div className="flex items-center gap-2 text-xs text-gray-400 mb-2 font-medium">
                            <Volume2 className="w-3.5 h-3.5" />
                            Narration
                          </div>
                          <p className="text-sm text-gray-300 leading-relaxed italic">
                            "{scene.narration || 'No narration'}"
                          </p>
                        </div>
                      </div>
                    </>
                  )}

                  {/* Regenerate Feedback */}
                  {showFeedback === scene.id && (
                    <div className="mt-4 pt-4 border-t border-gray-700/50">
                      <label className="text-xs text-gray-400 block mb-2 font-medium">
                        Feedback for regeneration (optional)
                      </label>
                      <div className="flex gap-2">
                        <input
                          type="text"
                          value={feedback}
                          onChange={(e) => setFeedback(e.target.value)}
                          placeholder="e.g., Make it more dramatic, add more detail..."
                          className="input text-sm flex-1"
                        />
                        <button
                          onClick={() => handleRegenerate(scene.id)}
                          disabled={isRegenerating}
                          className="btn-secondary text-sm flex items-center gap-2"
                        >
                          {isRegenerating ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <RefreshCw className="w-4 h-4" />
                          )}
                          Regenerate
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Bottom Action */}
      <div className="card bg-gradient-to-r from-green-900/20 to-emerald-900/20 border border-green-500/20">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-medium text-green-300">Ready to generate?</h3>
            <p className="text-sm text-gray-400 mt-1">
              Once approved, AI will generate images, audio, and compile your video.
            </p>
          </div>
          <button 
            onClick={onApprove} 
            disabled={isApproving}
            className="btn-success flex items-center gap-2"
          >
            {isApproving ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Play className="w-5 h-5" />
            )}
            {isApproving ? 'Starting...' : 'Generate Video'}
          </button>
        </div>
      </div>
    </div>
  )
}
