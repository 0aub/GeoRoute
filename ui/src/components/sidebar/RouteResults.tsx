import { useState } from 'react';
import {
  ChevronDown,
  ChevronUp,
  Clock,
  Route,
  Target,
  AlertTriangle,
  CheckCircle,
  ListChecks,
} from 'lucide-react';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useMission } from '@/hooks/useMission';
import { cn } from '@/lib/utils';

const difficultyConfig = {
  easy: { label: 'Easy', className: 'badge-easy' },
  moderate: { label: 'Moderate', className: 'badge-moderate' },
  difficult: { label: 'Difficult', className: 'badge-difficult' },
  very_difficult: { label: 'Very Difficult', className: 'badge-very-difficult' },
  impassable: { label: 'Impassable', className: 'badge-impassable' },
};

export const RouteResults = () => {
  const { routeResult } = useMission();
  const [challengesOpen, setChallengesOpen] = useState(false);
  const [recommendationsOpen, setRecommendationsOpen] = useState(false);

  if (!routeResult) return null;

  const difficulty = difficultyConfig[routeResult.difficulty];

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-sm font-semibold text-foreground uppercase tracking-wider">
        <Target className="w-4 h-4 text-success" />
        <span>Route Results</span>
      </div>

      <div className="p-3 bg-muted/30 rounded-md border border-success/30 space-y-4">
        <div className="flex items-center justify-between">
          <h4 className="font-medium text-foreground">{routeResult.name}</h4>
          <Badge className={cn('text-xs', difficulty.className)}>
            {difficulty.label}
          </Badge>
        </div>

        <div className="grid grid-cols-2 gap-3 text-sm">
          <div className="flex items-center gap-2">
            <Route className="w-4 h-4 text-foreground-muted" />
            <div>
              <div className="text-foreground-muted text-xs">Distance</div>
              <div className="font-mono font-semibold">
                {routeResult.totalDistance.toFixed(1)} km
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-foreground-muted" />
            <div>
              <div className="text-foreground-muted text-xs">Duration</div>
              <div className="font-mono font-semibold">
                {routeResult.estimatedDuration.toFixed(1)} hrs
              </div>
            </div>
          </div>
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="text-foreground-muted">Feasibility</span>
            <span className="font-mono font-semibold text-foreground-accent">
              {routeResult.feasibilityScore}%
            </span>
          </div>
          <Progress value={routeResult.feasibilityScore} className="h-2" />
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="text-foreground-muted">Confidence</span>
            <span className="font-mono font-semibold">
              {routeResult.confidenceScore}%
            </span>
          </div>
          <Progress value={routeResult.confidenceScore} className="h-2" />
        </div>

        {/* Key Challenges */}
        <div className="border-t border-border pt-3">
          <Button
            variant="ghost"
            className="w-full justify-between px-0 h-auto py-1 hover:bg-transparent"
            onClick={() => setChallengesOpen(!challengesOpen)}
          >
            <span className="flex items-center gap-2 text-sm">
              <AlertTriangle className="w-4 h-4 text-warning" />
              Key Challenges ({routeResult.keyChallenges.length})
            </span>
            {challengesOpen ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </Button>
          {challengesOpen && (
            <ul className="mt-2 space-y-1 text-xs text-foreground-muted">
              {routeResult.keyChallenges.map((challenge, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="text-warning mt-0.5">•</span>
                  {challenge}
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Recommendations */}
        <div className="border-t border-border pt-3">
          <Button
            variant="ghost"
            className="w-full justify-between px-0 h-auto py-1 hover:bg-transparent"
            onClick={() => setRecommendationsOpen(!recommendationsOpen)}
          >
            <span className="flex items-center gap-2 text-sm">
              <ListChecks className="w-4 h-4 text-success" />
              Recommendations ({routeResult.recommendations.length})
            </span>
            {recommendationsOpen ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </Button>
          {recommendationsOpen && (
            <ul className="mt-2 space-y-1 text-xs text-foreground-muted">
              {routeResult.recommendations.map((rec, i) => (
                <li key={i} className="flex items-start gap-2">
                  <CheckCircle className="w-3 h-3 text-success mt-0.5 shrink-0" />
                  {rec}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
};
