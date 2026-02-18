import { cn } from '@/lib/utils';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'default' | 'win' | 'draw' | 'loss' | 'live' | 'outline';
  className?: string;
}

const variantClasses = {
  default: 'bg-slate-700 text-slate-200',
  win: 'bg-green-500/20 text-green-400',
  draw: 'bg-yellow-500/20 text-yellow-400',
  loss: 'bg-red-500/20 text-red-400',
  live: 'bg-red-500 text-white animate-pulse',
  outline: 'border border-slate-600 text-slate-300',
};

export function Badge({ children, variant = 'default', className }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
        variantClasses[variant],
        className
      )}
    >
      {children}
    </span>
  );
}
