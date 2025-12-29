import { useState, useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { Loader2, FileText, Globe, BarChart3 } from 'lucide-react'
import { compareArticles } from '@/services/compareArticles'
import { fetchArticle } from '@/services/fetchArticle'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import { Separator } from '@/components/ui/separator'

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
      const { sourceContent, translatedContent } = JSON.parse(comparisonData)
      setSourceText(sourceContent)
      setTargetText(translatedContent)
      form.setValue('sourceText', sourceContent)
      form.setValue('targetText', translatedContent)
      
      // Clear the sessionStorage data after loading
      sessionStorage.removeItem('comparisonData')
    }
  }, [form])

  const onSubmit = async (data: { sourceText: string; targetText: string }) => {
    try {
      setIsLoading(true)
      setComparisonResult(null)

      const response = await compareArticles(data.sourceText, data.targetText)
      // The response data has a 'comparisons' array, we need the first comparison
      const comparison = response.data.comparisons[0]
      setComparisonResult(comparison)
      setSourceText(data.sourceText)
      setTargetText(data.targetText)
    } catch (error) {
      console.error('Error comparing articles:', error)
      alert('Failed to compare articles. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  const fetchFromUrl = async (url: string, setText: (text: string) => void) => {
    try {
      setIsLoading(true)
      const response = await fetchArticle(url)
      const text = response.data.sourceArticle
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
                onChange={(e) => {
                  if (e.target.value) {
                    fetchFromUrl(e.target.value, setSourceText)
                  }
                }}
              />
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  const url = (document.querySelector('input[placeholder="Enter Wikipedia URL"]') as HTMLInputElement)?.value
                  if (url) {
                    fetchFromUrl(url, setSourceText)
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
                  <FormLabel>Source Content</FormLabel>
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
                  <FormLabel>Target Content</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder="Paste translated text here..."
                      className="min-h-[150px]"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>

          {/* Submit Button */}
          <Button type="submit" disabled={isLoading} className="w-full">
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Comparing...
              </>
            ) : (
              'Compare Articles'
            )}
          </Button>
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