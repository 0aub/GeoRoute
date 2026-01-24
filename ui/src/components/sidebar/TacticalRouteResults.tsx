import { useMission } from '@/hooks/useMission';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { ScoreBar } from '@/components/tactical/ScoreBar';
import { Eye, EyeOff, ChevronDown, ChevronUp } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useState } from 'react';
import type { RouteVerdict } from '@/types';

const verdictConfig: Record<
  RouteVerdict,
  { label: string; color: string; bgColor: string }
> = {
  success: {
    label: 'SUCCESS',
    color: 'text-white',
    bgColor: 'bg-[#00A05A]',  // Brand Light Green
  },
  risk: {
    label: 'RISK',
    color: 'text-black',
    bgColor: 'bg-[#F5C623]',  // Golden Yellow
  },
  failed: {
    label: 'FAILED',
    color: 'text-white',
    bgColor: 'bg-[#DC2626]',  // Clear Red
  },
};

export const TacticalRouteResults = () => {
  const {
    tacticalRoutes,
    routeVisibility,
    selectedRouteId,
    toggleRouteVisibility,
    setSelectedRoute,
  } = useMission();

  const [expandedRoutes, setExpandedRoutes] = useState<Record<number, boolean>>({});

  if (tacticalRoutes.length === 0) return null;

  const toggleExpanded = (routeId: number) => {
    setExpandedRoutes((prev) => ({ ...prev, [routeId]: !prev[routeId] }));
  };

  return (
    <div className="space-y-4">
      <Label className="text-base font-semibold">
        Tactical Routes ({tacticalRoutes.length})
      </Label>

      {tacticalRoutes.map((route) => {
        const { classification } = route;
        const isVisible = routeVisibility[route.route_id];
        const isSelected = selectedRouteId === route.route_id;
        const isExpanded = expandedRoutes[route.route_id];

        const verdict = verdictConfig[classification.final_verdict];

        return (
          <Card
            key={route.route_id}
            className={cn(
              'p-4 border-2 cursor-pointer transition-all',
              isSelected && 'border-primary ring-2 ring-primary/20',
              !isVisible && 'opacity-50'
            )}
            onClick={() => setSelectedRoute(route.route_id)}
          >
            {/* Header */}
            <div className="flex items-start justify-between mb-3">
              <div className="flex-1">
                <h3 className="font-semibold text-sm mb-1">{route.name}</h3>
                <p className="text-xs text-muted-foreground line-clamp-2">
                  {route.description}
                </p>
              </div>
              <div className="flex items-center gap-2 ml-2">
                <Badge className={cn('text-xs font-bold', verdict.bgColor)}>
                  {verdict.label}
                </Badge>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={(e) => {
                    e.stopPropagation();
                    toggleRouteVisibility(route.route_id);
                  }}
                  className="h-7 w-7 p-0"
                >
                  {isVisible ? (
                    <Eye className="w-4 h-4" />
                  ) : (
                    <EyeOff className="w-4 h-4" />
                  )}
                </Button>
              </div>
            </div>

            {/* Scores */}
            <div className="space-y-2 mb-3">
              <ScoreBar
                label="Time to Target"
                value={classification.scores.time_to_target}
                color="blue"
              />
              <ScoreBar
                label="Stealth"
                value={classification.scores.stealth_score}
                color="purple"
              />
              <ScoreBar
                label="Survival"
                value={classification.scores.survival_probability}
                color="green"
              />
              <ScoreBar
                label="Overall Score"
                value={classification.scores.overall_score}
                color="yellow"
              />
            </div>

            {/* Key Metrics */}
            <div className="grid grid-cols-2 gap-2 text-xs mb-3">
              <div className="bg-secondary p-2 rounded">
                <div className="text-muted-foreground">Distance</div>
                <div className="font-semibold">
                  {(route.total_distance_m / 1000).toFixed(2)} km
                </div>
              </div>
              <div className="bg-secondary p-2 rounded">
                <div className="text-muted-foreground">Duration</div>
                <div className="font-semibold">
                  {Math.round(route.estimated_duration_seconds / 60)} min
                </div>
              </div>
              <div className="bg-secondary p-2 rounded">
                <div className="text-muted-foreground">Detection</div>
                <div className="font-semibold">
                  {(classification.simulation.detection_probability * 100).toFixed(1)}%
                </div>
              </div>
              <div className="bg-secondary p-2 rounded">
                <div className="text-muted-foreground">Safe Route</div>
                <div className="font-semibold">
                  {classification.simulation.safe_percentage.toFixed(1)}%
                </div>
              </div>
            </div>

            {/* Expandable Details */}
            <Collapsible open={isExpanded} onOpenChange={() => toggleExpanded(route.route_id)}>
              <CollapsibleTrigger
                className="flex items-center gap-2 text-sm text-primary hover:underline w-full"
                onClick={(e) => e.stopPropagation()}
              >
                <span>AI Analysis</span>
                {isExpanded ? (
                  <ChevronUp className="w-4 h-4" />
                ) : (
                  <ChevronDown className="w-4 h-4" />
                )}
              </CollapsibleTrigger>
              <CollapsibleContent className="mt-2 space-y-2">
                <div className="text-xs bg-secondary/50 p-3 rounded">
                  <div className="font-semibold mb-1">Gemini Evaluation:</div>
                  <p className="text-muted-foreground">{classification.gemini_reasoning}</p>
                </div>
                <div className="text-xs bg-secondary/50 p-3 rounded">
                  <div className="font-semibold mb-1">Final Assessment:</div>
                  <p className="text-muted-foreground">{classification.final_reasoning}</p>
                </div>
                <div className="text-xs bg-secondary/50 p-3 rounded">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold">Confidence:</span>
                    <span className="font-mono">
                      {(classification.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
                <div className="text-xs bg-secondary/50 p-3 rounded">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold">Waypoints:</span>
                    <span>{route.waypoints.length}</span>
                  </div>
                  <div className="flex items-center justify-between mt-1">
                    <span className="font-semibold">Segments:</span>
                    <span>{route.segments.length}</span>
                  </div>
                </div>
              </CollapsibleContent>
            </Collapsible>
          </Card>
        );
      })}

      {/* Legend */}
      <div className="text-xs text-muted-foreground bg-secondary/50 p-3 rounded space-y-2">
        <div className="font-semibold mb-2">Route Classification:</div>
        <div className="flex items-center gap-2">
          <div className="w-16 h-3 bg-[#00A05A] rounded" />
          <span>SUCCESS: High survival probability (&gt;75%)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-16 h-3 bg-[#F5C623] rounded" />
          <span>RISK: Moderate risk, casualties likely (50-74%)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-16 h-3 bg-[#DC2626] rounded" />
          <span>FAILED: High risk of failure (&lt;50%)</span>
        </div>
        <div className="mt-3 pt-2 border-t border-border">
          <div className="font-semibold mb-2">Segment Risk Levels:</div>
          <div className="grid grid-cols-2 gap-1">
            <div className="flex items-center gap-1">
              <div className="w-8 h-2 bg-[#00A05A] rounded" />
              <span>Safe</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-8 h-2 bg-[#F5C623] rounded" />
              <span>Moderate</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-8 h-2 bg-[#FF6B00] rounded" />
              <span>High</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-8 h-2 bg-[#DC2626] rounded" />
              <span>Critical</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
