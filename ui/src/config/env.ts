export const getApiUrl = (): string => {
  const apiUrl = import.meta.env.VITE_API_URL;

  // If not set or empty, use relative URL (works with nginx proxy)
  if (!apiUrl || apiUrl === '' || apiUrl === 'undefined') {
    return '';  // Relative URL - requests go to same origin
  }

  return apiUrl;
};

export const isConfigured = (): boolean => {
  // Always configured - either explicit URL or relative (nginx proxy)
  return true;
};
