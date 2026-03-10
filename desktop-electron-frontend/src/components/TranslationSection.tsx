import { useForm } from 'react-hook-form'
import { ChevronRight, Info } from 'lucide-react'
import { useCallback, useState, useEffect } from 'react'

import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { SelectData } from '@/models/SelectData'
import { fetchArticle } from '@/services/fetchArticle'
import { translateArticle } from '@/services/translateArticle'
import { useAppContext } from '@/context/AppContext'
import { TranslationFormType } from '@/models/TranslationFormType'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'

const TranslationSection = () => {
  const getColorClass = (type: any) => {
    switch (type) {
      case 'change':
        return 'bg-green-100';
      case 'addition':
        return 'bg-red-100';
      default:
        return '';
    }
  };
  
  const [availableTranslationLanguages, setAvailableTranslationLanguages] = useState<SelectData<string>[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [backendStatus, setBackendStatus] = useState<'unknown' | 'online' | 'offline'>('unknown')
  const [texts, setTexts] = useState([
    {
      editing: "",
      reference: "",
      suggestedContribution: "",
      suggestionType: ""
    }
  ]);

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
    
    const comparisonButton = document.querySelector('button[onClick*="Phase.AI_COMPARISON"]') as HTMLElement
    if (comparisonButton) {
      comparisonButton.click()
    }
    
    sessionStorage.setItem('comparisonData', JSON.stringify({
      sourceContent,
      translatedContent,
      sourceUrl,
      targetLanguage
    }))
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

  const onSubmit = useCallback(async (data: TranslationFormType) => {
    try {
      setIsLoading(true)
      await checkBackendStatus()
      const response = await fetchArticle(data.sourceArticleUrl)
      setValue('sourceArticleContent', response.data.sourceArticle)
      setValue('translatedArticleContent', '')
      setTexts([
        {
          editing: response.data.sourceArticle,
          reference: response.data.sourceArticle,
          suggestedContribution: '',
          suggestionType: 'change',
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
    try {
      setIsLoading(true)

      const sourceText = form.getValues('sourceArticleContent')
      const sourceUrl = form.getValues('sourceArticleUrl')
      const sourceLangMatch = sourceUrl.match(/https?:\/\/([a-z]{2})\.wikipedia\.org/)
      const sourceLanguage = sourceLangMatch ? sourceLangMatch[1] : 'en'

      if (!sourceText || !sourceText.trim()) {
        throw new Error('Source article content is empty.')
      }

      setValue('translatedArticleContent', '')
      setTexts([
        {
          editing: sourceText,
          reference: sourceText,
          suggestedContribution: '',
          suggestionType: 'change',
        },
      ])

      const response = await translateArticle(sourceText, sourceLanguage, language)
      const translatedArticle = typeof response.data?.translatedArticle === 'string'
        ? response.data.translatedArticle
        : ''

      if (!translatedArticle.trim()) {
        throw new Error('Translated content is empty.')
      }

      setValue('translatedArticleContent', translatedArticle)
      setTexts([
        {
          editing: sourceText,
          reference: sourceText,
          suggestedContribution: '',
          suggestionType: 'change',
        },
        {
          editing: translatedArticle,
          reference: translatedArticle,
          suggestedContribution: '',
          suggestionType: 'addition',
        },
      ]);
    } catch (error) {
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
                  setTexts([])
                  form.setValue('sourceArticleUrl', '')
                  form.setValue('sourceArticleContent', '')
                  form.setValue('translatedArticleContent', '')
                }}
              >
                Clear
              </Button>
              <Button disabled={isLoading} variant="default" type="submit">Submit</Button>
              <Button
                disabled={isLoading || !form.getValues('sourceArticleContent') || !form.getValues('translatedArticleContent')}
                className="flex gap-x-2"
                onClick={handleCompare}
              >
                Compare <ChevronRight size={16} />
              </Button>
            </div>
          </div>

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
            {texts.map((text, index) => (
              <div key={index} className={getColorClass(text.suggestionType)}>
                <p className="text-xs text-zinc-600 px-2 pt-2">
                  {index === 0 ? 'Source Content' : 'Translated Content'}
                </p>
                <p className="font-medium whitespace-pre-wrap break-words px-2 pb-2 max-h-[28rem] overflow-y-auto">
                  {text.reference}
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
