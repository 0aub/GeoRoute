import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ApiCallCard } from './ApiCallCard';
import { GeminiRequestCard } from './GeminiRequestCard';
import { ImageGallery } from './ImageGallery';
import { JsonViewer } from './JsonViewer';
import type { BacklogEntry } from '@/types';
import { ChevronDown, ChevronUp, Users, Crosshair, Clock } from 'lucide-react';

interface BacklogCardProps {
  entry: BacklogEntry;
  isExpanded: boolean;
  onToggle: () => void;
}

const Section = ({ title, children }: { title: string; children: React.ReactNode }) => (
  <div className="space-y-2">
    <h3 className="font-semibold text-sm">{title}</h3>
    {children}
  </div>
);

export const BacklogCard = ({ entry, isExpanded, onToggle }: BacklogCardProps) => {
  return (
    <Card>
      <CardHeader className="cursor-pointer hover:bg-secondary/50 transition" onClick={onToggle}>
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <CardTitle className="text-base">
              {new Date(entry.timestamp).toLocaleString()}
            </CardTitle>
            <CardDescription className="flex items-center gap-4 mt-1">
              <span className="flex items-center gap-1">
                <Users className="w-3 h-3" />
                {entry.user_input.soldiers.length} soldiers
              </span>
              <span className="flex items-center gap-1">
                <Crosshair className="w-3 h-3" />
                {entry.user_input.enemies.length} enemies
              </span>
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {entry.total_duration_seconds.toFixed(1)}s
              </span>
            </CardDescription>
          </div>

          <div className="flex items-center gap-2">
            <Badge>{entry.result.routes.length} routes</Badge>
            <Badge variant="secondary">
              {entry.gemini_pipeline.length} AI stages
            </Badge>
            {isExpanded ? (
              <ChevronUp className="w-5 h-5" />
            ) : (
              <ChevronDown className="w-5 h-5" />
            )}
          </div>
        </div>
      </CardHeader>

      {isExpanded && (
        <CardContent className="space-y-6 pt-0">
          {/* User Input */}
          <Section title="User Input">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <div className="text-xs font-semibold mb-1">Soldiers</div>
                <JsonViewer data={entry.user_input.soldiers} maxHeight="200px" />
              </div>
              <div>
                <div className="text-xs font-semibold mb-1">Enemies</div>
                <JsonViewer data={entry.user_input.enemies} maxHeight="200px" />
              </div>
            </div>
            <div>
              <div className="text-xs font-semibold mb-1">Tactical Area Bounds</div>
              <JsonViewer data={entry.user_input.bounds} maxHeight="100px" />
            </div>
          </Section>

          {/* API Calls */}
          <Section title={`External API Calls (${entry.api_calls.length})`}>
            <div className="space-y-2">
              {entry.api_calls.map((call, i) => (
                <ApiCallCard key={i} call={call} index={i} />
              ))}
            </div>
          </Section>

          {/* Gemini Pipeline */}
          <Section title="Gemini AI Pipeline (4 Stages)">
            <div className="space-y-2">
              {entry.gemini_pipeline.map((req, i) => (
                <GeminiRequestCard key={i} request={req} index={i + 1} />
              ))}
            </div>
          </Section>

          {/* Images */}
          {(entry.satellite_image || entry.terrain_image) && (
            <Section title="Terrain & Satellite Imagery">
              <ImageGallery
                satellite={entry.satellite_image}
                terrain={entry.terrain_image}
              />
            </Section>
          )}

          {/* Generated Routes Summary */}
          <Section title={`Generated Routes (${entry.result.routes.length})`}>
            <div className="space-y-2">
              {entry.result.routes.map((route) => (
                <Card key={route.route_id} className="p-3 bg-secondary/30">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-semibold text-sm">{route.name}</span>
                    <Badge
                      className={
                        route.classification.final_verdict === 'success'
                          ? 'bg-green-500'
                          : route.classification.final_verdict === 'risk'
                          ? 'bg-yellow-500'
                          : 'bg-red-500'
                      }
                    >
                      {route.classification.final_verdict.toUpperCase()}
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground mb-2">{route.description}</p>
                  <div className="grid grid-cols-3 gap-2 text-xs">
                    <div>
                      <div className="text-muted-foreground">Distance</div>
                      <div className="font-semibold">
                        {(route.total_distance_m / 1000).toFixed(2)} km
                      </div>
                    </div>
                    <div>
                      <div className="text-muted-foreground">Waypoints</div>
                      <div className="font-semibold">{route.waypoints.length}</div>
                    </div>
                    <div>
                      <div className="text-muted-foreground">Overall Score</div>
                      <div className="font-semibold">
                        {route.classification.scores.overall_score.toFixed(0)}/100
                      </div>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          </Section>

          {/* Metadata */}
          <Section title="Request Metadata">
            <div className="grid grid-cols-3 gap-3 text-xs">
              <div className="bg-secondary/50 p-2 rounded">
                <div className="text-muted-foreground">Request ID</div>
                <div className="font-mono text-xs">{entry.request_id}</div>
              </div>
              <div className="bg-secondary/50 p-2 rounded">
                <div className="text-muted-foreground">Total Duration</div>
                <div>{entry.total_duration_seconds.toFixed(2)}s</div>
              </div>
              <div className="bg-secondary/50 p-2 rounded">
                <div className="text-muted-foreground">API Calls</div>
                <div>{entry.total_api_calls}</div>
              </div>
              <div className="bg-secondary/50 p-2 rounded">
                <div className="text-muted-foreground">Recommended Route</div>
                <div>Route {entry.result.recommended_route_id}</div>
              </div>
              <div className="bg-secondary/50 p-2 rounded">
                <div className="text-muted-foreground">Mission Assessment</div>
                <div className="truncate">{entry.result.mission_assessment}</div>
              </div>
              <div className="bg-secondary/50 p-2 rounded">
                <div className="text-muted-foreground">Timestamp</div>
                <div>{new Date(entry.timestamp).toISOString().split('T')[1].split('.')[0]}</div>
              </div>
            </div>
          </Section>
        </CardContent>
      )}
    </Card>
  );
};
