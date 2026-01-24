import { useMemo } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { ChevronUp, ChevronDown, Mountain } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useMission } from '@/hooks/useMission';
import type { ElevationPoint } from '@/types';

export const ElevationProfile = () => {
  const { routeResult, bottomPanelOpen, setBottomPanelOpen, setHoveredDistance, hoveredDistance } = useMission();

  const chartData = useMemo(() => {
    if (!routeResult?.elevationProfile) return [];
    return routeResult.elevationProfile;
  }, [routeResult]);

  const maxElevation = useMemo(() => {
    return Math.max(...chartData.map((d) => d.elevation), 0);
  }, [chartData]);

  const minElevation = useMemo(() => {
    return Math.min(...chartData.map((d) => d.elevation), 0);
  }, [chartData]);

  if (!routeResult) {
    return (
      <div className="h-[200px] bg-background-panel border-t border-border flex items-center justify-center">
        <div className="text-center text-foreground-muted">
          <Mountain className="w-8 h-8 mx-auto mb-2 opacity-50" />
          <p className="text-sm">No route data available</p>
          <p className="text-xs">Plan a route to see elevation profile</p>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`bg-background-panel border-t border-border transition-all duration-300 ${
        bottomPanelOpen ? 'h-[200px]' : 'h-10'
      }`}
    >
      {/* Header */}
      <div className="h-10 flex items-center justify-between px-4 border-b border-border/50">
        <div className="flex items-center gap-2">
          <Mountain className="w-4 h-4 text-primary" />
          <span className="text-sm font-medium">Elevation Profile</span>
          {chartData.length > 0 && (
            <span className="text-xs text-foreground-muted font-mono">
              {minElevation.toFixed(0)}m - {maxElevation.toFixed(0)}m
            </span>
          )}
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="h-6 w-6 p-0"
          onClick={() => setBottomPanelOpen(!bottomPanelOpen)}
        >
          {bottomPanelOpen ? (
            <ChevronDown className="w-4 h-4" />
          ) : (
            <ChevronUp className="w-4 h-4" />
          )}
        </Button>
      </div>

      {/* Chart */}
      {bottomPanelOpen && (
        <div className="h-[calc(100%-40px)] p-2">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={chartData}
              margin={{ top: 10, right: 20, left: 0, bottom: 0 }}
              onMouseMove={(e) => {
                if (e.activePayload?.[0]?.payload) {
                  setHoveredDistance(e.activePayload[0].payload.distance);
                }
              }}
              onMouseLeave={() => setHoveredDistance(null)}
            >
              <defs>
                <linearGradient id="elevationGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(210, 80%, 45%)" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="hsl(210, 80%, 45%)" stopOpacity={0.05} />
                </linearGradient>
                <linearGradient id="difficultGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(25, 100%, 50%)" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="hsl(25, 100%, 50%)" stopOpacity={0.05} />
                </linearGradient>
              </defs>
              <XAxis
                dataKey="distance"
                stroke="hsl(220, 15%, 55%)"
                tick={{ fontSize: 10, fill: 'hsl(220, 15%, 55%)' }}
                tickFormatter={(value) => `${value.toFixed(1)}km`}
                axisLine={{ stroke: 'hsl(220, 30%, 25%)' }}
              />
              <YAxis
                stroke="hsl(220, 15%, 55%)"
                tick={{ fontSize: 10, fill: 'hsl(220, 15%, 55%)' }}
                tickFormatter={(value) => `${value}m`}
                axisLine={{ stroke: 'hsl(220, 30%, 25%)' }}
                width={50}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'hsl(222, 50%, 16%)',
                  border: '1px solid hsl(220, 30%, 25%)',
                  borderRadius: '6px',
                  fontSize: '12px',
                }}
                labelStyle={{ color: 'hsl(60, 10%, 90%)' }}
                itemStyle={{ color: 'hsl(175, 70%, 45%)' }}
                formatter={(value: number) => [`${value.toFixed(0)}m`, 'Elevation']}
                labelFormatter={(value: number) => `Distance: ${value.toFixed(2)} km`}
              />
              {hoveredDistance !== null && (
                <ReferenceLine
                  x={hoveredDistance}
                  stroke="hsl(175, 70%, 45%)"
                  strokeDasharray="3 3"
                />
              )}
              <Area
                type="monotone"
                dataKey="elevation"
                stroke="hsl(210, 80%, 45%)"
                strokeWidth={2}
                fill="url(#elevationGradient)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
};
