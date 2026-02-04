import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Card } from '@/components/ui/card';
import {
  Target,
  Clock,
  Package,
  Shield,
  AlertTriangle,
  FileText,
  Trash2,
  MapPin,
  Calendar,
  Star,
  Route,
  ImageIcon,
  Award,
  Building,
  TreePine,
  Mountain,
  CheckCircle,
  XCircle,
  Eye,
  EyeOff,
  Compass,
  TrendingUp,
  Timer,
  Navigation,
  Flag,
  Footprints,
  Crosshair,
  Radio,
  Siren,
  ArrowRight,
  CircleDot,
  Zap,
} from 'lucide-react';
import { useMission, type TacticalReportEntry, type TacticalSimulationResult, type TacticalScores, type SimulationHistoryEntry } from '@/hooks/useMission';
import { cn } from '@/lib/utils';

const SEVERITY_COLORS = {
  low: 'text-green-500 bg-green-500/10 border-green-500/20',
  medium: 'text-yellow-500 bg-yellow-500/10 border-yellow-500/20',
  high: 'text-orange-500 bg-orange-500/10 border-orange-500/20',
  critical: 'text-red-500 bg-red-500/10 border-red-500/20',
};

// Verdict colors and styling (moved here for use in component)
const VERDICT_STYLES: Record<string, { bg: string; text: string; border: string }> = {
  EXCELLENT: { bg: 'bg-green-500/20', text: 'text-green-400', border: 'border-green-500/50' },
  GOOD: { bg: 'bg-blue-500/20', text: 'text-blue-400', border: 'border-blue-500/50' },
  ACCEPTABLE: { bg: 'bg-yellow-500/20', text: 'text-yellow-400', border: 'border-yellow-500/50' },
  RISKY: { bg: 'bg-red-500/20', text: 'text-red-400', border: 'border-red-500/50' },
};

export const TacticalReportModal = () => {
  const {
    tacticalAnalysisReport,
    tacticalReportHistory,
    selectedReportId,
    reportModalOpen,
    selectReport,
    removeReportFromHistory,
    setReportModalOpen,
    simulationResult,
    // Simulation history
    simulationHistory,
    selectedHistoryId,
    loadFromSimulationHistory,
    removeFromSimulationHistory,
    clearSimulationHistory,
    setSelectedHistoryId,
  } = useMission();

  const [activeTab, setActiveTab] = useState<string>('current');

  // Get the report to display - either current or selected from history
  const displayReport = selectedReportId
    ? tacticalReportHistory.find((r) => r.id === selectedReportId)?.report
    : tacticalAnalysisReport;

  const selectedHistoryEntry = selectedReportId
    ? tacticalReportHistory.find((r) => r.id === selectedReportId)
    : null;

  // Type-safe access to report
  const report = displayReport as TacticalReportEntry['report'] | null;

  // Check if we have simulation result (from Draw mode)
  const hasSimulationResult = !!simulationResult;

  const formatDate = (date: Date) => {
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      timeZone: 'Asia/Riyadh',
    }).format(new Date(date));
  };

  const formatCoords = (coords: { lat: number; lon: number }) => {
    return `${coords.lat.toFixed(4)}, ${coords.lon.toFixed(4)}`;
  };

  // Determine modal title based on content
  const modalTitle = hasSimulationResult ? 'Tactical Simulation Analysis' : 'Tactical Analysis Report';

  return (
    <Dialog open={reportModalOpen} onOpenChange={setReportModalOpen}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-purple-500" />
            {modalTitle}
          </DialogTitle>
        </DialogHeader>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col overflow-hidden">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="current">Current Analysis</TabsTrigger>
            <TabsTrigger value="history">
              History ({simulationHistory.length + tacticalReportHistory.length})
            </TabsTrigger>
          </TabsList>

          <TabsContent value="current" className="flex-1 overflow-hidden mt-4">
            <ScrollArea className="h-[65vh]">
              {/* Priority order:
                  1. If selectedReportId is set → user clicked tactical report from history → show that report
                  2. If simulationResult exists → show simulation (either current or loaded from history)
                  3. If tacticalAnalysisReport exists → show current tactical report
                  4. Otherwise → no analysis available
              */}
              {selectedReportId && report ? (
                <ReportContent report={report} />
              ) : hasSimulationResult ? (
                <SimulationResultContent result={simulationResult} />
              ) : report ? (
                <ReportContent report={report} />
              ) : (
                <div className="flex flex-col items-center justify-center h-48 text-muted-foreground">
                  <FileText className="w-12 h-12 mb-4 opacity-50" />
                  <p>No analysis available</p>
                  <p className="text-sm mt-2">
                    Run a tactical simulation or generate routes to see analysis
                  </p>
                </div>
              )}
            </ScrollArea>
          </TabsContent>

          <TabsContent value="history" className="flex-1 overflow-hidden mt-4">
            <ScrollArea className="h-[65vh]">
              {(simulationHistory.length > 0 || tacticalReportHistory.length > 0) ? (
                <div className="space-y-3 pr-4">
                  {/* Clear history button */}
                  <div className="flex justify-end mb-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-xs text-muted-foreground hover:text-destructive"
                      onClick={() => clearSimulationHistory()}
                    >
                      <Trash2 className="w-3 h-3 mr-1" />
                      Clear All
                    </Button>
                  </div>

                  {/* Simulation History (new feature) */}
                  {simulationHistory.length > 0 && (
                    <>
                      <div className="text-xs font-medium text-muted-foreground mb-2">Tactical Simulations</div>
                      {simulationHistory.map((entry) => {
                        const verdictStyle = entry.result.verdict
                          ? VERDICT_STYLES[entry.result.verdict]
                          : VERDICT_STYLES.ACCEPTABLE;

                        return (
                          <Card
                            key={entry.id}
                            className={cn(
                              'p-3 cursor-pointer transition-all hover:border-primary/50',
                              selectedHistoryId === entry.id && 'border-primary ring-1 ring-primary/30'
                            )}
                            onClick={() => {
                              loadFromSimulationHistory(entry.id);
                              setActiveTab('current');
                            }}
                          >
                            <div className="flex items-start justify-between">
                              <div className="flex-1">
                                <div className="flex items-center gap-2 mb-2">
                                  {entry.result.verdict && (
                                    <span className={cn(
                                      'text-xs font-bold px-2 py-0.5 rounded',
                                      verdictStyle.bg, verdictStyle.text
                                    )}>
                                      {entry.result.verdict}
                                    </span>
                                  )}
                                  <span className={cn(
                                    'text-sm font-bold',
                                    entry.result.strategy_rating >= 8 ? 'text-green-400' :
                                    entry.result.strategy_rating >= 6 ? 'text-blue-400' :
                                    entry.result.strategy_rating >= 4 ? 'text-yellow-400' : 'text-red-400'
                                  )}>
                                    {entry.result.strategy_rating.toFixed(1)}/10
                                  </span>
                                </div>
                                <div className="flex items-center gap-3 text-xs text-muted-foreground mb-1">
                                  <span className="flex items-center gap-1">
                                    <Calendar className="w-3 h-3" />
                                    {formatDate(entry.timestamp)}
                                  </span>
                                  <span className="flex items-center gap-1">
                                    <Target className="w-3 h-3 text-red-400" />
                                    {entry.enemyCount} enemies
                                  </span>
                                  <span className="flex items-center gap-1">
                                    <Route className="w-3 h-3 text-blue-400" />
                                    {entry.waypointCount} waypoints
                                  </span>
                                </div>
                                {entry.result.overall_assessment && (
                                  <p className="text-xs text-muted-foreground line-clamp-2 mt-1">
                                    {entry.result.overall_assessment}
                                  </p>
                                )}
                              </div>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-8 w-8 p-0 text-muted-foreground hover:text-destructive shrink-0"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  removeFromSimulationHistory(entry.id);
                                }}
                              >
                                <Trash2 className="w-4 h-4" />
                              </Button>
                            </div>
                          </Card>
                        );
                      })}
                    </>
                  )}

                  {/* Route Generation History (old feature) */}
                  {tacticalReportHistory.length > 0 && (
                    <>
                      {simulationHistory.length > 0 && <div className="border-t my-4" />}
                      <div className="text-xs font-medium text-muted-foreground mb-2">Route Planning</div>
                      {tacticalReportHistory.map((entry) => (
                        <Card
                          key={entry.id}
                          className={cn(
                            'p-3 cursor-pointer transition-all hover:border-primary/50',
                            selectedReportId === entry.id && 'border-primary ring-1 ring-primary/30'
                          )}
                          onClick={() => {
                            selectReport(entry.id);
                            setActiveTab('current');
                          }}
                        >
                          <div className="flex items-start justify-between">
                            <div className="flex-1">
                              <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
                                <Calendar className="w-3 h-3" />
                                <span>{formatDate(entry.timestamp)}</span>
                                <span className="mx-1">|</span>
                                <MapPin className="w-3 h-3" />
                                <span>{formatCoords(entry.centerCoords)}</span>
                              </div>
                              {entry.report.mission_summary && (
                                <p className="text-sm line-clamp-2">
                                  {entry.report.mission_summary}
                                </p>
                              )}
                              {entry.report.recommended_approach && (
                                <div className="mt-1 text-xs text-green-500">
                                  Recommended: {entry.report.recommended_approach.route?.toUpperCase()} route
                                </div>
                              )}
                            </div>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-8 w-8 p-0 text-muted-foreground hover:text-destructive"
                              onClick={(e) => {
                                e.stopPropagation();
                                removeReportFromHistory(entry.id);
                              }}
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </div>
                        </Card>
                      ))}
                    </>
                  )}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center h-48 text-muted-foreground">
                  <FileText className="w-12 h-12 mb-4 opacity-50" />
                  <p>No analysis history</p>
                  <p className="text-sm mt-2">
                    Reports are automatically saved when you run analysis
                  </p>
                </div>
              )}
            </ScrollArea>
          </TabsContent>
        </Tabs>

        {/* Show indicator when viewing simulation from history */}
        {selectedHistoryId && activeTab === 'current' && (() => {
          const historyEntry = simulationHistory.find(h => h.id === selectedHistoryId);
          return historyEntry ? (
            <div className="mt-2 pt-2 border-t text-xs text-muted-foreground flex items-center justify-between">
              <span className="flex items-center gap-2">
                <Clock className="w-3 h-3" />
                Viewing simulation from {formatDate(historyEntry.timestamp)}
              </span>
              <Button
                variant="link"
                size="sm"
                className="text-xs h-auto p-0"
                onClick={() => setSelectedHistoryId(null)}
              >
                Return to current
              </Button>
            </div>
          ) : null;
        })()}

        {/* Show indicator when viewing tactical report from history */}
        {selectedReportId && activeTab === 'current' && (() => {
          const reportEntry = tacticalReportHistory.find(r => r.id === selectedReportId);
          return reportEntry ? (
            <div className="mt-2 pt-2 border-t text-xs text-muted-foreground flex items-center justify-between">
              <span className="flex items-center gap-2">
                <Clock className="w-3 h-3" />
                Viewing route planning report from {formatDate(reportEntry.timestamp)}
              </span>
              <Button
                variant="link"
                size="sm"
                className="text-xs h-auto p-0"
                onClick={() => selectReport(null)}
              >
                Return to current
              </Button>
            </div>
          ) : null;
        })()}
      </DialogContent>
    </Dialog>
  );
};

// Cover status colors
const COVER_STATUS_COLORS: Record<string, { bg: string; text: string }> = {
  exposed: { bg: 'bg-red-500', text: 'text-red-400' },
  partial: { bg: 'bg-amber-500', text: 'text-amber-400' },
  covered: { bg: 'bg-green-500', text: 'text-green-400' },
  clear: { bg: 'bg-blue-500', text: 'text-blue-400' },
};

// Cover type icons
const getCoverTypeIcon = (coverType: string | null) => {
  switch (coverType) {
    case 'building': return <Building className="w-3 h-3" />;
    case 'vegetation': return <TreePine className="w-3 h-3" />;
    case 'terrain': return <Mountain className="w-3 h-3" />;
    default: return null;
  }
};

// Component for simulation result content (Draw mode)
const SimulationResultContent = ({ result }: { result: TacticalSimulationResult }) => {
  const {
    annotated_image,
    strategy_rating,
    verdict,
    tactical_scores,
    flanking_analysis,
    segment_cover_analysis,
    cover_breakdown,
    weak_spots,
    strong_points,
    overall_assessment,
    terrain_assessment,
    recommendations,
    route_distance_m,
    estimated_time_minutes,
  } = result;

  // Rating color based on score
  const getRatingColor = (rating: number) => {
    if (rating >= 8) return 'text-green-500';
    if (rating >= 6) return 'text-yellow-500';
    if (rating >= 4) return 'text-orange-500';
    return 'text-red-500';
  };

  // Radar Chart Component for tactical scores - compact size
  const RadarChart = ({ scores }: { scores: TacticalScores }) => {
    const width = 200;  // Compact width
    const height = 160;
    const centerX = width / 2;  // 100
    const centerY = height / 2; // 80
    const radius = 40; // Smaller chart radius
    const labels = ['Stealth', 'Safety', 'Terrain', 'Flanking'];
    const values = [scores.stealth, scores.safety, scores.terrain_usage, scores.flanking];
    const numPoints = 4;

    const getPoint = (index: number, value: number) => {
      const angle = (Math.PI * 2 * index) / numPoints - Math.PI / 2;
      const r = (value / 100) * radius;
      return { x: centerX + r * Math.cos(angle), y: centerY + r * Math.sin(angle) };
    };

    const gridLevels = [25, 50, 75, 100];
    const polygonPoints = values.map((v, i) => getPoint(i, v));
    const polygonPath = polygonPoints.map(p => `${p.x},${p.y}`).join(' ');

    // Labels with proper margins - left/right pushed further out
    const labelConfigs = [
      { x: centerX, y: 12, anchor: 'middle', baseline: 'hanging' },      // Top (Stealth)
      { x: width - 5, y: centerY, anchor: 'end', baseline: 'middle' },   // Right (Safety) - at edge
      { x: centerX, y: height - 12, anchor: 'middle', baseline: 'auto' },// Bottom (Terrain)
      { x: 5, y: centerY, anchor: 'start', baseline: 'middle' },         // Left (Flanking) - at edge
    ];

    return (
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
        {/* Grid polygons */}
        {gridLevels.map((level) => (
          <polygon
            key={level}
            points={Array.from({ length: numPoints }, (_, i) => {
              const p = getPoint(i, level);
              return `${p.x},${p.y}`;
            }).join(' ')}
            fill="none"
            stroke="currentColor"
            strokeOpacity={0.15}
            strokeWidth={1}
          />
        ))}
        {/* Axis lines */}
        {Array.from({ length: numPoints }, (_, i) => {
          const p = getPoint(i, 100);
          return <line key={i} x1={centerX} y1={centerY} x2={p.x} y2={p.y} stroke="currentColor" strokeOpacity={0.2} strokeWidth={1} />;
        })}
        {/* Data polygon */}
        <polygon points={polygonPath} fill="rgba(59, 130, 246, 0.3)" stroke="rgb(59, 130, 246)" strokeWidth={2} />
        {/* Labels with values below (or above for bottom label) */}
        {labels.map((label, i) => {
          // Offset for value text: positive = below, negative = above
          const valueOffset = i === 2 ? -10 : 10; // Bottom label: value above, others: value below
          return (
            <g key={i}>
              <text
                x={labelConfigs[i].x}
                y={labelConfigs[i].y}
                textAnchor={labelConfigs[i].anchor}
                dominantBaseline={labelConfigs[i].baseline}
                className="fill-muted-foreground text-[9px] font-medium"
              >
                {label}
              </text>
              <text
                x={labelConfigs[i].x}
                y={labelConfigs[i].y + valueOffset}
                textAnchor={labelConfigs[i].anchor}
                dominantBaseline={labelConfigs[i].baseline}
                className="fill-blue-400 text-[10px] font-bold"
              >
                {Math.round(values[i])}
              </text>
            </g>
          );
        })}
      </svg>
    );
  };

  // Mini Gauge Chart Component for individual scores
  const MiniGauge = ({ value, label, color }: { value: number; label: string; color: string }) => {
    const width = 80;
    const height = 60;
    const centerX = width / 2;
    const centerY = height - 8;
    const radius = 32;

    // Arc from -150° to -30° (120° sweep)
    const startAngle = -150;
    const endAngle = -30;
    const sweepAngle = endAngle - startAngle;

    const valueAngle = startAngle + (value / 100) * sweepAngle;

    const polarToCartesian = (angle: number, r: number) => {
      const rad = (angle * Math.PI) / 180;
      return {
        x: centerX + r * Math.cos(rad),
        y: centerY + r * Math.sin(rad),
      };
    };

    const describeArc = (startA: number, endA: number, r: number) => {
      const start = polarToCartesian(startA, r);
      const end = polarToCartesian(endA, r);
      const largeArc = Math.abs(endA - startA) > 180 ? 1 : 0;
      return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} 1 ${end.x} ${end.y}`;
    };

    const getColor = (v: number) => {
      if (v >= 80) return '#22c55e';
      if (v >= 60) return '#3b82f6';
      if (v >= 40) return '#eab308';
      return '#ef4444';
    };

    const displayColor = getColor(value);

    return (
      <div className="flex flex-col items-center">
        <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
          {/* Background arc */}
          <path
            d={describeArc(startAngle, endAngle, radius)}
            fill="none"
            stroke="currentColor"
            strokeOpacity={0.15}
            strokeWidth={6}
            strokeLinecap="round"
          />
          {/* Value arc */}
          <path
            d={describeArc(startAngle, valueAngle, radius)}
            fill="none"
            stroke={displayColor}
            strokeWidth={6}
            strokeLinecap="round"
          />
          {/* Value text */}
          <text
            x={centerX}
            y={centerY - 8}
            textAnchor="middle"
            dominantBaseline="middle"
            className="fill-foreground text-sm font-bold"
          >
            {Math.round(value)}
          </text>
        </svg>
        <span className="text-[10px] text-muted-foreground -mt-1">{label}</span>
      </div>
    );
  };

  // Flanking detection: consider both calculated angle AND AI tactical score
  // A route can be a "flanking maneuver" strategically even if the final approach angle is lower
  // - If approach_angle >= 90: definitely flanking (mathematical)
  // - If tactical_scores.flanking >= 70: AI identified flanking strategy (even if final angle is tighter)
  const hasFlankingFromAngle = flanking_analysis && flanking_analysis.approach_angle >= 90;
  const hasFlankingFromAI = tactical_scores && tactical_scores.flanking >= 70 &&
    segment_cover_analysis && segment_cover_analysis.length > 0; // Only trust if AI actually analyzed
  const effectiveFlanking = hasFlankingFromAngle || hasFlankingFromAI;

  const verdictStyle = verdict ? VERDICT_STYLES[verdict] : VERDICT_STYLES.ACCEPTABLE;

  return (
    <div className="space-y-4 pr-4">
      {/* Header: Verdict + Rating + Quick Stats */}
      <Card className="p-4">
        <div className="flex items-start justify-between mb-4">
          {/* Verdict Badge */}
          {verdict && (
            <div className={cn(
              'px-4 py-2 rounded-lg border-2 font-bold text-lg',
              verdictStyle.bg, verdictStyle.text, verdictStyle.border
            )}>
              <div className="flex items-center gap-2">
                <Award className="w-5 h-5" />
                {verdict}
              </div>
            </div>
          )}

          {/* Strategy Rating */}
          <div className="text-right">
            <div className="flex items-center gap-2 justify-end">
              <Star className="w-5 h-5 text-yellow-500" />
              <span className={cn('text-3xl font-bold', getRatingColor(strategy_rating))}>
                {strategy_rating.toFixed(1)}
              </span>
              <span className="text-muted-foreground text-lg">/10</span>
            </div>
            {flanking_analysis?.bonus_awarded != null && flanking_analysis.bonus_awarded > 0 && (
              <div className="text-xs text-green-400 mt-1">
                +{flanking_analysis.bonus_awarded.toFixed(1)} flanking bonus
              </div>
            )}
          </div>
        </div>

        {/* Quick Stats Row */}
        <div className="grid grid-cols-4 gap-3 text-center border-t pt-3">
          <div>
            <div className="text-xs text-muted-foreground">Distance</div>
            <div className="font-semibold">{(route_distance_m / 1000).toFixed(2)} km</div>
          </div>
          <div>
            <div className="text-xs text-muted-foreground">Est. Time</div>
            <div className="font-semibold">{estimated_time_minutes.toFixed(0)} min</div>
          </div>
          <div>
            <div className="text-xs text-muted-foreground">Cover</div>
            <div className="font-semibold text-green-400">
              {cover_breakdown?.overall_cover_percentage?.toFixed(0) || '--'}%
            </div>
          </div>
          <div>
            <div className="text-xs text-muted-foreground">Flanking</div>
            <div className={cn('font-semibold', effectiveFlanking ? 'text-green-400' : 'text-muted-foreground')}>
              {effectiveFlanking ? 'Yes' : 'No'}
            </div>
          </div>
        </div>
      </Card>

      {/* Tactical Scores - Dual Charts */}
      {tactical_scores && (
        <Card className="p-4">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-blue-400" />
              <span className="font-semibold">Tactical Performance</span>
              {/* AI-generated indicator */}
              {segment_cover_analysis && segment_cover_analysis.length > 0 && segment_cover_analysis.some(s => s.explanation && s.explanation.length > 10) ? (
                <span className="text-[9px] px-1.5 py-0.5 rounded bg-green-500/20 text-green-400 border border-green-500/30 flex items-center gap-1">
                  <Zap className="w-2.5 h-2.5" />AI
                </span>
              ) : (
                <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400 border border-amber-500/30">
                  Geometric
                </span>
              )}
            </div>
            <div className="flex items-center gap-3">
              <div className="text-center">
                <div className="text-[10px] text-muted-foreground uppercase">Overall</div>
                <div className={cn(
                  'text-2xl font-bold leading-none',
                  tactical_scores.overall >= 80 ? 'text-green-400' :
                  tactical_scores.overall >= 60 ? 'text-blue-400' :
                  tactical_scores.overall >= 40 ? 'text-yellow-400' : 'text-red-400'
                )}>
                  {Math.round(tactical_scores.overall)}
                </div>
              </div>
            </div>
          </div>

          {/* Charts Section */}
          <div className="space-y-4">
            {/* Radar Chart */}
            <div className="flex justify-center">
              <RadarChart scores={tactical_scores} />
            </div>

            {/* Separator */}
            <div className="border-t border-secondary" />

            {/* 4 Mini Gauges */}
            <div className="grid grid-cols-4 gap-2">
              <MiniGauge value={tactical_scores.stealth} label="Stealth" color="#3b82f6" />
              <MiniGauge value={tactical_scores.safety} label="Safety" color="#22c55e" />
              <MiniGauge value={tactical_scores.terrain_usage} label="Terrain" color="#f59e0b" />
              <MiniGauge value={tactical_scores.flanking} label="Flanking" color="#8b5cf6" />
            </div>
          </div>

          {/* Score interpretation */}
          <div className="mt-3 pt-3 border-t border-secondary text-xs text-center text-muted-foreground flex items-center justify-center gap-2">
            {tactical_scores.overall >= 80 ? (
              <><Target className="w-3.5 h-3.5 text-green-400" /><span>Excellent tactical approach - proceed with confidence</span></>
            ) : tactical_scores.overall >= 60 ? (
              <><CheckCircle className="w-3.5 h-3.5 text-blue-400" /><span>Good tactical plan - minor adjustments recommended</span></>
            ) : tactical_scores.overall >= 40 ? (
              <><AlertTriangle className="w-3.5 h-3.5 text-yellow-400" /><span>Acceptable risk level - consider improvements</span></>
            ) : (
              <><XCircle className="w-3.5 h-3.5 text-red-400" /><span>High risk approach - significant modifications needed</span></>
            )}
          </div>
        </Card>
      )}

      {/* Cover Breakdown */}
      {cover_breakdown && (
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-3">
            <Shield className="w-4 h-4 text-green-400" />
            <span className="font-semibold">Cover Analysis</span>
            {segment_cover_analysis && segment_cover_analysis.length > 0 && segment_cover_analysis.some(s => s.cover_type && s.cover_type !== 'none') ? (
              <span className="text-[9px] px-1.5 py-0.5 rounded bg-green-500/20 text-green-400 border border-green-500/30 flex items-center gap-1">
                <Zap className="w-2.5 h-2.5" />AI
              </span>
            ) : (
              <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400 border border-amber-500/30">
                Geometric
              </span>
            )}
          </div>

          {/* Visual breakdown bar */}
          <div className="h-4 rounded-full overflow-hidden flex mb-3">
            {cover_breakdown.covered_count > 0 && (
              <div
                className="bg-green-500 h-full"
                style={{ width: `${(cover_breakdown.covered_count / cover_breakdown.total_segments) * 100}%` }}
                title={`Covered: ${cover_breakdown.covered_count}`}
              />
            )}
            {cover_breakdown.partial_count > 0 && (
              <div
                className="bg-amber-500 h-full"
                style={{ width: `${(cover_breakdown.partial_count / cover_breakdown.total_segments) * 100}%` }}
                title={`Partial: ${cover_breakdown.partial_count}`}
              />
            )}
            {cover_breakdown.clear_count > 0 && (
              <div
                className="bg-blue-500 h-full"
                style={{ width: `${(cover_breakdown.clear_count / cover_breakdown.total_segments) * 100}%` }}
                title={`Clear: ${cover_breakdown.clear_count}`}
              />
            )}
            {cover_breakdown.exposed_count > 0 && (
              <div
                className="bg-red-500 h-full"
                style={{ width: `${(cover_breakdown.exposed_count / cover_breakdown.total_segments) * 100}%` }}
                title={`Exposed: ${cover_breakdown.exposed_count}`}
              />
            )}
          </div>

          {/* Legend */}
          <div className="grid grid-cols-4 gap-2 text-xs">
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded bg-green-500" />
              <span>Covered ({cover_breakdown.covered_count})</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded bg-amber-500" />
              <span>Partial ({cover_breakdown.partial_count})</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded bg-blue-500" />
              <span>Clear ({cover_breakdown.clear_count})</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded bg-red-500" />
              <span>Exposed ({cover_breakdown.exposed_count})</span>
            </div>
          </div>

          {/* Cover types used */}
          {cover_breakdown.cover_types_used.length > 0 && (
            <div className="mt-3 pt-2 border-t flex items-center gap-2 text-xs text-muted-foreground">
              <span>Cover types:</span>
              {cover_breakdown.cover_types_used.map((type, i) => (
                <div key={i} className="flex items-center gap-1 px-2 py-0.5 bg-secondary rounded">
                  {getCoverTypeIcon(type)}
                  <span className="capitalize">{type}</span>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {/* Flanking Analysis */}
      {effectiveFlanking && (
        <Card className="p-4 bg-green-500/10 border-green-500/30">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Compass className="w-4 h-4 text-green-400" />
              <span className="font-semibold text-green-400">Flanking Maneuver Detected</span>
              {flanking_analysis?.description && flanking_analysis.description !== "Flanking analysis not available" ? (
                <span className="text-[9px] px-1.5 py-0.5 rounded bg-green-500/20 text-green-400 border border-green-500/30 flex items-center gap-1">
                  <Zap className="w-2.5 h-2.5" />AI
                </span>
              ) : (
                <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400 border border-amber-500/30">
                  Calculated
                </span>
              )}
            </div>
            <div className="px-2 py-1 rounded-full bg-green-500/20 text-green-400 text-xs font-bold">
              +{(flanking_analysis?.bonus_awarded ?? 0).toFixed(1)} Bonus
            </div>
          </div>

          {/* Visual angle indicator */}
          <div className="flex items-center gap-4 mb-3">
            <div className="relative w-16 h-16">
              {/* Enemy circle */}
              <div className="absolute inset-0 rounded-full border-2 border-red-500/30" />
              {/* Enemy facing direction */}
              <div className="absolute top-0 left-1/2 -translate-x-1/2 w-0.5 h-6 bg-red-500/50" />
              {/* Your approach direction - use ?? to preserve 0 as valid value */}
              <div
                className="absolute top-1/2 left-1/2 w-0.5 h-6 bg-green-500 origin-bottom"
                style={{ transform: `translate(-50%, -100%) rotate(${flanking_analysis?.approach_angle ?? 0}deg)` }}
              />
              {/* Center dot */}
              <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-2 h-2 rounded-full bg-red-500" />
            </div>
            <div className="flex-1 text-sm">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-muted-foreground">Approach Angle:</span>
                <span className="font-bold text-green-400">{(flanking_analysis?.approach_angle ?? 0).toFixed(0)}°</span>
                <span className="text-xs text-muted-foreground">from enemy facing</span>
              </div>
              <p className="text-xs text-muted-foreground">
                {(flanking_analysis?.approach_angle ?? 0) >= 150 ? 'Rear attack - Maximum surprise' :
                 (flanking_analysis?.approach_angle ?? 0) >= 120 ? 'Strong flank - Enemy blind spot' :
                 (flanking_analysis?.approach_angle ?? 0) >= 90 ? 'Side approach - Reduced detection' :
                 'Partial flank - Some tactical advantage'}
              </p>
            </div>
          </div>

          <div className="text-xs text-muted-foreground p-2 rounded bg-secondary/30">
            <span className="font-medium text-green-400">What is flanking?</span> Approaching from outside the enemy's field of view (90°+ from their facing direction). This provides tactical surprise and reduces detection chance.
          </div>
        </Card>
      )}

      {/* Route Improvement Suggestions - Always show with dynamic tips */}
      <Card className="p-4 bg-gradient-to-br from-amber-500/5 to-orange-500/5 border-amber-500/20">
        <div className="flex items-center gap-2 mb-3">
          <Route className="w-4 h-4 text-amber-400" />
          <span className="font-semibold text-amber-400">Tactical Recommendations</span>
          <span className="text-[9px] px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-400 border border-blue-500/30">
            Dynamic
          </span>
        </div>
        <div className="space-y-2 text-sm">
          {/* Critical exposure warning */}
          {weak_spots && weak_spots.some(ws => ws.severity === 'critical' || ws.severity === 'high') && (
            <div className="flex items-start gap-2 p-2 rounded bg-red-500/10 border border-red-500/20">
              <AlertTriangle className="w-4 h-4 text-red-400 mt-0.5 shrink-0" />
              <div>
                <span className="font-medium text-red-400">High-risk segments detected</span>
                <p className="text-xs text-muted-foreground">Consider rerouting around critical exposure points using available cover.</p>
              </div>
            </div>
          )}

          {/* Cover usage tip */}
          {cover_breakdown && cover_breakdown.exposed_count > 0 && (
            <div className="flex items-start gap-2 p-2 rounded bg-secondary/50">
              <ArrowRight className="w-4 h-4 text-amber-400 mt-0.5 shrink-0" />
              <div>
                <span className="font-medium">Maximize cover usage</span>
                <p className="text-xs text-muted-foreground">
                  {cover_breakdown.exposed_count > cover_breakdown.covered_count
                    ? 'Route has more exposed than covered segments. Stay closer to buildings/terrain.'
                    : 'Good cover usage. Maintain proximity to cover features when possible.'}
                </p>
              </div>
            </div>
          )}

          {/* Flanking tip */}
          <div className="flex items-start gap-2 p-2 rounded bg-secondary/50">
            <ArrowRight className="w-4 h-4 text-amber-400 mt-0.5 shrink-0" />
            <div>
              <span className="font-medium">{effectiveFlanking ? 'Maintain flanking advantage' : 'Consider flanking maneuver'}</span>
              <p className="text-xs text-muted-foreground">
                {effectiveFlanking
                  ? 'Keep approach angle >90° from enemy facing to maintain surprise.'
                  : 'Approach from enemy blind spot (90°+ from facing) for tactical advantage.'}
              </p>
            </div>
          </div>

          {/* Movement timing */}
          <div className="flex items-start gap-2 p-2 rounded bg-secondary/50">
            <ArrowRight className="w-4 h-4 text-amber-400 mt-0.5 shrink-0" />
            <div>
              <span className="font-medium">Movement discipline</span>
              <p className="text-xs text-muted-foreground">
                Move during low visibility periods. Cross open areas quickly using bounding overwatch.
              </p>
            </div>
          </div>

          {/* Coordination tip */}
          <div className="flex items-start gap-2 p-2 rounded bg-secondary/50">
            <ArrowRight className="w-4 h-4 text-amber-400 mt-0.5 shrink-0" />
            <div>
              <span className="font-medium">Team coordination</span>
              <p className="text-xs text-muted-foreground">
                Maintain visual contact between team members. Use hand signals in danger zones.
              </p>
            </div>
          </div>
        </div>
      </Card>

      {/* Annotated Map Image */}
      {annotated_image && (
        <Card className="p-0 overflow-hidden">
          <div className="flex items-center gap-2 text-sm font-medium p-2 text-muted-foreground border-b">
            <ImageIcon className="w-4 h-4" />
            <span>Annotated Tactical Map</span>
          </div>
          <div className="bg-black/20">
            <img
              src={`data:image/png;base64,${annotated_image}`}
              alt="Annotated tactical map"
              className="w-full h-auto"
              style={{ maxHeight: '50vh', objectFit: 'contain', width: '100%' }}
            />
          </div>
        </Card>
      )}

      {/* Overall Assessment */}
      <Card className="p-4 bg-purple-500/10 border-purple-500/30">
        <div className="flex items-center gap-2 mb-2">
          <Shield className="w-4 h-4 text-purple-500" />
          <span className="font-semibold text-purple-400">Overall Assessment</span>
          {overall_assessment && overall_assessment.length > 20 && !overall_assessment.includes('Analysis pending') ? (
            <span className="text-[9px] px-1.5 py-0.5 rounded bg-green-500/20 text-green-400 border border-green-500/30 flex items-center gap-1">
              <Zap className="w-2.5 h-2.5" />AI
            </span>
          ) : (
            <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400 border border-amber-500/30">
              Fallback
            </span>
          )}
        </div>
        <p className="text-sm">{overall_assessment}</p>
        {terrain_assessment && (
          <p className="text-xs text-muted-foreground mt-2 pt-2 border-t border-purple-500/20">
            {terrain_assessment}
          </p>
        )}
      </Card>

      {/* Movement Timeline - Based on AI segment analysis */}
      <Card className="p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Timer className="w-4 h-4 text-cyan-400" />
            <span className="font-semibold">Movement Timeline</span>
            {segment_cover_analysis && segment_cover_analysis.length > 0 && segment_cover_analysis.some(s => s.explanation && s.explanation.length > 10) ? (
              <span className="text-[9px] px-1.5 py-0.5 rounded bg-green-500/20 text-green-400 border border-green-500/30 flex items-center gap-1">
                <Zap className="w-2.5 h-2.5" />AI
              </span>
            ) : (
              <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400 border border-amber-500/30">
                Estimate
              </span>
            )}
          </div>
          <div className="text-xs text-muted-foreground">
            Total: <span className="font-medium text-cyan-400">{estimated_time_minutes.toFixed(0)} min</span> |
            <span className="ml-1">{(route_distance_m / 1000).toFixed(2)} km</span>
          </div>
        </div>

        {/* Dynamic progress bar based on segment analysis */}
        {segment_cover_analysis && segment_cover_analysis.length > 0 ? (
          <>
            <div className="h-2 rounded-full bg-secondary overflow-hidden mb-4 flex">
              {segment_cover_analysis.map((seg, idx) => (
                <div
                  key={idx}
                  className={cn(
                    'h-full',
                    seg.cover_status === 'exposed' ? 'bg-red-500' :
                    seg.cover_status === 'partial' ? 'bg-amber-500' :
                    seg.cover_status === 'covered' ? 'bg-green-500' : 'bg-blue-500'
                  )}
                  style={{ width: `${100 / segment_cover_analysis.length}%` }}
                  title={`Segment ${idx + 1}: ${seg.cover_status}`}
                />
              ))}
            </div>

            <div className="relative">
              <div className="absolute left-3 top-2 bottom-2 w-0.5 bg-gradient-to-b from-green-500 via-blue-500 to-red-500" />

              <ScrollArea className="h-64">
              <div className="space-y-3 pl-8 pr-3">
                {/* Start */}
                <div className="relative">
                  <div className="absolute -left-[22px] w-5 h-5 rounded-full bg-green-500 border-2 border-background flex items-center justify-center">
                    <Footprints className="w-2.5 h-2.5 text-white" />
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-green-400 text-sm">Start</span>
                    <span className="text-[10px] text-muted-foreground">0:00</span>
                  </div>
                </div>

                {/* AI-analyzed segments */}
                {segment_cover_analysis.map((seg, idx) => {
                  const timeAtSeg = Math.round(estimated_time_minutes * ((idx + 1) / (segment_cover_analysis.length + 1)));
                  const statusColors = {
                    exposed: { bg: 'bg-red-500', text: 'text-red-400', label: 'EXPOSED' },
                    partial: { bg: 'bg-amber-500', text: 'text-amber-400', label: 'PARTIAL' },
                    covered: { bg: 'bg-green-500', text: 'text-green-400', label: 'COVERED' },
                    clear: { bg: 'bg-blue-500', text: 'text-blue-400', label: 'CLEAR' },
                  };
                  const status = statusColors[seg.cover_status] || statusColors.clear;

                  return (
                    <div key={idx} className="relative">
                      <div className={cn('absolute -left-[22px] w-5 h-5 rounded-full border-2 border-background flex items-center justify-center', status.bg)}>
                        {seg.cover_status === 'exposed' ? <AlertTriangle className="w-2.5 h-2.5 text-white" /> :
                         seg.cover_status === 'covered' ? <Shield className="w-2.5 h-2.5 text-white" /> :
                         <CircleDot className="w-2.5 h-2.5 text-white" />}
                      </div>
                      <div className="flex items-center justify-between">
                        <div>
                          <span className={cn('font-medium text-sm', status.text)}>Segment {seg.segment_index + 1}</span>
                          <span className="text-[10px] text-muted-foreground ml-2">{timeAtSeg}:00</span>
                        </div>
                        <span className={cn('text-[9px] px-1.5 py-0.5 rounded', `${status.bg}/20`, status.text)}>{status.label}</span>
                      </div>
                      <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">
                        {seg.explanation || (seg.cover_type ? `Using ${seg.cover_type} for cover` : 'Move tactically')}
                      </p>
                    </div>
                  );
                })}

                {/* End */}
                <div className="relative">
                  <div className="absolute -left-[22px] w-5 h-5 rounded-full bg-red-500 border-2 border-background flex items-center justify-center">
                    <Crosshair className="w-2.5 h-2.5 text-white" />
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-red-400 text-sm">Objective</span>
                    <span className="text-[10px] text-muted-foreground">{estimated_time_minutes.toFixed(0)}:00</span>
                  </div>
                </div>
              </div>
              </ScrollArea>
            </div>
          </>
        ) : (
          /* Fallback when no segment analysis available */
          <div className="text-center py-4 text-muted-foreground">
            <Timer className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">Detailed timeline requires AI segment analysis</p>
            <p className="text-xs mt-1">Est. movement time: {estimated_time_minutes.toFixed(0)} minutes</p>
          </div>
        )}
      </Card>

      {/* Risk Hotspots */}
      {weak_spots && weak_spots.length > 0 && (
        <Card className="p-4 border-red-500/30">
          <div className="flex items-center gap-2 mb-3">
            <Siren className="w-4 h-4 text-red-400" />
            <span className="font-semibold text-red-400">Risk Hotspots</span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-red-500/20 text-red-400">{weak_spots.length} identified</span>
            {weak_spots.some(ws => ws.description && ws.description.length > 10) ? (
              <span className="text-[9px] px-1.5 py-0.5 rounded bg-green-500/20 text-green-400 border border-green-500/30 flex items-center gap-1">
                <Zap className="w-2.5 h-2.5" />AI
              </span>
            ) : (
              <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400 border border-amber-500/30">
                Geometric
              </span>
            )}
          </div>
          <div className="grid gap-2">
            {weak_spots.slice(0, 3).map((spot, idx) => (
              <div key={idx} className={cn(
                'p-2 rounded-lg border flex items-start gap-3',
                spot.severity === 'critical' ? 'bg-red-500/10 border-red-500/30' :
                spot.severity === 'high' ? 'bg-orange-500/10 border-orange-500/30' :
                'bg-yellow-500/10 border-yellow-500/30'
              )}>
                <div className={cn(
                  'w-8 h-8 rounded-full flex items-center justify-center shrink-0',
                  spot.severity === 'critical' ? 'bg-red-500' :
                  spot.severity === 'high' ? 'bg-orange-500' : 'bg-yellow-500'
                )}>
                  <AlertTriangle className="w-4 h-4 text-white" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-sm">{spot.location}</span>
                    <span className={cn(
                      'text-[10px] uppercase font-bold px-1.5 py-0.5 rounded',
                      spot.severity === 'critical' ? 'bg-red-500 text-white' :
                      spot.severity === 'high' ? 'bg-orange-500 text-white' : 'bg-yellow-500 text-black'
                    )}>{spot.severity}</span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-0.5">{spot.description}</p>
                  {spot.recommendation && (
                    <p className="text-xs text-green-400 mt-1 flex items-center gap-1">
                      <ArrowRight className="w-3 h-3" />{spot.recommendation}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Equipment & Loadout Recommendations */}
      <Card className="p-4">
        <div className="flex items-center gap-2 mb-3">
          <Package className="w-4 h-4 text-orange-400" />
          <span className="font-semibold">Recommended Loadout</span>
          <span className="text-[9px] px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-400 border border-blue-500/30">
            Suggested
          </span>
        </div>
        <div className="grid grid-cols-2 gap-2">
          {/* Dynamic recommendations based on analysis */}
          {cover_breakdown && cover_breakdown.exposed_count > 0 && (
            <div className="p-2 rounded bg-secondary/50 flex items-center gap-2">
              <div className="w-8 h-8 rounded bg-purple-500/20 flex items-center justify-center">
                <Zap className="w-4 h-4 text-purple-400" />
              </div>
              <div>
                <div className="text-xs font-medium">Smoke Grenades</div>
                <div className="text-[10px] text-muted-foreground">Cover exposed segments</div>
              </div>
            </div>
          )}
          {effectiveFlanking && (
            <div className="p-2 rounded bg-secondary/50 flex items-center gap-2">
              <div className="w-8 h-8 rounded bg-green-500/20 flex items-center justify-center">
                <Crosshair className="w-4 h-4 text-green-400" />
              </div>
              <div>
                <div className="text-xs font-medium">Suppressor</div>
                <div className="text-[10px] text-muted-foreground">Maintain flanking stealth</div>
              </div>
            </div>
          )}
          <div className="p-2 rounded bg-secondary/50 flex items-center gap-2">
            <div className="w-8 h-8 rounded bg-blue-500/20 flex items-center justify-center">
              <Radio className="w-4 h-4 text-blue-400" />
            </div>
            <div>
              <div className="text-xs font-medium">Comms Radio</div>
              <div className="text-[10px] text-muted-foreground">Team coordination</div>
            </div>
          </div>
          <div className="p-2 rounded bg-secondary/50 flex items-center gap-2">
            <div className="w-8 h-8 rounded bg-amber-500/20 flex items-center justify-center">
              <Eye className="w-4 h-4 text-amber-400" />
            </div>
            <div>
              <div className="text-xs font-medium">Binoculars</div>
              <div className="text-[10px] text-muted-foreground">Scout before movement</div>
            </div>
          </div>
        </div>
      </Card>

      {/* Rally Points & Evacuation */}
      <Card className="p-4 bg-blue-500/5 border-blue-500/20">
        <div className="flex items-center gap-2 mb-3">
          <Flag className="w-4 h-4 text-blue-400" />
          <span className="font-semibold">Rally & Evacuation Points</span>
          <span className="text-[9px] px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-400 border border-blue-500/30">
            Standard
          </span>
        </div>
        <div className="space-y-2">
          <div className="flex items-center gap-3 p-2 rounded bg-secondary/50">
            <div className="w-3 h-3 rounded-full bg-green-500" />
            <div className="flex-1">
              <div className="text-xs font-medium">Primary Rally Point</div>
              <div className="text-[10px] text-muted-foreground">Return to start position if compromised</div>
            </div>
            <Navigation className="w-4 h-4 text-green-400" />
          </div>
          <div className="flex items-center gap-3 p-2 rounded bg-secondary/50">
            <div className="w-3 h-3 rounded-full bg-amber-500" />
            <div className="flex-1">
              <div className="text-xs font-medium">Emergency Extraction</div>
              <div className="text-[10px] text-muted-foreground">
                {cover_breakdown && cover_breakdown.cover_types_used.includes('building')
                  ? 'Use nearby building for cover during extraction'
                  : 'Move perpendicular to enemy lines of sight'}
              </div>
            </div>
            <Navigation className="w-4 h-4 text-amber-400 rotate-90" />
          </div>
          <div className="flex items-center gap-3 p-2 rounded bg-secondary/50">
            <div className="w-3 h-3 rounded-full bg-red-500" />
            <div className="flex-1">
              <div className="text-xs font-medium">Abort Protocol</div>
              <div className="text-[10px] text-muted-foreground">Signal team, smoke out, retreat to rally</div>
            </div>
            <Siren className="w-4 h-4 text-red-400" />
          </div>
        </div>
      </Card>

      {/* Strong Points */}
      {strong_points && strong_points.length > 0 && (
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-3">
            <CheckCircle className="w-4 h-4 text-green-500" />
            <span className="font-semibold">Strong Points ({strong_points.length})</span>
            {strong_points.some(sp => sp.description && sp.description.length > 10) ? (
              <span className="text-[9px] px-1.5 py-0.5 rounded bg-green-500/20 text-green-400 border border-green-500/30 flex items-center gap-1">
                <Zap className="w-2.5 h-2.5" />AI
              </span>
            ) : (
              <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400 border border-amber-500/30">
                Fallback
              </span>
            )}
          </div>
          <div className="space-y-2">
            {strong_points.map((point, idx) => (
              <div key={idx} className="p-2 rounded bg-green-500/10 border border-green-500/20">
                <div className="font-medium text-sm text-green-400">{point.location}</div>
                <p className="text-xs text-muted-foreground mt-1">{point.description}</p>
                {point.benefit && (
                  <p className="text-xs text-green-400/80 mt-1">{point.benefit}</p>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Weak Spots */}
      {weak_spots && weak_spots.length > 0 && (
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-3">
            <XCircle className="w-4 h-4 text-red-500" />
            <span className="font-semibold">Weak Spots ({weak_spots.length})</span>
            {weak_spots.some(ws => ws.description && ws.description.length > 10) ? (
              <span className="text-[9px] px-1.5 py-0.5 rounded bg-green-500/20 text-green-400 border border-green-500/30 flex items-center gap-1">
                <Zap className="w-2.5 h-2.5" />AI
              </span>
            ) : (
              <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400 border border-amber-500/30">
                Fallback
              </span>
            )}
          </div>
          <div className="space-y-2">
            {weak_spots.map((spot, idx) => (
              <div
                key={idx}
                className={cn(
                  'p-3 rounded border',
                  SEVERITY_COLORS[spot.severity]
                )}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-medium text-sm">{spot.location}</span>
                  <span className="text-xs uppercase font-semibold">{spot.severity}</span>
                </div>
                <p className="text-xs text-muted-foreground">{spot.description}</p>
                {spot.recommendation && (
                  <div className="mt-2 pt-2 border-t border-current/20 text-xs">
                    <span className="font-medium">Recommendation: </span>
                    {spot.recommendation}
                  </div>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Recommendations */}
      {recommendations && recommendations.length > 0 && (
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-3">
            <Target className="w-4 h-4 text-green-500" />
            <span className="font-semibold">Recommendations</span>
            {recommendations.some(rec => rec.length > 20) ? (
              <span className="text-[9px] px-1.5 py-0.5 rounded bg-green-500/20 text-green-400 border border-green-500/30 flex items-center gap-1">
                <Zap className="w-2.5 h-2.5" />AI
              </span>
            ) : (
              <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400 border border-amber-500/30">
                Generic
              </span>
            )}
          </div>
          <ul className="space-y-2">
            {recommendations.map((rec, idx) => (
              <li key={idx} className="text-sm flex items-start gap-2">
                <span className="text-green-500 mt-0.5">•</span>
                <span>{rec}</span>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {/* Bottom spacing to ensure last card is fully visible */}
      <div className="h-4" />
    </div>
  );
};

// Separate component for report content (Route mode)
const ReportContent = ({ report }: { report: TacticalReportEntry['report'] }) => {
  return (
    <div className="space-y-4 pr-4">
      {/* Mission Summary */}
      {report.mission_summary && (
        <Card className="p-4 bg-purple-500/10 border-purple-500/30">
          <p className="text-purple-400 font-medium">{report.mission_summary}</p>
        </Card>
      )}

      {/* Recommended Approach */}
      {report.recommended_approach && (
        <Card className="p-4">
          <div className="flex items-center gap-2 text-green-500 font-semibold mb-2">
            <Target className="w-4 h-4" />
            <span>Recommended Approach</span>
          </div>
          <div className="space-y-2 pl-6">
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground">Route:</span>
              <span className="font-semibold text-green-400">
                {report.recommended_approach.route?.toUpperCase()}
              </span>
            </div>
            <p className="text-sm text-muted-foreground">
              {report.recommended_approach.reasoning}
            </p>
          </div>
        </Card>
      )}

      {/* Timing */}
      {report.timing_suggestions && (
        <Card className="p-4">
          <div className="flex items-center gap-2 text-blue-400 font-semibold mb-2">
            <Clock className="w-4 h-4" />
            <span>Optimal Timing</span>
          </div>
          <div className="space-y-2 pl-6">
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground">Time:</span>
              <span className="font-semibold">{report.timing_suggestions.optimal_time}</span>
            </div>
            <p className="text-sm text-muted-foreground">
              {report.timing_suggestions.reasoning}
            </p>
          </div>
        </Card>
      )}

      {/* Equipment */}
      {report.equipment_recommendations && report.equipment_recommendations.length > 0 && (
        <Card className="p-4">
          <div className="flex items-center gap-2 text-orange-400 font-semibold mb-2">
            <Package className="w-4 h-4" />
            <span>Equipment Recommendations</span>
          </div>
          <ul className="space-y-2 pl-6">
            {report.equipment_recommendations.map((eq, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="text-orange-400">•</span>
                <div>
                  <span className="font-medium">{eq.item}</span>
                  {eq.reason && (
                    <span className="text-sm text-muted-foreground ml-2">
                      - {eq.reason}
                    </span>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {/* Enemy Analysis */}
      {report.enemy_analysis?.weakness && (
        <Card className="p-4">
          <div className="flex items-center gap-2 text-red-400 font-semibold mb-2">
            <Shield className="w-4 h-4" />
            <span>Enemy Weakness</span>
          </div>
          <p className="text-sm pl-6">{report.enemy_analysis.weakness}</p>
        </Card>
      )}

      {/* Risk Zones */}
      {report.risk_zones && report.risk_zones.length > 0 && (
        <Card className="p-4">
          <div className="flex items-center gap-2 text-yellow-500 font-semibold mb-2">
            <AlertTriangle className="w-4 h-4" />
            <span>Risk Zones</span>
          </div>
          <ul className="space-y-2 pl-6">
            {report.risk_zones.map((rz, i) => (
              <li key={i} className="text-sm">
                <div className="flex items-start gap-2">
                  <span className="text-yellow-500">•</span>
                  <div>
                    <span className="font-medium">{rz.location}</span>
                    {rz.mitigation && (
                      <p className="text-muted-foreground mt-0.5">
                        Mitigation: {rz.mitigation}
                      </p>
                    )}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
};
