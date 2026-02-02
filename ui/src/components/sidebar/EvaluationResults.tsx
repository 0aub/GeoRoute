import {
  Route,
  Clock,
  AlertTriangle,
  Shield,
  Crosshair,
  Flag,
  Heart,
  ChevronDown,
  ChevronRight,
  X,
} from 'lucide-react';
import { useState } from 'react';
import { useMission } from '@/hooks/useMission';
import { Button } from '@/components/ui/button';

function PositionIcon({ type }: { type: string }) {
  switch (type) {
    case 'overwatch':
      return <Crosshair className="h-3.5 w-3.5 text-yellow-500" />;
    case 'cover':
      return <Shield className="h-3.5 w-3.5 text-green-500" />;
    case 'rally':
      return <Flag className="h-3.5 w-3.5 text-orange-500" />;
    case 'danger':
      return <AlertTriangle className="h-3.5 w-3.5 text-red-500" />;
    case 'medic':
      return <Heart className="h-3.5 w-3.5 text-pink-500" />;
    default:
      return <Route className="h-3.5 w-3.5 text-muted-foreground" />;
  }
}

function RiskBadge({ level }: { level: string }) {
  const colors: Record<string, string> = {
    low: 'bg-green-500/20 text-green-400 border-green-500/30',
    medium: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    high: 'bg-red-500/20 text-red-400 border-red-500/30',
  };
  return (
    <span
      className={`text-[10px] px-1.5 py-0.5 rounded border ${colors[level] || colors.medium}`}
    >
      {level.toUpperCase()}
    </span>
  );
}

export function EvaluationResults() {
  const { routeEvaluation, setRouteEvaluation, clearDrawnWaypoints } = useMission();
  const [expandedSegment, setExpandedSegment] = useState<number | null>(null);

  if (!routeEvaluation) {
    return null;
  }

  const handleClear = () => {
    setRouteEvaluation(null);
    clearDrawnWaypoints();
  };

  // Count positions by type
  const positionCounts = routeEvaluation.positions.reduce(
    (acc, pos) => {
      acc[pos.position_type] = (acc[pos.position_type] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>
  );

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
          Route Evaluation
        </div>
        <Button variant="ghost" size="icon" className="h-5 w-5" onClick={handleClear}>
          <X className="h-3.5 w-3.5" />
        </Button>
      </div>

      {/* Route Stats */}
      <div className="grid grid-cols-2 gap-2">
        <div className="p-2 rounded bg-background-deep">
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Route className="h-3.5 w-3.5" />
            Distance
          </div>
          <div className="text-sm font-mono">
            {(routeEvaluation.route_distance_m / 1000).toFixed(2)} km
          </div>
        </div>
        <div className="p-2 rounded bg-background-deep">
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Clock className="h-3.5 w-3.5" />
            Est. Time
          </div>
          <div className="text-sm font-mono">
            {Math.round(routeEvaluation.estimated_time_minutes)} min
          </div>
        </div>
      </div>

      {/* Overall Assessment */}
      <div className="p-2 rounded bg-background-deep text-xs">
        {routeEvaluation.overall_assessment}
      </div>

      {/* Position Summary */}
      {Object.keys(positionCounts).length > 0 && (
        <div className="space-y-1.5">
          <div className="text-xs text-muted-foreground">Suggested Positions</div>
          <div className="flex flex-wrap gap-1.5">
            {Object.entries(positionCounts).map(([type, count]) => (
              <div
                key={type}
                className="flex items-center gap-1 px-2 py-1 rounded bg-background-deep text-xs"
              >
                <PositionIcon type={type} />
                <span className="capitalize">{type}</span>
                <span className="text-muted-foreground">x{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Segment Analysis */}
      {routeEvaluation.segment_analysis.length > 0 && (
        <div className="space-y-1.5">
          <div className="text-xs text-muted-foreground">Segment Analysis</div>
          <div className="space-y-1">
            {routeEvaluation.segment_analysis.map((seg) => (
              <div key={seg.segment_index} className="rounded bg-background-deep overflow-hidden">
                <button
                  className="w-full flex items-center justify-between p-2 text-left hover:bg-muted/50 transition-colors"
                  onClick={() =>
                    setExpandedSegment(
                      expandedSegment === seg.segment_index ? null : seg.segment_index
                    )
                  }
                >
                  <div className="flex items-center gap-2">
                    {expandedSegment === seg.segment_index ? (
                      <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
                    ) : (
                      <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
                    )}
                    <span className="text-xs">Segment {seg.segment_index + 1}</span>
                  </div>
                  <RiskBadge level={seg.risk_level} />
                </button>
                {expandedSegment === seg.segment_index && (
                  <div className="px-2 pb-2 pt-1 border-t border-border">
                    <p className="text-xs text-muted-foreground mb-1">{seg.description}</p>
                    {seg.suggestions.length > 0 && (
                      <ul className="text-xs space-y-0.5">
                        {seg.suggestions.map((sug, i) => (
                          <li key={i} className="flex items-start gap-1">
                            <span className="text-primary">-</span>
                            {sug}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
