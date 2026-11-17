import { Outlet } from 'react-router-dom'
import Navbar from '@/components/Navbar'
import PageHeader from '@/components/PageHeader'

const Layout = () => {
  return (
    <div className="!bg-gray-50 min-h-full grid grid-cols-[100px_minmax(0,1fr)]">
      <Navbar />
      <main className="min-w-0 overflow-x-hidden text-black bg-gray-50 py-6 px-7 flex flex-col gap-y-6">
        <PageHeader />
        <Outlet />
      </main>
    </div>
  )
}

export default Layout
