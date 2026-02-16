import axios, { AxiosInstance } from 'axios'

// Type declaration for the electron API
declare global {
  interface Window {
    electronAPI: {
      getAppConfig: () => Promise<any>;
      onConfigUpdated: (callback: (config: any) => void) => () => void;
    };
  }
}

// Create a function to get the axios instance with proper configuration
export const getAxiosInstance = async (): Promise<AxiosInstance> => {
  try {
    const AppConstants = await window.electronAPI.getAppConfig();
    console.log('[DEBUG] AppConstants loaded:', AppConstants);
    
    if (!AppConstants) {
      throw new Error('AppConstants is undefined');
    }
    
    if (!AppConstants.BACKEND_BASE_URL) {
      throw new Error('BACKEND_BASE_URL is not defined in AppConstants');
    }
    
    console.log('[DEBUG] Backend base URL:', AppConstants.BACKEND_BASE_URL);

    return axios.create({
      baseURL: AppConstants.BACKEND_BASE_URL,
      timeout: 30000, // 30 second timeout
    });
  } catch (error) {
    console.error('Failed to load AppConstants:', error);
    // Fallback to default configuration
    return axios.create({
      baseURL: 'http://127.0.0.1:8000',
      timeout: 30000,
    });
  }
}

// Create a default instance that will be updated when AppConstants loads
export const axiosInstance: AxiosInstance = axios.create({
  baseURL: 'http://127.0.0.1:8000', // Default fallback
  timeout: 30000,
});

// Function to update the axios instance with proper config
export const updateAxiosInstance = async (): Promise<void> => {
  try {
    const AppConstants = await window.electronAPI.getAppConfig();
    console.log('[DEBUG] Updating axios instance with:', AppConstants.BACKEND_BASE_URL);
    axiosInstance.defaults.baseURL = AppConstants.BACKEND_BASE_URL;
  } catch (error) {
    console.error('Failed to update axios instance:', error);
  }
}

// Add request interceptor for debugging
axiosInstance.interceptors.request.use(
  (config) => {
    console.log('[DEBUG] API Request:', {
      url: config.url,
      method: config.method?.toUpperCase(),
      baseURL: config.baseURL,
      params: config.params,
      headers: config.headers,
    });
    return config;
  },
  (error) => {
    console.error('[DEBUG] API Request Error:', error);
    return Promise.reject(error);
  }
);

// Add response interceptor for debugging
axiosInstance.interceptors.response.use(
  (response) => {
    console.log('[DEBUG] API Response:', {
      url: response.config.url,
      status: response.status,
      statusText: response.statusText,
      data: response.data,
    });
    return response;
  },
  (error) => {
    console.error('[DEBUG] API Response Error:', {
      url: error.config?.url,
      method: error.config?.method?.toUpperCase(),
      status: error.response?.status,
      statusText: error.response?.statusText,
      data: error.response?.data,
      message: error.message,
      code: error.code,
      config: error.config,
    });
    
    // Provide more specific error information
    if (error.code === 'ECONNABORTED') {
      console.error('[DEBUG] Timeout Error: Request took too long');
    } else if (!error.response) {
      console.error('[DEBUG] Network Error: No response received');
      console.error('[DEBUG] This could be due to:');
      console.error('  - Backend server not running');
      console.error('  - Firewall blocking the request');
      console.error('  - Incorrect backend URL');
      console.error('  - Network connectivity issues');
    }
    
    return Promise.reject(error);
  }
);