import { useState, useEffect, useRef } from 'react'
import { useForm } from 'react-hook-form'
import { Loader2, FileText, Globe, BarChart3 } from 'lucide-react'
import { compareArticles } from '@/services/compareArticles'
import { fetchArticle } from '@/services/fetchArticle'
import { getThresholds } from '@/services/thresholdService'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import { Separator } from '@/components/ui/separator'
import { Input } from '@/components/ui/input'

const ComparisonSection = () => {
  const [isLoading, setIsLoading] = useState(false)
  const [comparisonResult, setComparisonResult] = useState<{
    left_article_array: string[]
    right_article_array: string[]
    left_article_missing_info_index: number[]
    right_article_extra_info_index: number[]
  } | null>(null)
  const [sourceText, setSourceText] = useState('')
  const [targetText, setTargetText] = useState('')
  const [elapsedTime, setElapsedTime] = useState(0)
  const [isRunning, setIsRunning] = useState(false)

  // Progress bar
  const [compareProgress, setCompareProgress] = useState(0)
  const [compareStage, setCompareStage] = useState('')
  const rafRef = useRef<number | null>(null)
  const resetTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const animatingRef = useRef(false)
  const [sourceLanguage, setSourceLanguage] = useState('en')
  const [targetLanguage, setTargetLanguage] = useState('en')
  const [targetUrl, setTargetUrl] = useState('')
  const [isTargetTextReadOnly, setIsTargetTextReadOnly] = useState(false)
  const [isTargetLanguageReadOnly, setIsTargetLanguageReadOnly] = useState(false)
  const [similarityThreshold, setSimilarityThreshold] = useState(0.65)
  const [selectedModel, setSelectedModel] = useState('sentence-transformers/LaBSE')
  const sourceUrlRef = useRef<HTMLInputElement>(null)

  // Fetch default threshold from backend on mount
  useEffect(() => {
    getThresholds().then((thresholds) => {
      setSimilarityThreshold(thresholds.similarity_threshold)
    })
  }, [])

  const form = useForm({
    defaultValues: {
      sourceText: '',
      targetText: '',
    },
  })

  // Load comparison data from sessionStorage when component mounts
  useEffect(() => {
    const comparisonData = sessionStorage.getItem('comparisonData')
    if (comparisonData) {
      const { sourceContent, translatedContent, sourceUrl, targetLanguage: targetLang } = JSON.parse(comparisonData)
      setSourceText(sourceContent)
      setTargetText(translatedContent)

      // If source URL is provided, extract language and set target URL
      if (sourceUrl) {
        const langMatch = sourceUrl.match(/https?:\/\/([a-z]{2})\.wikipedia\.org/)
        const sourceLang = langMatch ? langMatch[1] : 'en'
        setSourceLanguage(sourceLang)

        if (targetLang) {
          // Set target URL with target language
          const targetUrlObj = new URL(sourceUrl)
          targetUrlObj.hostname = `${targetLang.toLowerCase()}.wikipedia.org`
          setTargetUrl(targetUrlObj.toString())

          // Set target language (convert to 2-letter code)
          const langMap: Record<string, string> = {
            'English': 'en',
            'French': 'fr',
            'Hindi': 'hi',
            'Arabic': 'ar',
          }
          setTargetLanguage(langMap[targetLang] || targetLang.toLowerCase())
        }

        // Make target fields read-only
        setIsTargetTextReadOnly(true)
        setIsTargetLanguageReadOnly(true)
      }

      form.setValue('sourceText', sourceContent)
      form.setValue('targetText', translatedContent)

      // Clear the sessionStorage data after loading
      sessionStorage.removeItem('comparisonData')
    }
  }, [form])

  // Timer effect
  useEffect(() => {
    let interval: NodeJS.Timeout | null = null
    if (isRunning) {
      interval = setInterval(() => {
        setElapsedTime(prev => prev + 1)
      }, 1000)
    } else {
      setElapsedTime(0)
    }
    return () => {
      if (interval) clearInterval(interval)
    }
  }, [isRunning])

  // Progress bar animation
  useEffect(() => {
    if (resetTimerRef.current) clearTimeout(resetTimerRef.current)

    if (!isLoading) {
      if (animatingRef.current) {
        animatingRef.current = false
        if (rafRef.current) cancelAnimationFrame(rafRef.current)
        setCompareProgress(100)
        setCompareStage('Complete')
        resetTimerRef.current = setTimeout(() => {
          setCompareProgress(0)
          setCompareStage('')
        }, 1000)
      }
      return
    }

    animatingRef.current = true
    setCompareProgress(0)

    const stages: { to: number; ms: number; label: string }[] = [
      { to: 12, ms: 1500,   label: 'Preparing texts...' },
      { to: 40, ms: 5000,   label: 'Computing embeddings...' },
      { to: 83, ms: 30000,  label: 'Comparing sentences...' },
      { to: 91, ms: 6000,   label: 'Finalizing results...' },
      // Slow creep to 99% so the bar never freezes while waiting for the response.
      // This stage has a very long budget — the bar snaps to 100% whenever the
      // response actually arrives, regardless of how far along this stage is.
      { to: 99, ms: 120000, label: 'Finalizing results...' },
    ]

    let stageIdx = 0
    let from = 0
    let stageStart = Date.now()
    setCompareStage(stages[0].label)

    const tick = () => {
      if (!animatingRef.current) return
      const stage = stages[stageIdx]
      const elapsed = Date.now() - stageStart
      const t = Math.min(elapsed / stage.ms, 1)
      const eased = 1 - Math.pow(1 - t, 3)
      setCompareProgress(Math.floor(from + (stage.to - from) * eased))

      if (t >= 1 && stageIdx < stages.length - 1) {
        from = stage.to
        stageIdx++
        stageStart = Date.now()
        setCompareStage(stages[stageIdx].label)
      }

      rafRef.current = requestAnimationFrame(tick)
    }

    rafRef.current = requestAnimationFrame(tick)
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
    }
  }, [isLoading])

  // Create abort controller for stopping comparison
  let abortController: AbortController | null = null

  const onSubmit = async (data: { sourceText: string; targetText: string }) => {
    abortController = new AbortController()
    setIsLoading(true)
    setIsRunning(true)
    setComparisonResult(null)

    try {
      const response = await compareArticles(data.sourceText, data.targetText, sourceLanguage, targetLanguage, similarityThreshold, selectedModel)
      // The response data has a 'comparisons' array, we need the first comparison
      const comparison = response.data.comparisons[0]
      setComparisonResult(comparison)
      setSourceText(data.sourceText)
      setTargetText(data.targetText)
    } catch (error) {
      console.error('Error comparing articles:', error)
      const axiosError = error as any
      let errorMessage = 'Failed to compare articles. Please try again.'

      if (axiosError?.code === 'ECONNABORTED') {
        errorMessage = `Comparison request timed out after ${elapsedTime}s. The comparison is taking longer than expected. Please try again or reduce the amount of text being compared.`
      } else if (axiosError?.code === 'ERR_CANCELED') {
        errorMessage = 'Comparison was stopped by the user.'
      } else if (axiosError?.response?.status === 400) {
        errorMessage = `Bad Request: ${axiosError.response.data?.detail || 'Invalid request parameters.'}`
      } else if (axiosError?.response?.status === 404) {
        errorMessage = `Comparison endpoint not found (404). ${axiosError.response.data?.detail || 'Please check that the backend server is running.'}`
      } else if (axiosError?.response?.status === 422) {
        errorMessage = `Validation Error: ${axiosError.response.data?.detail || 'The request contains invalid data.'}`
      } else if (axiosError?.response?.status >= 500) {
        errorMessage = `Server error (${axiosError.response.status}): ${axiosError.response.data?.detail || 'The backend encountered an error. Check backend logs for details.'}`
      } else if (!axiosError?.response) {
        errorMessage = `Unable to connect to the backend server. Please ensure the backend is running at the configured URL. (${axiosError.message})`
      } else {
        errorMessage = `Comparison failed: ${axiosError.message}`
      }

      alert(errorMessage)
    } finally {
      setIsLoading(false)
      setIsRunning(false)
      abortController = null
    }
  }

  const onStopComparison = () => {
    if (abortController) {
      abortController.abort()
    }
  }

  const fetchFromUrl = async (url: string, setText: (text: string) => void, setLang: (lang: string) => void) => {
    try {
      setIsLoading(true)
      const response = await fetchArticle(url)
      const text = response.data.sourceArticle

      // Extract language from Wikipedia URL
      const langMatch = url.match(/https?:\/\/([a-z]{2})\.wikipedia\.org/)
      const language = langMatch ? langMatch[1] : 'en'
      setLang(language)

      setText(text)
      form.setValue('sourceText', text)
    } catch (error) {
      console.error('Error fetching article:', error)
      alert('Failed to fetch article. Please check the URL and try again.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <section className="bg-white mt-6 rounded-xl shadow-md p-6">
      <div className="flex items-center gap-2 mb-6">
        <BarChart3 size={20} />
        <h2 className="text-xl font-semibold">AI Comparison</h2>
      </div>

      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
          {/* Source Text Section */}
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <FileText size={16} />
              <h3 className="text-lg font-medium">Source Text</h3>
            </div>

            <div className="flex gap-2">
              <input
                type="url"
                placeholder="Enter Wikipedia URL"
                className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                ref={sourceUrlRef}
              />
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  const url = sourceUrlRef.current?.value
                  if (url) {
                    fetchFromUrl(url, setSourceText, setSourceLanguage)
                  }
                }}
                disabled={isLoading}
              >
                Fetch
              </Button>
            </div>

            <FormField
              control={form.control}
              name="sourceText"
              render={({ field }) => (
                <FormItem>
                  <div className="flex items-center justify-between">
                    <FormLabel>Source Content</FormLabel>
                    <span className="text-sm text-gray-500">Language: <span className="font-medium">{sourceLanguage}</span></span>
                  </div>
                  <FormControl>
                    <Textarea
                      placeholder="Paste source text here or fetch from URL above..."
                      className="min-h-[150px]"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>

          <Separator />

          {/* Target Text Section */}
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <Globe size={16} />
              <h3 className="text-lg font-medium">Target Text</h3>
            </div>

            <FormField
              control={form.control}
              name="targetText"
              render={({ field }) => (
                <FormItem>
                  <div className="flex items-center justify-between">
                    <FormLabel>Target Content</FormLabel>
                    <div className="flex items-center gap-2">
                      {isTargetTextReadOnly && (
                        <div className="flex items-center gap-2 mr-2">
                          <input
                            type="text"
                            value={targetUrl}
                            readOnly
                            className="max-w-[200px] px-2 py-1 text-xs border border-gray-300 rounded-md bg-gray-50"
                            title="Source URL from Translation page"
                          />
                          <span className="text-xs text-gray-400">→</span>
                        </div>
                      )}
                      <label className="text-sm text-gray-500">Language:</label>
                      <input
                        type="text"
                        value={targetLanguage}
                        onChange={(e) => setTargetLanguage(e.target.value)}
                        className="w-16 px-2 py-1 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="en"
                        readOnly={isTargetLanguageReadOnly}
                      />
                    </div>
                  </div>
                  <FormControl>
                    <Textarea
                      placeholder="Paste translated text here..."
                      className="min-h-[150px]"
                      {...field}
                      readOnly={isTargetTextReadOnly}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>

          {/* Comparison Model */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Comparison Model</label>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
            >
              <option value="sentence-transformers/LaBSE">LaBSE (multilingual embeddings)</option>
              <option value="similarity_prototype">Similarity Prototype (Phase 1/2/3 — English only, auto-translates)</option>
            </select>
          </div>

          {/* Similarity Threshold */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Similarity Threshold</label>
            <div className="flex items-center gap-4">
              <Input
                type="number"
                min="0"
                max="1"
                step="0.01"
                value={similarityThreshold}
                onChange={(e) => setSimilarityThreshold(parseFloat(e.target.value) || 0.65)}
                className="w-24"
              />
              <span className="text-sm text-gray-500">
                Higher values = more sensitive (stricter matching, detects more differences)
              </span>
            </div>
          </div>

          {/* Submit Button */}
          <div className="flex gap-2">
            <Button type="submit" disabled={isLoading} className="flex-1">
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Comparing... ({elapsedTime}s)
                </>
              ) : (
                'Compare Articles'
              )}
            </Button>
            {isLoading && (
              <Button
                type="button"
                variant="destructive"
                onClick={onStopComparison}
              >
                Stop
              </Button>
            )}
          </div>

          {/* Progress bar */}
          {(isLoading || compareProgress > 0) && (
            <div className="space-y-1">
              <div className="flex justify-between text-xs text-gray-500">
                <span>{compareStage}</span>
                <span>{compareProgress}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                <div
                  className={`h-2 rounded-full transition-all duration-300 ease-out ${
                    compareProgress === 100 ? 'bg-green-500' : 'bg-blue-500'
                  }`}
                  style={{ width: `${compareProgress}%` }}
                />
              </div>
            </div>
          )}
        </form>
      </Form>

      {/* Results Section */}
      {comparisonResult && (
        <div className="mt-8 space-y-6">
          <Separator />

          <div className="space-y-4">
            <h3 className="text-lg font-semibold">Comparison Results</h3>

            {/* Legend */}
            <div className="bg-gray-50 rounded-lg p-4 border">
              <h4 className="text-sm font-medium text-gray-700 mb-3">Legend</h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
                <div className="flex items-center gap-2">
                  <del className="text-red-600 bg-red-100/50 px-1 rounded">Missing</del>
                  <span className="text-gray-600">= Information missing in target</span>
                </div>
                <div className="flex items-center gap-2">
                  <ins className="text-green-600 bg-green-100/50 px-1 rounded">Extra</ins>
                  <span className="text-gray-600">= Extra information in target</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-gray-500 italic">—</span>
                  <span className="text-gray-600">= No corresponding sentence</span>
                </div>
              </div>
            </div>

            {/* Side-by-side comparison view */}
            <div className="space-y-3">
              {/* Column headers */}
              <div className="grid grid-cols-2 gap-4 text-xs font-medium text-gray-500 uppercase tracking-wide px-3">
                <span>Source ({sourceLanguage})</span>
                <span>Target ({targetLanguage})</span>
              </div>

              {/* Comparison rows */}
              {comparisonResult.left_article_array.map((sourceSentence, idx) => {
                const isSourceMissing = comparisonResult.right_article_extra_info_index.includes(idx);
                const isTargetExtra = comparisonResult.left_article_missing_info_index.includes(idx);
                const targetSentence = idx < comparisonResult.right_article_array.length ? comparisonResult.right_article_array[idx] : '';

                return (
                  <div
                    key={idx}
                    className={`grid grid-cols-2 gap-4 p-3 rounded-md border ${
                      isSourceMissing
                        ? 'border-red-200 bg-red-50/30'
                        : isTargetExtra
                        ? 'border-green-200 bg-green-50/30'
                        : 'border-gray-200 bg-gray-50/30'
                    }`}
                  >
                    {/* Source sentence */}
                    <div className="text-sm leading-relaxed text-gray-700">
                      {isSourceMissing ? (
                        <del className="text-red-600 bg-red-100/50">{sourceSentence}</del>
                      ) : (
                        <p>{sourceSentence}</p>
                      )}
                    </div>

                    {/* Target sentence */}
                    <div className="text-sm leading-relaxed text-gray-700">
                      {isTargetExtra ? (
                        <ins className="text-green-600 bg-green-100/50">{targetSentence}</ins>
                      ) : (
                        <p>{targetSentence || <span className="italic text-gray-400">—</span>}</p>
                      )}
                    </div>
                  </div>
                );
              })}

              {/* Handle extra sentences in target not in source */}
              {comparisonResult.right_article_array.length > comparisonResult.left_article_array.length && (
                <>
                  {comparisonResult.right_article_array.slice(comparisonResult.left_article_array.length).map((targetSentence, idx) => (
                    <div
                      key={`extra-${idx}`}
                      className="grid grid-cols-2 gap-4 p-3 rounded-md border border-green-200 bg-green-50/30"
                    >
                      <div className="text-sm leading-relaxed text-gray-400 italic">—</div>
                      <div className="text-sm leading-relaxed text-gray-700">
                        <ins className="text-green-600 bg-green-100/50">{targetSentence}</ins>
                      </div>
                    </div>
                  ))}
                </>
              )}
            </div>

            {comparisonResult.right_article_extra_info_index.length === 0 && comparisonResult.left_article_missing_info_index.length === 0 && (
              <div className="text-center py-4 text-gray-500">
                No significant differences found between the texts.
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  )
}

export default ComparisonSection
