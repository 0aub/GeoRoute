import { AlertTriangle, Settings } from 'lucide-react';

export const ConfigError = () => {
  return (
    <div className="h-screen w-screen flex items-center justify-center bg-background-deep">
      <div className="tactical-panel p-8 max-w-lg text-center space-y-6">
        <div className="flex justify-center">
          <div className="p-4 rounded-full bg-danger/20 border border-danger/50">
            <AlertTriangle className="w-12 h-12 text-danger" />
          </div>
        </div>
        
        <div className="space-y-2">
          <h1 className="text-2xl font-bold text-foreground">Configuration Error</h1>
          <p className="text-foreground-muted">
            The application cannot start due to missing configuration.
          </p>
        </div>
        
        <div className="bg-background-deep rounded-md p-4 border border-danger/30">
          <div className="flex items-center gap-2 text-danger font-mono text-sm">
            <Settings className="w-4 h-4" />
            <span>VITE_API_URL environment variable is required</span>
          </div>
        </div>
        
        <div className="text-left space-y-2">
          <p className="text-sm text-foreground-muted font-medium">To fix this issue:</p>
          <ol className="text-sm text-foreground-muted space-y-1 list-decimal list-inside">
            <li>Create a <code className="font-mono bg-muted px-1 rounded">.env</code> file in the project root</li>
            <li>Add: <code className="font-mono bg-muted px-1 rounded">VITE_API_URL=http://localhost:8000</code></li>
            <li>Restart the development server</li>
          </ol>
        </div>
      </div>
    </div>
  );
};
