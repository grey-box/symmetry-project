import { useMatch } from 'react-router-dom'
import ROUTES from '@/constants/ROUTES'

const PageHeader = () => {
  const isHomePage = useMatch(ROUTES.BASE)
  const isSettingsPage = useMatch(ROUTES.SETTINGS)

  return (
    <section className="flex justify-between">
      <div>
        <h1 className="text-base font-bold">
          {isSettingsPage
            ? 'Settings'
            : isHomePage
              ? 'Cross-Language Article Analysis'
              : ''}
        </h1>
        <p className="text-sm">
          {isSettingsPage
            ? 'Configure application settings'
            : isHomePage
              ? 'Compare Wikipedia articles across languages to find content gaps'
              : ''}
        </p>
      </div>
    </section>
  )
}

export default PageHeader
