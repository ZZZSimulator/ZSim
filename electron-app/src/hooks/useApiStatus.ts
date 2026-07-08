import { useState, useEffect } from 'react';

interface UseApiStatusReturn {
  apiStatus: string;
  apiResponse: unknown;
  testApi: () => Promise<void>;
}

export const useApiStatus = (): UseApiStatusReturn => {
  const [apiStatus, setApiStatus] = useState<string>('初始化中...');
  const [apiResponse, setApiResponse] = useState<unknown>(null);

  const testApi = async () => {
    if (!window.apiClient) {
      setApiStatus('API 客户端未加载');
      return;
    }

    try {
      const response = await window.apiClient.get('/health');
      setApiStatus(`API 连接成功 (${response.status})`);
      setApiResponse(JSON.parse(response.body));
    } catch (error) {
      setApiStatus(`API 连接失败: ${error instanceof Error ? error.message : String(error)}`);
      console.error('API test failed:', error);
    }
  };

  useEffect(() => {
    const checkApiClient = async () => {
      console.log('[useApiStatus] Checking window.apiClient...');

      const maxAttempts = 50;
      let attempts = 0;

      const checkInterval = setInterval(() => {
        attempts++;
        console.log(
          `[useApiStatus] Attempt ${attempts}: window.apiClient =`,
          typeof window.apiClient,
        );

        if (typeof window !== 'undefined' && window.apiClient) {
          clearInterval(checkInterval);
          console.log('[useApiStatus] window.apiClient is available:', window.apiClient);
          setApiStatus('API 客户端已就绪');
        } else if (attempts >= maxAttempts) {
          clearInterval(checkInterval);
          console.error('[useApiStatus] window.apiClient not available after maximum attempts');
          setApiStatus('API 客户端加载超时');
        } else {
          console.log('[useApiStatus] window.apiClient not available yet, waiting...');
        }
      }, 200);
    };

    checkApiClient();
  }, []);

  useEffect(() => {
    setTimeout(testApi, 1000);
  }, []);

  return {
    apiStatus,
    apiResponse,
    testApi,
  };
};
