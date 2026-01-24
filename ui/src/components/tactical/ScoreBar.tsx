import { cn } from '@/lib/utils';

interface ScoreBarProps {
  label: string;
  value: number; // 0-100
  color?: 'blue' | 'green' | 'purple' | 'yellow';
  className?: string;
}

const colorClasses = {
  blue: 'bg-blue-500',
  green: 'bg-green-500',
  purple: 'bg-purple-500',
  yellow: 'bg-yellow-500',
};

export const ScoreBar = ({ label, value, color = 'blue', className }: ScoreBarProps) => {
  return (
    <div className={cn('space-y-1', className)}>
      <div className="flex justify-between text-xs">
        <span className="font-medium text-muted-foreground">{label}</span>
        <span className="font-semibold">{value.toFixed(0)}/100</span>
      </div>
      <div className="h-2 bg-secondary rounded-full overflow-hidden">
        <div
          className={cn('h-full transition-all duration-300 ease-out', colorClasses[color])}
          style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
        />
      </div>
    </div>
  );
};
