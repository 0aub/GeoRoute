import { useMission } from '@/hooks/useMission';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { RefreshCw } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { RouteVerdict } from '@/types';

const verdictConfig: Record<
  RouteVerdict,
  { label: string; bgColor: string }
> = {
  success: {
    label: 'SUCCESS',
    bgColor: 'bg-[#00A05A]',
  },
  risk: {
    label: 'RISK',
    bgColor: 'bg-[#F5C623] text-black',
  },
  failed: {
    label: 'FAILED',
    bgColor: 'bg-[#DC2626]',
  },
};

interface TacticalRouteResultsProps {
  onRegenerate?: () => void;
}

export const TacticalRouteResults = ({ onRegenerate }: TacticalRouteResultsProps) => {
  const {
    tacticalRoutes,
    resetForRegeneration,
  } = useMission();

  if (tacticalRoutes.length === 0) return null;

  const handleRegenerate = () => {
    // Reset units so they can be reused for new route generation
    resetForRegeneration();
    if (onRegenerate) {
      setTimeout(() => onRegenerate(), 100);
    }
  };

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <Label className="text-[10px] font-semibold">Routes</Label>
        <Button
          size="sm"
          variant="ghost"
          onClick={handleRegenerate}
          className="h-5 px-1.5 text-[9px] gap-1 text-muted-foreground hover:text-foreground"
        >
          <RefreshCw className="w-2.5 h-2.5" />
          Regenerate
        </Button>
      </div>

      {/* Route list with inline colored dots */}
      <div className="space-y-0.5">
        {tacticalRoutes.map((route) => {
          const { classification } = route;
          const verdict = verdictConfig[classification.final_verdict];
          const routeColor = route.color === 'orange' ? 'bg-orange-500' : 'bg-green-500';

          return (
            <div
              key={route.route_id}
              className="flex items-center justify-between p-1 rounded text-[10px] bg-secondary/30"
            >
              <div className="flex items-center gap-1.5">
                <div className={cn('w-2.5 h-2.5 rounded-full', routeColor)} />
                <span>{route.name}</span>
              </div>
              <Badge className={cn('text-[8px] px-1 py-0 h-4', verdict.bgColor)}>
                {verdict.label}
              </Badge>
            </div>
          );
        })}
      </div>
    </div>
  );
};
