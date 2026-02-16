/*
This file is critical as it handles all the rendering work on frontend.
Whether rendering source article from API call, providing translation languages in dropdown or
providing translated article, all the logic is handled here.
*/


import { useForm } from 'react-hook-form'
import { ChevronRight, Info, Play, Loader2 } from 'lucide-react'
import { useCallback, useState, useEffect } from 'react'

// Importing UI components and necessary services
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { SelectData } from '@/models/SelectData'
import { fetchArticle } from '@/services/fetchArticle'
import { translateArticle } from '@/services/translateArticle'
import { compareArticles } from '@/services/compareArticles'
import { useAppContext } from '@/context/AppContext'
import { TranslationFormType } from '@/models/TranslationFormType'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'

// Translation languages available for selection
const TRANSLATION_LANGUAGES = [
  { value: 'english', label: 'English' },
  { value: 'french', label: 'French' },
  { value: 'hindi', label: 'Hindi' },
  { value: 'arabic', label: 'Arabic' },
]


const TranslationSection = () => {
  // Function to assign background color based on suggestion type
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
  
  // State variables for storing available translation languages and article data
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

  // Setting up form handling with default values
  const form = useForm<TranslationFormType>({
    defaultValues: {
      sourceArticleUrl: '',
      targetArticleLanguage: 'English',
      sourceArticleContent: '',
      translatedArticleContent: '',
    },
  })

  // Accessing global context values
  const { translationTool, APIKey } = useAppContext()
  
  // Function to handle compare button click
  const handleCompare = useCallback(() => {
    // Get the form values
    const sourceContent = form.getValues('sourceArticleContent')
    const translatedContent = form.getValues('translatedArticleContent')
    const sourceUrl = form.getValues('sourceArticleUrl')
    const targetLanguage = form.getValues('targetArticleLanguage')
    
    // Navigate to comparison section using phase navigation
    const comparisonButton = document.querySelector('button[onClick*="Phase.AI_COMPARISON"]') as HTMLElement
    if (comparisonButton) {
      comparisonButton.click()
    }
    
    // Store the data in sessionStorage for the comparison section to access
    sessionStorage.setItem('comparisonData', JSON.stringify({
      sourceContent,
      translatedContent,
      sourceUrl,
      targetLanguage
    }))
  }, [form])

  // Extracting form methods
  const {
    handleSubmit,
    setValue,
  } = form
  
  // Function to check backend status using health endpoint
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

  // Check backend status when component mounts
  useEffect(() => {
    checkBackendStatus()
    
    // Set up periodic status check every 30 seconds
    const interval = setInterval(checkBackendStatus, 30000)
    
    return () => clearInterval(interval)
  }, [checkBackendStatus])

  // Function to handle form submission and fetch article data
  const onSubmit = useCallback(async (data: TranslationFormType) => {
    console.log("Translate button is hit")
    
    try {
      setIsLoading(true)
      // Check backend status before making request
      await checkBackendStatus()
      
      // Fetch the article content from the given URL
      const response = await fetchArticle(data.sourceArticleUrl)
      setValue('sourceArticleContent', response.data.sourceArticle)
      
      // Store fetched article content in texts array
      setTexts(prevTexts => [
        ...prevTexts,
        {
          editing: response.data.sourceArticle,
          reference: response.data.sourceArticle,
          suggestedContribution: '',
          suggestionType: 'change',
        },
      ]);

      // Set available translation languages
      setAvailableTranslationLanguages(
        response.data.articleLanguages.map(lang => ({
          value: lang,
          label: lang,
        })))
      
    } catch (error) {
      console.error('Error fetching article:', error)
      setIsLoading(false)
      
      // Provide user-friendly error messages based on error type
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
  
  // Function to handle language selection and translation
  const onLanguageChange = useCallback(async (language: string) => {
    try {
      setIsLoading(true)
      
      // Get the source article title from the URL
      const sourceUrl = form.getValues('sourceArticleUrl')
      const title = new URL(sourceUrl).pathname.split('/').pop() || sourceUrl
      
      const response = await translateArticle(title, language)
      console.log(response.data.translatedArticle)
      setValue('translatedArticleContent', response.data.translatedArticle)
    } catch (error) {
      console.error('Error translating article:', error)
      setIsLoading(false)
      
      // Provide user-friendly error messages based on error type
      let errorMessage = 'Failed to translate article. Please try again.'
      
      if (error instanceof Error) {
        if (error.message.includes('Network Error') || error.message.includes('ECONNREFUSED')) {
          errorMessage = 'Backend server is not running. Please start the backend server first.'
        } else if (error.message.includes('timeout')) {
          errorMessage = 'Request timed out. Please check your internet connection and try again.'
        } else if (error.message.includes('404')) {
          errorMessage = 'Translation not available for the selected language.'
        } else if (error.message.includes('400')) {
          errorMessage = 'Invalid translation request. Please try again.'
        } else {
          errorMessage = `Error: ${error.message}`
        }
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
          {/* Top section with instructions and buttons */}
          <div className="flex items-center justify-between p-4">
            <div className="flex items-center gap-x-4">
              <div className="inline-flex items-center gap-x-2">
                <Info size={16} />
                <span className="text-zinc-700 text-xs">
                  Here will be instruction regarding translation.
                </span>
              </div>
              
              {/* Backend Status Indicator */}
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
                  console.log("Clear button clicked")
                  setTexts([]) // Clear the texts state
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

          {/* Input fields for source article URL and target language selection */}
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
                        // Trigger translation when language changes
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
                <p className="font-medium">{text.reference}</p>
              </div>
            ))}
          </div>
        </form>
      </Form>
    </section>
  )
}

export default TranslationSection
