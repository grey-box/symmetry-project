import { Home, Settings, User } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import ROUTES from '@/constants/ROUTES'
import { cn } from '@/lib/utils'

const Navbar = () => {
  return (
    <nav className="bg-slate-100 px-4 py-5">
      <ul className="flex flex-col gap-y-5 text-black items-center">
        <li className="">
          <NavLink
            to={ROUTES.BASE}
            className={cn(
              ({ isActive, isPending }: { isActive: boolean, isPending: boolean }) =>
                isActive ? 'nav-active' : isPending ? 'pending' : '',
              'text-black p-3 cursor-pointer size-12  flex items-center justify-center hover:text-black',
            )}>
            <Home size={24} />
          </NavLink>
        </li>
        <li>
          <NavLink to={ROUTES.PROFILE} className={cn(
            ({ isActive, isPending }: { isActive: boolean, isPending: boolean }) =>
              isActive ? 'nav-active' : isPending ? 'pending' : '',
            'text-black p-3 cursor-pointer size-12  flex items-center justify-center hover:text-black',
          )}>
            <User size={24} />
          </NavLink>
        </li>
        <li>
          <NavLink to={ROUTES.SETTINGS} className={cn(
            ({ isActive, isPending }: { isActive: boolean, isPending: boolean }) =>
              isActive ? 'nav-active' : isPending ? 'pending' : '',
            'text-black p-3 cursor-pointer size-12  flex items-center justify-center hover:text-black',
          )}>
            <Settings size={24} />
          </NavLink>
        </li>
      </ul>

    </nav>
  )
}

export default Navbar
