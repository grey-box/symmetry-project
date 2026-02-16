import { useState, useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { Loader2, FileText, Globe, BarChart3 } from 'lucide-react'
import { compareArticles } from '@/services/compareArticles'
import { fetchArticle } from '@/services/fetchArticle'
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
  const [sourceLanguage, setSourceLanguage] = useState('en')
  const [targetLanguage, setTargetLanguage] = useState('en')
  const [targetUrl, setTargetUrl] = useState('')
  const [isTargetTextReadOnly, setIsTargetTextReadOnly] = useState(false)
  const [isTargetLanguageReadOnly, setIsTargetLanguageReadOnly] = useState(false)
  const [similarityThreshold, setSimilarityThreshold] = useState(0.65)

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

  // Create abort controller for stopping comparison
  let abortController: AbortController | null = null

  const onSubmit = async (data: { sourceText: string; targetText: string }) => {
    abortController = new AbortController()
    setIsLoading(true)
    setIsRunning(true)
    setComparisonResult(null)

    try {
      const response = await compareArticles(data.sourceText, data.targetText, sourceLanguage, targetLanguage, similarityThreshold)
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
                 id="source-url"
               />
               <Button
                 type="button"
                 variant="outline"
                 onClick={() => {
                   const url = (document.getElementById('source-url') as HTMLInputElement)?.value
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
                Lower values = more sensitive (detects more differences)
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
        </form>
      </Form>

      {/* Results Section */}
      {comparisonResult && (
        <div className="mt-8 space-y-6">
          <Separator />
          
          <div className="space-y-4">
            <h3 className="text-lg font-semibold">Comparison Results</h3>
            
            {/* Missing Information (from right article - translated) */}
            {comparisonResult.right_article_extra_info_index.length > 0 && (
              <div className="space-y-2">
                <h4 className="font-medium text-red-700">Missing Information in Translation</h4>
                <ul className="list-disc list-inside space-y-1 text-sm">
                  {comparisonResult.right_article_extra_info_index.map((index, i) => (
                    <li key={i} className="text-red-600">
                      Sentence {index + 1}: "{comparisonResult.right_article_array[index]}"
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Extra Information (in right article - translated) */}
            {comparisonResult.left_article_missing_info_index.length > 0 && (
              <div className="space-y-2">
                <h4 className="font-medium text-green-700">Extra Information in Translation</h4>
                <ul className="list-disc list-inside space-y-1 text-sm">
                  {comparisonResult.left_article_missing_info_index.map((index, i) => (
                    <li key={i} className="text-green-600">
                      Sentence {index + 1}: "{comparisonResult.left_article_array[index]}"
                    </li>
                  ))}
                </ul>
              </div>
            )}

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