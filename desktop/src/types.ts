export interface ReadyFile {
  filename: string;
  extension: string;
  category: string;
  subfolder: string;
  size_bytes: number;
  source_path: string;
  target_relative_path: string;
}

export interface SkippedFile {
  path: string;
  reason: string;
}

export interface ScanResponse {
  downloads_dir: string;
  total_ready: number;
  total_ready_bytes: number;
  already_organized_count: number;
  category_breakdown: Record<string, number>;
  ready_files: ReadyFile[];
  skipped_files: SkippedFile[];
}

export interface PlannedMove {
  source: string;
  destination: string;
  file_size: number;
  category: string;
  extension: string;
}

export interface PreviewResponse {
  downloads_dir: string;
  total_files: number;
  total_bytes: number;
  planned_moves: PlannedMove[];
}

export interface ExecutedMove {
  source: string;
  destination: string;
  file_size: number;
  category: string;
  operation_id: number;
}

export interface FailedMove {
  source: string;
  target_destination: string;
  error: string;
  category: string;
}

export interface OrganizeResponse {
  batch_id: string | null;
  total_files: number;
  successful_moves: number;
  failed_moves: number;
  is_dry_run: boolean;
  moved_items: ExecutedMove[];
  failed_items: FailedMove[];
}

export interface BatchItem {
  id: string;
  timestamp: string;
  total_files: number;
  successful_moves: number;
  failed_moves: number;
  status: string;
  notes: string | null;
}

export interface HistoryResponse {
  batches: BatchItem[];
}

export interface StatusResponse {
  version: string;
  downloads_dir: string;
  app_data_dir: string;
  recursive: boolean;
  rules_count: number;
  stats: {
    total_batches: number;
    active_organized_files: number;
    total_undone_files: number;
    total_failed_moves: number;
    category_breakdown: Record<string, number>;
  };
  scheduler: {
    is_registered: boolean;
    is_enabled: boolean;
    next_run_time: string | null;
    last_run_time: string | null;
  };
}

export interface RuleConfig {
  name: string;
  category: string;
  subfolder: string;
  extensions: string[];
}

export interface AppConfig {
  version: string;
  downloads_dir: string | null;
  recursive: boolean;
  min_file_size_bytes: number;
  max_file_size_bytes: number | null;
  conflict_strategy: string;
  ignored_extensions: string[];
  excluded_directories: string[];
  rules: RuleConfig[];
  default_fallback_folder: string;
}
