import { cn } from '../lib/utils'

export function Card({ children, className }) {
  return (
    <div className={cn('bg-surface border border-border rounded-xl shadow-card', className)}>
      {children}
    </div>
  )
}

export function CardHeader({ title, subtitle, action, border = true }) {
  return (
    <div className={cn('flex items-center justify-between px-5 py-3.5',
      border && 'border-b border-border')}>
      <div>
        <p className="text-[13px] font-semibold text-ink">{title}</p>
        {subtitle && <p className="text-[11px] text-faint mt-0.5">{subtitle}</p>}
      </div>
      {action && <div>{action}</div>}
    </div>
  )
}

export function CardBody({ children, className }) {
  return <div className={cn('px-5 py-4', className)}>{children}</div>
}
