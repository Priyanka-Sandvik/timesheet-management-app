/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_PROFILE_SERVICE_BASE_URL: string;
  readonly VITE_TASK_SERVICE_BASE_URL: string;
  readonly VITE_TIMELOG_SERVICE_BASE_URL: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
