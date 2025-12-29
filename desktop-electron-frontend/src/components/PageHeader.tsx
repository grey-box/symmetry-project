import React from 'react'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { BookOpenText } from 'lucide-react'
import { useMatch } from 'react-router-dom'
import ROUTES from '@/constants/ROUTES'

const PageHeader = () => {
  const homePageMatch = useMatch(ROUTES.BASE)
  const settingsPageMatch = useMatch(ROUTES.SETTINGS)

  return (
    <section className="flex justify-between">
      <div>
        <h1 className="text-base font-bold">
          {
            settingsPageMatch ?
              'Settings'
              : homePageMatch ?
                'Hi there, Suraj'
                : ''
          }
        </h1>
        <p className="text-sm">
          {
            settingsPageMatch ?
              'You can set the settings according to your requirements'
              : homePageMatch ?
                'Here will be the content regarding the basic use of app.'
                : ''
          }
        </p>
      </div>
      <div className="flex items-center gap-x-2">
        <Select>
          <SelectTrigger className="w-[180px] border-slate-300">
            <SelectValue placeholder="Select a language" />
          </SelectTrigger>
          <SelectContent className="text-black">
            <SelectItem value="english">English</SelectItem>
            <SelectItem value="french">French</SelectItem>
            <SelectItem value="arabic">Arabic</SelectItem>
          </SelectContent>
        </Select>
        <div
          className="rounded-full size-11 flex items-center justify-center bg-white border-slate-200 border">
          <BookOpenText />
        </div>
      </div>
    </section>
  )
}

export default PageHeader
