import { HTMLAttributes, createContext, useContext, forwardRef, ReactNode } from 'react'
import { cn } from '@/utils/helpers'

interface TabsContextValue {
  value: string
  onValueChange: (value: string) => void
}

const TabsContext = createContext<TabsContextValue | undefined>(undefined)

function useTabsContext() {
  const context = useContext(TabsContext)
  if (!context) {
    throw new Error('Tabs-related components must be used within Tabs')
  }
  return context
}

export interface TabsProps {
  value: string
  onValueChange: (value: string) => void
  className?: string
  defaultValue?: string
  children: ReactNode
}

export function Tabs({ value, onValueChange, className, children }: TabsProps) {
  return (
    <TabsContext.Provider value={{ value, onValueChange }}>
      <div className={cn('w-full', className)}>{children}</div>
    </TabsContext.Provider>
  )
}

export interface TabsListProps extends HTMLAttributes<HTMLDivElement> {}

export const TabsList = forwardRef<HTMLDivElement, TabsListProps>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      'inline-flex items-center justify-center rounded-lg bg-slate-100 dark:bg-slate-800 p-1 text-slate-500 dark:text-slate-400',
      className
    )}
    {...props}
  />
))
TabsList.displayName = 'TabsList'

export interface TabsTriggerProps extends HTMLAttributes<HTMLButtonElement> {
  value: string
}

export const TabsTrigger = forwardRef<HTMLButtonElement, TabsTriggerProps>(({ className, value, ...props }, ref) => {
  const { value: selectedValue, onValueChange } = useTabsContext()
  const isActive = selectedValue === value

  return (
    <button
      ref={ref}
      type="button"
      role="tab"
      aria-selected={isActive}
      onClick={() => onValueChange(value)}
      className={cn(
        'inline-flex items-center justify-center whitespace-nowrap rounded-md px-3 py-2 text-sm font-medium',
        'transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
        'disabled(pointer-events-none) disabled(opacity-50)',
        isActive
          ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-sm'
          : 'hover:bg-white/50 dark:hover:bg-slate-800/50',
        className
      )}
      {...props}
    />
  )
})
TabsTrigger.displayName = 'TabsTrigger'

export interface TabsContentProps extends HTMLAttributes<HTMLDivElement> {
  value: string
}

export const TabsContent = forwardRef<HTMLDivElement, TabsContentProps>(({ className, value, ...props }, ref) => {
  const { value: selectedValue } = useTabsContext()
  const isActive = selectedValue === value

  if (!isActive) return null

  return (
    <div
      ref={ref}
      role="tabpanel"
      className={cn(
        'mt-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        className
      )}
      {...props}
    />
  )
})
TabsContent.displayName = 'TabsContent'
