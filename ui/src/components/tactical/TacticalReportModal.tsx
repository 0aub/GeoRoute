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
} from 'lucide-react';
import { useMission, type TacticalReportEntry } from '@/hooks/useMission';
import { cn } from '@/lib/utils';

export const TacticalReportModal = () => {
  const {
    tacticalAnalysisReport,
    tacticalReportHistory,
    selectedReportId,
    reportModalOpen,
    selectReport,
    removeReportFromHistory,
    setReportModalOpen,
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

  const formatDate = (date: Date) => {
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(date));
  };

  const formatCoords = (coords: { lat: number; lon: number }) => {
    return `${coords.lat.toFixed(4)}, ${coords.lon.toFixed(4)}`;
  };

  return (
    <Dialog open={reportModalOpen} onOpenChange={setReportModalOpen}>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-purple-500" />
            Tactical Analysis Report
          </DialogTitle>
        </DialogHeader>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col overflow-hidden">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="current">Current Report</TabsTrigger>
            <TabsTrigger value="history">
              History ({tacticalReportHistory.length})
            </TabsTrigger>
          </TabsList>

          <TabsContent value="current" className="flex-1 overflow-hidden mt-4">
            <ScrollArea className="h-[55vh]">
              {report ? (
                <ReportContent report={report} />
              ) : (
                <div className="flex flex-col items-center justify-center h-48 text-muted-foreground">
                  <FileText className="w-12 h-12 mb-4 opacity-50" />
                  <p>No report available</p>
                  <p className="text-sm mt-2">
                    Enable Advanced Analytics and generate routes to see a report
                  </p>
                </div>
              )}
            </ScrollArea>
          </TabsContent>

          <TabsContent value="history" className="flex-1 overflow-hidden mt-4">
            <ScrollArea className="h-[55vh]">
              {tacticalReportHistory.length > 0 ? (
                <div className="space-y-3 pr-4">
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
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center h-48 text-muted-foreground">
                  <FileText className="w-12 h-12 mb-4 opacity-50" />
                  <p>No report history</p>
                  <p className="text-sm mt-2">
                    Reports are automatically saved when generated
                  </p>
                </div>
              )}
            </ScrollArea>
          </TabsContent>
        </Tabs>

        {selectedHistoryEntry && activeTab === 'current' && (
          <div className="mt-2 pt-2 border-t text-xs text-muted-foreground flex items-center justify-between">
            <span>
              Viewing report from {formatDate(selectedHistoryEntry.timestamp)}
            </span>
            <Button
              variant="link"
              size="sm"
              className="text-xs h-auto p-0"
              onClick={() => selectReport(null)}
            >
              View latest report
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};

// Separate component for report content
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
