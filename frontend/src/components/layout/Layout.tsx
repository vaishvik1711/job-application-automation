import { Outlet, NavLink, useLocation } from 'react-router-dom'
import { useUIStore } from '@/store'
import {
  LayoutDashboard,
  User,
  Search,
  Target,
  FileText,
  Kanban,
  BarChart3,
  Settings,
  ChevronLeft,
  ChevronRight,
  Bell,
  Moon,
  Sun,
  LogOut,
} from 'lucide-react'
import { cn } from '@/utils/helpers'
import { WebSocketStatus } from '@/components/WebSocketStatus'

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Profile', href: '/profile', icon: User },
  { name: 'Job Search', href: '/job-search', icon: Search },
  { name: 'Job Matching', href: '/job-matching', icon: Target },
  { name: 'Resume Builder', href: '/resume-builder', icon: FileText },
  { name: 'Applications', href: '/applications', icon: Kanban },
  { name: 'Analytics', href: '/analytics', icon: BarChart3 },
  { name: 'Settings', href: '/settings', icon: Settings },
] as const

export function Layout() {
  const { sidebarOpen, toggleSidebar, theme, setTheme } = useUIStore()
  const location = useLocation()

  const toggleTheme = () => {
    const newTheme = theme === 'dark' ? 'light' : 'dark'
    setTheme(newTheme)
    document.documentElement.classList.toggle('dark', newTheme === 'dark')
  }

  return (
    <div className="min-h-screen bg-background-light dark:bg-background-dark flex">
      {/* Sidebar */}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-700 transition-all duration-300 flex flex-col',
          sidebarOpen ? 'w-64' : 'w-20'
        )}
      >
        {/* Logo */}
        <div className="flex items-center justify-between h-16 px-4 border-b border-slate-200 dark:border-slate-700">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary-500 flex items-center justify-center">
              <Target className="w-5 h-5 text-white" />
            </div>
            {sidebarOpen && (
              <span className="font-bold text-lg text-slate-900 dark:text-white">JobApp AI</span>
            )}
          </div>
          <button
            onClick={toggleSidebar}
            className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            aria-label={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
          >
            {sidebarOpen ? <ChevronLeft className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto" role="navigation" aria-label="Main navigation">
          {navigation.map((item) => {
                return (
              <NavLink
                key={item.name}
                to={item.href}
                className={({ isActive }) =>
                  cn(
                    'sidebar-link',
                    isActive && 'sidebar-link-active',
                    !sidebarOpen && 'justify-center px-2'
                  )
                }
                title={sidebarOpen ? undefined : item.name}
                aria-label={item.name}
              >
                <item.icon className="w-5 h-5 flex-shrink-0" aria-hidden="true" />
                {sidebarOpen && <span>{item.name}</span>}
              </NavLink>
            )
          })}
        </nav>

        {/* Footer */}
        <div className="p-3 border-t border-slate-200 dark:border-slate-700">
          <div className="flex items-center justify-between">
            <button
              onClick={toggleTheme}
              className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
            >
              {theme === 'dark' ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
            </button>
            {sidebarOpen && (
              <button className="flex-1 ml-2 px-3 py-2 text-left text-sm text-slate-500 hover:text-slate-700 dark:hover:text-slate-300">
                <LogOut className="w-4 h-4 inline mr-2" /> Sign Out
              </button>
            )}
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main
        className={cn(
          'flex-1 min-h-screen transition-all duration-300',
          sidebarOpen ? 'lg:ml-64' : 'lg:ml-20'
        )}
      >
        {/* Top Bar */}
        <header className="sticky top-0 z-40 bg-white/80 dark:bg-slate-900/80 backdrop-blur-sm border-b border-slate-200 dark:border-slate-700">
          <div className="flex items-center justify-between h-16 px-6">
            <div className="flex items-center gap-4">
              <h1 className="text-xl font-semibold text-slate-900 dark:text-white">
                {navigation.find((n) => n.href === location.pathname)?.name || 'Dashboard'}
              </h1>
            </div>
            <div className="flex items-center gap-4">
              <WebSocketStatus compact />
              <button className="relative p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors">
                <Bell className="w-5 h-5 text-slate-600 dark:text-slate-400" />
                <span className="absolute top-1 right-1 w-2 h-2 bg-danger-500 rounded-full" />
              </button>
              <div className="w-8 h-8 rounded-full bg-primary-500 flex items-center justify-center text-white font-medium">
                JA
              </div>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <div className="p-6 lg:p-8">
          <Outlet />
        </div>
      </main>
    </div>
  )
}