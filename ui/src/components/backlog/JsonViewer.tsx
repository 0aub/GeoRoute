interface JsonViewerProps {
  data: any;
  maxHeight?: string;
}

export const JsonViewer = ({ data, maxHeight = '400px' }: JsonViewerProps) => {
  return (
    <pre
      className="bg-secondary/50 p-3 rounded text-xs overflow-auto font-mono"
      style={{ maxHeight }}
    >
      <code>{JSON.stringify(data, null, 2)}</code>
    </pre>
  );
};
