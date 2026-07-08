import { useCallback, useMemo, useState } from 'react';

type ApiResponse = {
  status: number;
  body: string;
};

type SessionSmokePhase =
  'idle' | 'creating' | 'running' | 'polling' | 'result-ready' | 'analysis-ready' | 'failed';

type BuffTimelineEntry = {
  Task: string;
  Start: number;
  Finish: number;
  Value: number | null;
};

type NormalResultPayload = {
  dmg_result?: unknown;
  buff_result?: Record<string, BuffTimelineEntry[]>;
};

type NormalModeResult = {
  mode: 'normal';
  result: NormalResultPayload;
};

type MatrixSignoffRow = {
  row_id?: string;
  status?: string;
  signoff_effect?: string;
  data_analysis_contract?: unknown;
};

type MatrixSignoffSummary = {
  schema?: string;
  signoff_status?: string;
  row_count?: number;
  rows?: MatrixSignoffRow[];
  data_analysis_contract?: unknown;
};

type SessionStatusPayload = {
  status: string;
  result: NormalModeResult[] | null;
};

type SessionReadPayload = {
  session_result?: NormalModeResult[] | null;
  matrix_signoff?: MatrixSignoffSummary | null;
  selected_matrix_row?: MatrixSignoffRow | null;
};

type SmokeContract = {
  session: {
    session_id: string;
    session_name: string;
  };
  run: {
    stop_tick: number;
    mode: 'normal';
    common_config: {
      session_id: string;
      char_config: { name: string }[];
      enemy_config: {
        index_id: number;
        adjustment_id: number;
      };
      apl_path: string;
    };
  };
};

export type SessionSmokeSnapshot = {
  phase: SessionSmokePhase;
  sessionId?: string;
  status?: string;
  resultMode?: string;
  dataAnalysisReady?: boolean;
  matrixSignoffReady?: boolean;
  matrixSignoffStatus?: string;
  error?: string;
};

type UseSessionSmokeOptions = {
  onDataAnalysisReady?: () => void;
};

const createSmokeSessionId = () => `electron-smoke-${Date.now().toString(36)}`;

const delay = (ms: number) =>
  new Promise<void>(resolve => {
    window.setTimeout(resolve, ms);
  });

const readJsonResponse = <T>(response: ApiResponse, operation: string): T => {
  let parsed: unknown = null;

  if (response.body) {
    try {
      parsed = JSON.parse(response.body);
    } catch {
      throw new Error(`${operation} returned invalid JSON`);
    }
  }

  if (response.status < 200 || response.status >= 300) {
    const detail =
      parsed && typeof parsed === 'object' && 'detail' in parsed
        ? String((parsed as { detail?: unknown }).detail)
        : response.body || `HTTP ${response.status}`;
    throw new Error(`${operation} failed: ${detail}`);
  }

  return parsed as T;
};

const buildSmokeContract = (sessionId: string): SmokeContract => ({
  session: {
    session_id: sessionId,
    session_name: 'Electron smoke contract',
  },
  run: {
    stop_tick: 1,
    mode: 'normal',
    common_config: {
      session_id: sessionId,
      char_config: [{ name: '仪玄' }, { name: '耀嘉音' }, { name: '扳机' }],
      enemy_config: {
        index_id: 11412,
        adjustment_id: 22412,
      },
      apl_path: 'zsim/data/APLData/仪玄-耀嘉音-扳机.toml',
    },
  },
});

const findNormalResult = (result: NormalModeResult[] | null | undefined) =>
  result?.find(entry => entry.mode === 'normal');

const hasDataAnalysisEntry = (result: NormalModeResult[] | null | undefined) => {
  const normalResult = findNormalResult(result);
  if (!normalResult) return false;

  return 'dmg_result' in normalResult.result || 'buff_result' in normalResult.result;
};

const findSelectedMatrixRow = (payload: SessionReadPayload) =>
  payload.selected_matrix_row ?? payload.matrix_signoff?.rows?.[0] ?? null;

const getMatrixSignoffStatus = (payload: SessionReadPayload) => {
  const selectedRow = findSelectedMatrixRow(payload);
  return (
    payload.matrix_signoff?.signoff_status ?? selectedRow?.signoff_effect ?? selectedRow?.status
  );
};

const hasMatrixSignoffEntry = (payload: SessionReadPayload) =>
  Boolean(payload.matrix_signoff || findSelectedMatrixRow(payload));

export const useSessionSmoke = ({ onDataAnalysisReady }: UseSessionSmokeOptions = {}) => {
  const [snapshot, setSnapshot] = useState<SessionSmokeSnapshot>({ phase: 'idle' });

  const runSmoke = useCallback(async () => {
    if (!window.apiClient) {
      setSnapshot({
        phase: 'failed',
        error: 'API client is not available',
      });
      return;
    }

    const sessionId = createSmokeSessionId();
    const contract = buildSmokeContract(sessionId);

    try {
      setSnapshot({ phase: 'creating', sessionId });
      readJsonResponse(
        await window.apiClient.post('/api/sessions/', contract.session),
        'Create session',
      );

      setSnapshot({ phase: 'running', sessionId, status: 'running' });
      readJsonResponse(
        await window.apiClient.post(`/api/sessions/${sessionId}/run`, contract.run, {
          query: { test_mode: true },
        }),
        'Run session',
      );

      setSnapshot({ phase: 'polling', sessionId, status: 'running' });
      let statusPayload: SessionStatusPayload | null = null;

      for (let attempt = 0; attempt < 20; attempt += 1) {
        statusPayload = readJsonResponse<SessionStatusPayload>(
          await window.apiClient.get(`/api/sessions/${sessionId}/status`),
          'Poll session status',
        );

        if (!['pending', 'running'].includes(statusPayload.status)) {
          break;
        }

        await delay(250);
      }

      if (!statusPayload) {
        throw new Error('Session status was not returned');
      }

      if (statusPayload.status !== 'completed') {
        throw new Error(`Session finished with status ${statusPayload.status}`);
      }

      setSnapshot({
        phase: 'result-ready',
        sessionId,
        status: statusPayload.status,
        resultMode: findNormalResult(statusPayload.result)?.mode,
      });

      const readPayload = readJsonResponse<SessionReadPayload>(
        await window.apiClient.get(`/api/sessions/${sessionId}`),
        'Read session result',
      );
      const result = readPayload.session_result ?? statusPayload.result;
      const dataAnalysisReady = hasDataAnalysisEntry(result);
      const matrixSignoffReady = hasMatrixSignoffEntry(readPayload);
      const matrixSignoffStatus = getMatrixSignoffStatus(readPayload);

      if (!dataAnalysisReady) {
        throw new Error('Normal result is missing the data-analysis payload');
      }

      setSnapshot({
        phase: 'analysis-ready',
        sessionId,
        status: statusPayload.status,
        resultMode: findNormalResult(result)?.mode,
        dataAnalysisReady,
        matrixSignoffReady,
        matrixSignoffStatus,
      });
      onDataAnalysisReady?.();
    } catch (error) {
      setSnapshot({
        phase: 'failed',
        sessionId,
        error: error instanceof Error ? error.message : String(error),
      });
    }
  }, [onDataAnalysisReady]);

  const isRunning = useMemo(
    () => ['creating', 'running', 'polling', 'result-ready'].includes(snapshot.phase),
    [snapshot.phase],
  );

  return {
    snapshot,
    runSmoke,
    isRunning,
  };
};
