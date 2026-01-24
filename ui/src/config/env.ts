export const getApiUrl = (): string | null => {
  const apiUrl = import.meta.env.VITE_API_URL;
  
  if (!apiUrl || apiUrl === '' || apiUrl === 'undefined') {
    return null;
  }
  
  return apiUrl;
};

export const isConfigured = (): boolean => {
  return getApiUrl() !== null;
};
