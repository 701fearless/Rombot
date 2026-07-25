import { Compass, House, Sparkles, UserRound } from 'lucide-react'
import { NavLink, Outlet } from 'react-router-dom'

const tabs = [
  { to: '/', label: '灵感', Icon: Sparkles, end: true },
  { to: '/home', label: '我的家', Icon: House },
  { to: '/discover', label: '发现', Icon: Compass },
  { to: '/me', label: '我的', Icon: UserRound },
]

export function AppShell() {
  return <div className='app-shell'>
    <aside className='app-nav' aria-label='主导航'>
      <NavLink to='/' className='app-nav__brand' aria-label='QQ House 首页'>Q</NavLink>
      <div className='app-nav__items'>{tabs.map(({ to, label, Icon, end }) =>
        <NavLink key={to} to={to} end={end} className={({ isActive }) => `app-nav__item ${isActive ? 'is-active' : ''}`}>
          <Icon aria-hidden='true' /><span>{label}</span>
        </NavLink>)}</div>
    </aside>
    <main className='app-content'><Outlet /></main>
  </div>
}
