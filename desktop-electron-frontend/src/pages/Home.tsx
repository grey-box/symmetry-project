import { useEffect, useState } from 'react'
import { Phase } from '@/models/Phase'
import { Separator } from '@/components/ui/separator'
import StructuredArticleViewer from '@/components/StructuredArticleViewer'
import CrossLanguageComparison from '@/components/CrossLanguageComparison'
import ThroughTimeComparison from '@/components/ThroughTimeComparison'
import TranslationSection from '@/components/TranslationSection'
import ComparisonSection from '@/components/ComparisonSection'

const Home = () => {
  const [activeTab, setActiveTab] = useState(Phase.STRUCTURED_ARTICLE)

  useEffect(() => {
    const handleSetActiveTab = (event: Event) => {
      const customEvent = event as CustomEvent<Phase>
      if (customEvent.detail) {
        setActiveTab(customEvent.detail)
      }
    }

    window.addEventListener('set-active-tab', handleSetActiveTab as EventListener)
    return () => {
      window.removeEventListener('set-active-tab', handleSetActiveTab as EventListener)
    }
  }, [])

  const tabs = [
    { phase: Phase.STRUCTURED_ARTICLE, label: 'Structured Article' },
    { phase: Phase.CROSS_LANGUAGE_COMPARISON, label: 'Cross-Language Diff' },
    { phase: Phase.THROUGH_TIME_COMPARISON, label: 'Through-Time Diff' },
    { phase: Phase.TRANSLATION, label: 'Translation (Legacy)' },
    { phase: Phase.AI_COMPARISON, label: 'AI Comparison (Legacy)' },
  ]

  return (
    <section>
      {/* Tab Navigation */}
      <div className="flex gap-4 mb-6">
        {tabs.map(({ phase, label }) => (
          <button
            key={phase}
            className={`px-4 py-2 rounded-lg transition-colors ${activeTab === phase
                ? 'bg-blue-500 text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            onClick={() => setActiveTab(phase)}
          >
            {label}
          </button>
        ))}
      </div>

      <Separator className="mb-6" />

      {activeTab === Phase.STRUCTURED_ARTICLE && (
        <div id="structured-article-section">
          <StructuredArticleViewer initialLang="en" />
        </div>
      )}

      {activeTab === Phase.CROSS_LANGUAGE_COMPARISON && (
        <div id="cross-language-comparison-section">
          <CrossLanguageComparison />
        </div>
      )}

      {activeTab === Phase.THROUGH_TIME_COMPARISON && (
        <div id="through-time-comparison-section">
          <ThroughTimeComparison />
        </div>
      )}

      {activeTab === Phase.TRANSLATION && (
        <TranslationSection />
      )}

      {activeTab === Phase.AI_COMPARISON && (
        <div id="comparison-section">
          <ComparisonSection />
        </div>
      )}
    </section>
  )
}

export default Home
