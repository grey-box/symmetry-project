import { useForm } from 'react-hook-form'
import { ChevronRight, Info } from 'lucide-react'
import { useCallback, useState, useEffect, useRef } from 'react'

import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { SelectData } from '@/models/SelectData'
import { fetchArticle } from '@/services/fetchArticle'
import { translateArticle } from '@/services/translateArticle'
import { useAppContext } from '@/context/AppContext'
import { Phase } from '@/models/Phase'
import { TranslationFormType } from '@/models/TranslationFormType'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'

/** Maps display type to background color. */
const getHighlightClass = (displayType: string): string => {
  switch (displayType) {
    case 'source':
      return 'bg-green-50';
    case 'translated':
      return 'bg-blue-50';
    default:
      return '';
  }
};

interface ArticleDisplayBlock {
  label: string;
  content: string;
  displayType: 'source' | 'translated' | '';
}

const parseWikipediaUrlToLang = (url: string): string | null => {
  const match = url.match(/https?:\/\/([a-z-]{2,})\.wikipedia\.org\/wiki\//)
  return match?.[1] ?? null
}

const TranslationSection = () => {
  const [availableTranslationLanguages, setAvailableTranslationLanguages] = useState<SelectData<string>[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isTranslating, setIsTranslating] = useState(false)
  const translationAbortRef = useRef<AbortController | null>(null)
  const [translationProgress, setTranslationProgress] = useState(0)
  const [backendStatus, setBackendStatus] = useState<'unknown' | 'online' | 'offline'>('unknown')
  const [articleBlocks, setArticleBlocks] = useState<ArticleDisplayBlock[]>([]);

  const form = useForm<TranslationFormType>({
    defaultValues: {
      sourceArticleUrl: '',
      targetArticleLanguage: 'English',
      sourceArticleContent: '',
      translatedArticleContent: '',
    },
  })

  const { translationTool, APIKey } = useAppContext()
  
  const handleCompare = useCallback(() => {
    const sourceContent = form.getValues('sourceArticleContent')
    const translatedContent = form.getValues('translatedArticleContent')
    const sourceUrl = form.getValues('sourceArticleUrl')
    const targetLanguage = form.getValues('targetArticleLanguage')

    sessionStorage.setItem('comparisonData', JSON.stringify({
      sourceContent,
      translatedContent,
      sourceUrl,
      targetLanguage
    }))

    window.dispatchEvent(
      new CustomEvent('set-active-tab', { detail: Phase.AI_COMPARISON })
    )
  }, [form])

  const {
    handleSubmit,
    setValue,
  } = form
  
  const checkBackendStatus = useCallback(async () => {
    try {
      const { getAxiosInstance } = await import('@/services/axios');
      const axios = await getAxiosInstance();
      await axios.get('/health', { timeout: 5000 })
      setBackendStatus('online')
    } catch (error) {
      setBackendStatus('offline')
    }
  }, [])

  useEffect(() => {
    checkBackendStatus()
    const interval = setInterval(checkBackendStatus, 30000)
    
    return () => clearInterval(interval)
  }, [checkBackendStatus])

  useEffect(() => {
    if (!isTranslating) {
      return
    }

    setTranslationProgress((prev) => (prev > 0 ? prev : 8))
    const interval = setInterval(() => {
      setTranslationProgress((prev) => {
        if (prev >= 92) {
          return prev
        }
        if (prev < 40) {
          return Math.min(92, prev + 6)
        }
        if (prev < 70) {
          return Math.min(92, prev + 3)
        }
        return Math.min(92, prev + 1)
      })
    }, 900)

    return () => clearInterval(interval)
  }, [isTranslating])

  useEffect(() => {
    if (isTranslating || translationProgress !== 100) {
      return
    }
    const timeout = setTimeout(() => {
      setTranslationProgress(0)
    }, 500)
    return () => clearTimeout(timeout)
  }, [isTranslating, translationProgress])

  const onSubmit = useCallback(async (data: TranslationFormType) => {
    try {
      setIsLoading(true)
      await checkBackendStatus()
      const response = await fetchArticle(data.sourceArticleUrl)
      setValue('sourceArticleContent', response.data.sourceArticle)
      setValue('translatedArticleContent', '')
      setArticleBlocks([
        {
          label: 'Source Content',
          content: response.data.sourceArticle,
          displayType: 'source',
        },
      ]);

      setAvailableTranslationLanguages(
        response.data.articleLanguages.map(lang => ({
          value: lang,
          label: lang,
        })))
      
    } catch (error) {
      console.error('Error fetching article:', error)
      setIsLoading(false)
      
      let errorMessage = 'Failed to fetch article. Please try again.'
      
      if (error instanceof Error) {
        if (error.message.includes('Network Error') || error.message.includes('ECONNREFUSED')) {
          errorMessage = 'Backend server is not running. Please start the backend server first.'
        } else if (error.message.includes('timeout')) {
          errorMessage = 'Request timed out. Please check your internet connection and try again.'
        } else if (error.message.includes('404')) {
          errorMessage = 'Article not found. Please check the URL and try again.'
        } else if (error.message.includes('400')) {
          errorMessage = 'Invalid request. Please check the URL format.'
        } else {
          errorMessage = `Error: ${error.message}`
        }
      }
      
      alert(errorMessage)
    } finally {
      setIsLoading(false)
    }
  }, [setValue, translationTool, APIKey])
  
  const onLanguageChange = useCallback(async (language: string) => {
    let translationSucceeded = false

    translationAbortRef.current?.abort()
    translationAbortRef.current = new AbortController()
    const { signal } = translationAbortRef.current

    try {
      setIsLoading(true)
      setIsTranslating(true)
      setTranslationProgress(8)

      const sourceText = form.getValues('sourceArticleContent')
      const sourceUrl = form.getValues('sourceArticleUrl')
      const sourceLang = parseWikipediaUrlToLang(sourceUrl) || 'en'

      if (!sourceText || !sourceText.trim()) {
        throw new Error('Source article content is empty.')
      }

      if (!sourceUrl || !sourceUrl.trim()) {
        throw new Error('Source article URL is required for translation.')
      }

      setValue('translatedArticleContent', '')
      setArticleBlocks([
        {
          label: 'Source Content',
          content: sourceText,
          displayType: 'source',
        },
      ])

      const response = await translateArticle(sourceText, sourceLang, language, translationAbortRef.current?.signal)
      const translatedArticle = typeof response.data?.translatedArticle === 'string'
        ? response.data.translatedArticle
        : ''

      if (!translatedArticle.trim()) {
        throw new Error('Translated content is empty.')
      }

      if (signal.aborted) {
        return
      }

      setValue('translatedArticleContent', translatedArticle)
      setArticleBlocks([
        {
          label: 'Source Content',
          content: sourceText,
          displayType: 'source',
        },
        {
          label: 'Translated Content',
          content: translatedArticle,
          displayType: 'translated',
        },
      ]);
      translationSucceeded = true
    } catch (error) {
      if (signal.aborted) {
        return
      }
      console.error('Error translating article:', error)
      setIsLoading(false)

      const axiosError = error as any
      let errorMessage = 'Failed to translate article. Please try again.'

      if (axiosError?.response?.data?.detail) {
        const detail = axiosError.response.data.detail
        errorMessage = typeof detail === 'string' ? detail : JSON.stringify(detail)
      } else if (axiosError?.message?.includes('Network Error') || axiosError?.message?.includes('ECONNREFUSED')) {
        errorMessage = 'Backend server is not running. Please start the backend server first.'
      } else if (axiosError?.message?.includes('timeout')) {
        errorMessage = 'Request timed out. Please check your internet connection and try again.'
      } else if (axiosError?.message?.includes('404')) {
        errorMessage = 'Translation not available for the selected language.'
      } else if (axiosError?.message?.includes('400')) {
        errorMessage = 'Invalid translation request. Please try again.'
      } else if (axiosError?.message) {
        errorMessage = `Error: ${axiosError.message}`
      }

      alert(errorMessage)
    } finally {
      setIsLoading(false)
      if (translationSucceeded) {
        setTranslationProgress(100)
      } else {
        setTranslationProgress(0)
      }
      setIsTranslating(false)
    }
  }, [setValue, form])

  return (
    <section className="bg-white mt-6 rounded-xl shadow-md">
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)}>
          <div className="flex items-center justify-between p-4">
            <div className="flex items-center gap-x-4">
              <div className="inline-flex items-center gap-x-2">
                <Info size={16} />
                <span className="text-zinc-700 text-xs">
                  Here will be instruction regarding translation.
                </span>
              </div>
              
              <div className="flex items-center gap-x-2">
                <div className={`w-2 h-2 rounded-full ${
                  backendStatus === 'online' ? 'bg-green-500' :
                  backendStatus === 'offline' ? 'bg-red-500' : 'bg-yellow-500'
                }`} />
                <span className="text-xs text-gray-500">
                  {backendStatus === 'online' ? 'Backend Online' :
                   backendStatus === 'offline' ? 'Backend Offline' : 'Checking...'}
                </span>
              </div>
            </div>
            <div className="flex gap-x-2">
              <Button 
                disabled={isLoading} 
                type="button" 
                variant="outline" 
                onClick={() => { 
                  translationAbortRef.current?.abort()
                  translationAbortRef.current = null
                  setArticleBlocks([])
                  form.setValue('sourceArticleUrl', '')
                  form.setValue('sourceArticleContent', '')
                  form.setValue('translatedArticleContent', '')
                  setIsTranslating(false)
                  setTranslationProgress(0)
                }}
              >
                Clear
              </Button>
              <Button disabled={isLoading} variant="default" type="submit">Submit</Button>
              <Button
                type="button"
                disabled={isLoading || !form.getValues('sourceArticleContent') || !form.getValues('translatedArticleContent')}
                className="flex gap-x-2"
                onClick={handleCompare}
              >
                Compare <ChevronRight size={16} />
              </Button>
            </div>
          </div>
          {(isTranslating || translationProgress === 100) && (
            <div className="px-5 pb-2">
              <div className="flex items-center justify-between text-xs text-zinc-600 mb-1">
                <span>Translating article...</span>
                <span>{Math.round(translationProgress)}%</span>
              </div>
              <div className="w-full h-2 bg-zinc-200 rounded overflow-hidden">
                <div
                  className="h-full bg-blue-500 transition-all duration-500"
                  style={{ width: `${translationProgress}%` }}
                />
              </div>
            </div>
          )}

          <div className="flex justify-between py-2 px-5 mt-2 h-fit">
            <FormField
              control={form.control}
              name="sourceArticleUrl"
              render={({ field }) => (
                <FormItem className="w-2/5 flex items-center gap-x-4">
                  <FormLabel className="shrink-0">Source Article URL</FormLabel>
                  <FormControl>
                    <Input placeholder="Enter a URL" className="!mt-0" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="targetArticleLanguage"
              render={({ field }) => (
                <FormItem className="w-2/5 flex items-center gap-x-4">
                  <FormLabel className="shrink-0">Target Article Language</FormLabel>
                  <FormControl>
                    <Select
                      onValueChange={(value) => {
                        field.onChange(value);
                        onLanguageChange(value);
                      }}
                      defaultValue={field.value}
                      disabled={isLoading || availableTranslationLanguages.length === 0}
                    >
                      <SelectTrigger className="!mt-0">
                        <SelectValue placeholder="Language" />
                      </SelectTrigger>
                      <SelectContent>
                        {availableTranslationLanguages.map(language => (
                          <SelectItem value={language.value} key={language.value}>
                            {language.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>
          <div>
            {articleBlocks.map((block, index) => (
              <div key={index} className={getHighlightClass(block.displayType)}>
                <p className="text-xs text-zinc-600 px-2 pt-2">{block.label}</p>
                <p className="font-medium whitespace-pre-wrap break-words px-2 pb-2 max-h-[28rem] overflow-y-auto">
                  {block.content}
                </p>
              </div>
            ))}
          </div>
        </form>
      </Form>
    </section>
  )
}

export default TranslationSection
