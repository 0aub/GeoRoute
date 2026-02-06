import { useEffect, useState } from 'react';
import { MapPin, Satellite, Route, Shield, Target, CheckCircle2, Crosshair, AlertCircle, FileText } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ProgressUpdate } from '@/hooks/useApi';

interface LoadingStage {
  id: string;
  label: string;
  icon: React.ElementType;
}

// 3 main stages visible during route planning
const STAGES: LoadingStage[] = [
  { id: 'imagery', label: 'Acquiring Imagery', icon: Satellite },
  { id: 'routes', label: 'Planning Routes', icon: Route },
  { id: 'report', label: 'Generating Report', icon: FileText },
];

// Stages for tactical simulation (report generation)
const SIMULATION_STAGES: LoadingStage[] = [
  { id: 'imagery', label: 'Acquiring Imagery', icon: Satellite },
  { id: 'analysis', label: 'Analyzing Scenario', icon: Shield },
  { id: 'report', label: 'Generating Report', icon: FileText },
];

// Map backend stage names to stage index (consolidated)
const STAGE_MAP: Record<string, number> = {
  terrain: 0,      // Show as "Acquiring Imagery"
  imagery: 0,      // Show as "Acquiring Imagery"
  routes: 1,       // Show as "Planning Routes"
  classification: 1,  // Show as "Planning Routes"
  analysis: 1,     // Show as "Planning Routes"
  report: 2,       // Show as "Generating Report"
  complete: 2,     // Stay on last stage until done
  error: -1,
};

interface PlanningLoaderProps {
  progress: ProgressUpdate | null;
  advancedAnalytics?: boolean;
  isSimulation?: boolean;
  onDismiss?: () => void;
}

export const PlanningLoader = ({ progress, advancedAnalytics = false, isSimulation = false, onDismiss }: PlanningLoaderProps) => {
  // Pick stage set based on mode
  const baseStages = isSimulation ? SIMULATION_STAGES : STAGES;
  // Determine which stages to show based on advanced analytics
  const visibleStages = advancedAnalytics || isSimulation
    ? baseStages
    : baseStages.filter(s => s.id !== 'report');
  const [pulseRing, setPulseRing] = useState(0);

  // Pulsing ring animation
  useEffect(() => {
    const pulseInterval = setInterval(() => {
      setPulseRing((prev) => (prev + 1) % 4);
    }, 600);
    return () => clearInterval(pulseInterval);
  }, []);

  // Derive stage and progress from backend data
  const rawStageIndex = progress ? (STAGE_MAP[progress.stage] ?? 0) : 0;
  // Clamp stage index to visible stages (report stage may not be visible)
  const maxStageIndex = visibleStages.length - 1;
  const currentStageIndex = Math.min(rawStageIndex, maxStageIndex);
  const backendProgress = progress?.progress ?? 0;
  const message = progress?.message ?? 'Initializing...';

  // Use backend progress directly (0-100)
  const totalProgress = Math.min(backendProgress, 100);

  const currentStage = visibleStages[Math.min(Math.max(currentStageIndex, 0), maxStageIndex)];
  const Icon = currentStage?.icon ?? MapPin;
  const isError = progress?.stage === 'error';

  return (
    <div className="fixed inset-0 z-[9999] overflow-hidden">
      {/* Solid dark background layer for visibility */}
      <div className="absolute inset-0 bg-black/95" />
      {/* Dark gradient overlay */}
      <div className="absolute inset-0 bg-gradient-to-br from-[#0a1a18] via-[#0d2420] to-[#0a1a18]" />

      {/* Animated grid pattern */}
      <div className="absolute inset-0 opacity-10">
        <div
          className="absolute inset-0"
          style={{
            backgroundImage: `
              linear-gradient(rgba(0, 160, 90, 0.3) 1px, transparent 1px),
              linear-gradient(90deg, rgba(0, 160, 90, 0.3) 1px, transparent 1px)
            `,
            backgroundSize: '50px 50px',
            animation: 'moveGrid 20s linear infinite',
          }}
        />
      </div>

      {/* Scanning line effect */}
      <div
        className="absolute left-0 right-0 h-1 bg-gradient-to-r from-transparent via-[#00A05A] to-transparent opacity-60"
        style={{
          animation: 'scanLine 3s ease-in-out infinite',
        }}
      />

      {/* Main content */}
      <div className="relative z-10 h-full flex flex-col items-center justify-center px-4">
        {/* Logo at top */}
        <div className="mb-8">
          <img
            src="/logo.svg"
            alt="GeoRoute"
            className="h-16 w-auto opacity-80"
          />
        </div>

        {/* Central tactical display */}
        <div className="relative mb-12">
          {/* Outer pulsing rings */}
          {[0, 1, 2, 3].map((ring) => (
            <div
              key={ring}
              className={cn(
                'absolute rounded-full border-2 transition-all duration-500',
                isError
                  ? 'border-red-500/40'
                  : ring <= pulseRing ? 'border-[#00A05A]/40' : 'border-[#00A05A]/10'
              )}
              style={{
                width: `${180 + ring * 40}px`,
                height: `${180 + ring * 40}px`,
                top: `${-ring * 20}px`,
                left: `${-ring * 20}px`,
                transform: `scale(${ring <= pulseRing ? 1 : 0.95})`,
              }}
            />
          ))}

          {/* Center circle with rotating border */}
          <div className="relative w-[180px] h-[180px]">
            {/* Rotating outer ring */}
            <div
              className="absolute inset-0 rounded-full border-4 border-transparent"
              style={{
                borderTopColor: isError ? '#ef4444' : '#00A05A',
                borderRightColor: isError ? '#ef4444' : '#00A05A',
                animation: 'spin 2s linear infinite',
              }}
            />

            {/* Inner circle background */}
            <div className={cn(
              "absolute inset-3 rounded-full border flex items-center justify-center",
              isError ? "bg-red-900/30 border-red-500/30" : "bg-[#0d2420] border-[#00A05A]/30"
            )}>
              {/* Stage icon */}
              <div className="relative">
                {isError ? (
                  <AlertCircle className="w-16 h-16 text-red-500" strokeWidth={1.5} />
                ) : (
                  <>
                    <Icon className="w-16 h-16 text-[#00A05A]" strokeWidth={1.5} />
                    {/* Crosshair overlay */}
                    <Crosshair
                      className="absolute inset-0 w-16 h-16 text-[#00A05A]/30"
                      style={{ animation: 'pulse 2s ease-in-out infinite' }}
                    />
                  </>
                )}
              </div>
            </div>

            {/* Progress arc */}
            <svg className="absolute inset-0 w-full h-full -rotate-90">
              <circle
                cx="90"
                cy="90"
                r="85"
                fill="none"
                stroke={isError ? '#ef4444' : '#00A05A'}
                strokeWidth="4"
                strokeLinecap="round"
                strokeDasharray={`${totalProgress * 5.34} 534`}
                className="transition-all duration-300"
              />
            </svg>
          </div>
        </div>

        {/* Status text */}
        <div className="text-center mb-8 space-y-3">
          <h2 className={cn(
            "text-3xl font-bold tracking-wide",
            isError ? "text-red-500" : "text-white"
          )}>
            {isError ? 'PLANNING FAILED' : 'TACTICAL ANALYSIS IN PROGRESS'}
          </h2>
          <p className={cn(
            "text-xl font-medium",
            isError ? "text-red-400" : "text-[#00A05A] animate-pulse"
          )}>
            {message}
          </p>
          <p className="text-sm text-gray-400 font-mono">
            {Math.round(totalProgress)}% COMPLETE
          </p>
        </div>

        {/* Stage progress bar */}
        <div className="w-full max-w-lg mb-8">
          <div className="relative h-2 bg-[#1a3a35] rounded-full overflow-hidden">
            {/* Animated background pattern */}
            <div
              className="absolute inset-0 opacity-30"
              style={{
                backgroundImage: `repeating-linear-gradient(90deg, transparent, transparent 10px, ${isError ? '#ef4444' : '#00A05A'} 10px, ${isError ? '#ef4444' : '#00A05A'} 20px)`,
                backgroundSize: '20px 100%',
                animation: 'moveStripes 1s linear infinite',
              }}
            />
            {/* Progress fill */}
            <div
              className={cn(
                "absolute inset-y-0 left-0 transition-all duration-300",
                isError
                  ? "bg-gradient-to-r from-red-500 to-red-400"
                  : "bg-gradient-to-r from-[#00A05A] to-[#00c96e]"
              )}
              style={{ width: `${totalProgress}%` }}
            />
            {/* Glow effect at the end */}
            <div
              className="absolute top-0 bottom-0 w-8 bg-gradient-to-r from-transparent to-white/30"
              style={{ left: `calc(${totalProgress}% - 32px)` }}
            />
          </div>
        </div>

        {/* Stage indicators */}
        <div className="flex items-center gap-2 max-w-lg w-full justify-between">
          {visibleStages.map((stage, index) => {
            const StageIcon = stage.icon;
            const isComplete = index < currentStageIndex;
            const isCurrent = index === currentStageIndex;

            return (
              <div
                key={stage.id}
                className={cn(
                  'flex flex-col items-center gap-2 p-2 rounded-lg transition-all duration-300',
                  isComplete && 'text-[#00A05A]',
                  isCurrent && !isError && 'text-[#00A05A] scale-110',
                  isCurrent && isError && 'text-red-500 scale-110',
                  !isComplete && !isCurrent && 'text-gray-600'
                )}
              >
                <div
                  className={cn(
                    'w-10 h-10 rounded-full flex items-center justify-center border-2 transition-all',
                    isComplete && 'bg-[#00A05A]/20 border-[#00A05A]',
                    isCurrent && !isError && 'bg-[#00A05A]/10 border-[#00A05A] animate-pulse',
                    isCurrent && isError && 'bg-red-500/10 border-red-500',
                    !isComplete && !isCurrent && 'bg-transparent border-gray-700'
                  )}
                >
                  <StageIcon className="w-5 h-5" />
                </div>
              </div>
            );
          })}
        </div>

        {/* Error message with dismiss button */}
        {isError && (
          <div className="max-w-md w-full">
            <div className="backdrop-blur-sm rounded-lg p-5 border bg-red-900/30 border-red-500/30 space-y-4">
              <p className="text-sm text-gray-300 text-center">
                {message}
              </p>
              {onDismiss && (
                <button
                  onClick={onDismiss}
                  className="w-full py-2.5 px-4 rounded-md bg-red-600 hover:bg-red-500 text-white text-sm font-medium transition-colors"
                >
                  Dismiss
                </button>
              )}
            </div>
          </div>
        )}
      </div>

      {/* CSS Animations */}
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        @keyframes pulse {
          0%, 100% { opacity: 0.3; }
          50% { opacity: 0.6; }
        }
        @keyframes scanLine {
          0% { top: -5%; }
          100% { top: 105%; }
        }
        @keyframes moveGrid {
          0% { transform: translate(0, 0); }
          100% { transform: translate(50px, 50px); }
        }
        @keyframes moveStripes {
          0% { background-position: 0 0; }
          100% { background-position: 20px 0; }
        }
      `}</style>
    </div>
  );
};

