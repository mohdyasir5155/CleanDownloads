import {
  ScanResponse,
  PreviewResponse,
  OrganizeResponse,
  HistoryResponse,
  StatusResponse,
  AppConfig,
} from './types';

// Check if running inside Tauri window
export const isTauri = (): boolean => {
  return typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window;
};

// Generic executor for cleandownloads CLI
async function execCleanDownloads<T>(args: string[]): Promise<T> {
  if (isTauri()) {
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      const stdout = await invoke<string>('run_cleandownloads_cmd', { args });
      return JSON.parse(stdout) as T;
    } catch (err) {
      console.error('Tauri IPC failed:', err);
      throw err;
    }
  }

  // Web Browser / Dev Simulation Fallback
  return mockHandler<T>(args);
}

// ─── Notification helpers (Tauri-native) ────────────────────────────

async function scanWithNotification(): Promise<ScanResponse> {
  if (isTauri()) {
    const { invoke } = await import('@tauri-apps/api/core');
    const stdout = await invoke<string>('scan_and_notify', {});
    return JSON.parse(stdout) as ScanResponse;
  }
  return mockHandler<ScanResponse>(['scan']);
}

async function organizeWithNotification(dryRun: boolean): Promise<OrganizeResponse> {
  if (isTauri()) {
    const { invoke } = await import('@tauri-apps/api/core');
    const stdout = await invoke<string>('organize_and_notify', { dryRun });
    return JSON.parse(stdout) as OrganizeResponse;
  }
  return mockHandler<OrganizeResponse>(dryRun ? ['organize', '--dry-run'] : ['organize']);
}

async function undoWithNotification(batchId?: string): Promise<{ success: boolean; message?: string }> {
  if (isTauri()) {
    const { invoke } = await import('@tauri-apps/api/core');
    const stdout = await invoke<string>('undo_and_notify', {
      batchId: batchId ?? null,
    });
    return JSON.parse(stdout);
  }
  return mockHandler<{ success: boolean; message?: string }>(
    batchId ? ['undo', '--batch-id', batchId] : ['undo']
  );
}

// ─── Close-to-tray settings ────────────────────────────────────────

async function setCloseToTray(enabled: boolean): Promise<void> {
  if (isTauri()) {
    const { invoke } = await import('@tauri-apps/api/core');
    await invoke('set_close_to_tray', { enabled });
  }
}

async function getCloseToTray(): Promise<boolean> {
  if (isTauri()) {
    const { invoke } = await import('@tauri-apps/api/core');
    return await invoke<boolean>('get_close_to_tray');
  }
  return true; // default in dev
}

// ─── Send notification from frontend ───────────────────────────────

async function notify(title: string, body: string): Promise<void> {
  if (isTauri()) {
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      await invoke('send_notification', { title, body });
    } catch (err) {
      console.warn('Notification failed:', err);
    }
  }
}

// ─── Public API ────────────────────────────────────────────────────

export const api = {
  // Standard CLI commands (no notifications)
  scan: () => execCleanDownloads<ScanResponse>(['scan', '--json']),
  preview: () => execCleanDownloads<PreviewResponse>(['preview', '--json']),
  organize: (dryRun = false) =>
    execCleanDownloads<OrganizeResponse>(
      dryRun ? ['organize', '--dry-run', '--json'] : ['organize', '--json']
    ),
  undo: (batchId?: string) =>
    execCleanDownloads<{ success: boolean; message?: string }>(
      batchId ? ['undo', '--batch-id', batchId, '--json'] : ['undo', '--json']
    ),
  history: (limit = 15) =>
    execCleanDownloads<HistoryResponse>(['history', '--limit', limit.toString(), '--json']),
  status: () => execCleanDownloads<StatusResponse>(['status', '--json']),
  config: () => execCleanDownloads<AppConfig>(['config', '--json']),

  // Commands with native Windows notifications
  scanAndNotify: () => scanWithNotification(),
  organizeAndNotify: (dryRun = false) => organizeWithNotification(dryRun),
  undoAndNotify: (batchId?: string) => undoWithNotification(batchId),

  // Tray / system settings
  setCloseToTray,
  getCloseToTray,

  // Direct notification
  notify,

  // Open Downloads folder
  openDownloadsFolder: async () => {
    if (isTauri()) {
      const { invoke } = await import('@tauri-apps/api/core');
      await invoke('open_downloads_folder');
    } else {
      window.open('file:///C:/Users/User/Downloads', '_blank');
    }
  },
};

// ─── Dev fallback for responsive browser preview ───────────────────

function mockHandler<T>(args: string[]): Promise<T> {
  const cmd = args[0];

  if (cmd === 'scan') {
    return Promise.resolve({
      downloads_dir: 'C:\\Users\\User\\Downloads',
      total_ready: 6,
      total_ready_bytes: 48920112,
      already_organized_count: 142,
      category_breakdown: {
        Documents: 2,
        Images: 2,
        Archives: 1,
        Software: 1,
      },
      ready_files: [
        {
          filename: 'Q3_Financial_Report.pdf',
          extension: 'pdf',
          category: 'Documents',
          subfolder: 'Documents/PDF',
          size_bytes: 3450000,
          source_path: 'C:\\Users\\User\\Downloads\\Q3_Financial_Report.pdf',
          target_relative_path: 'Documents/PDF/Q3_Financial_Report.pdf',
        },
        {
          filename: 'Meeting_Notes.docx',
          extension: 'docx',
          category: 'Documents',
          subfolder: 'Documents/Word',
          size_bytes: 524000,
          source_path: 'C:\\Users\\User\\Downloads\\Meeting_Notes.docx',
          target_relative_path: 'Documents/Word/Meeting_Notes.docx',
        },
        {
          filename: 'app_wireframe.png',
          extension: 'png',
          category: 'Images',
          subfolder: 'Images/PNG',
          size_bytes: 4120000,
          source_path: 'C:\\Users\\User\\Downloads\\app_wireframe.png',
          target_relative_path: 'Images/PNG/app_wireframe.png',
        },
        {
          filename: 'hero_wallpaper.jpg',
          extension: 'jpg',
          category: 'Images',
          subfolder: 'Images',
          size_bytes: 8900000,
          source_path: 'C:\\Users\\User\\Downloads\\hero_wallpaper.jpg',
          target_relative_path: 'Images/hero_wallpaper.jpg',
        },
        {
          filename: 'database_backup_2026.zip',
          extension: 'zip',
          category: 'Archives',
          subfolder: 'Archives/ZIP',
          size_bytes: 18200000,
          source_path: 'C:\\Users\\User\\Downloads\\database_backup_2026.zip',
          target_relative_path: 'Archives/ZIP/database_backup_2026.zip',
        },
        {
          filename: 'DockerDesktopInstaller.exe',
          extension: 'exe',
          category: 'Software',
          subfolder: 'Software/EXE',
          size_bytes: 13700000,
          source_path: 'C:\\Users\\User\\Downloads\\DockerDesktopInstaller.exe',
          target_relative_path: 'Software/EXE/DockerDesktopInstaller.exe',
        },
      ],
      skipped_files: [
        { path: 'C:\\Users\\User\\Downloads\\installer.exe.crdownload', reason: 'incomplete_download' },
        { path: 'C:\\Users\\User\\Downloads\\desktop.ini', reason: 'hidden_system' },
      ],
    } as unknown as T);
  }

  if (cmd === 'preview') {
    return Promise.resolve({
      downloads_dir: 'C:\\Users\\User\\Downloads',
      total_files: 6,
      total_bytes: 48920112,
      planned_moves: [
        {
          source: 'C:\\Users\\User\\Downloads\\Q3_Financial_Report.pdf',
          destination: 'C:\\Users\\User\\Downloads\\Documents\\PDF\\Q3_Financial_Report.pdf',
          file_size: 3450000,
          category: 'Documents',
          extension: 'pdf',
        },
        {
          source: 'C:\\Users\\User\\Downloads\\Meeting_Notes.docx',
          destination: 'C:\\Users\\User\\Downloads\\Documents\\Word\\Meeting_Notes.docx',
          file_size: 524000,
          category: 'Documents',
          extension: 'docx',
        },
        {
          source: 'C:\\Users\\User\\Downloads\\app_wireframe.png',
          destination: 'C:\\Users\\User\\Downloads\\Images\\PNG\\app_wireframe.png',
          file_size: 4120000,
          category: 'Images',
          extension: 'png',
        },
        {
          source: 'C:\\Users\\User\\Downloads\\hero_wallpaper.jpg',
          destination: 'C:\\Users\\User\\Downloads\\Images\\hero_wallpaper.jpg',
          file_size: 8900000,
          category: 'Images',
          extension: 'jpg',
        },
        {
          source: 'C:\\Users\\User\\Downloads\\database_backup_2026.zip',
          destination: 'C:\\Users\\User\\Downloads\\Archives\\ZIP\\database_backup_2026.zip',
          file_size: 18200000,
          category: 'Archives',
          extension: 'zip',
        },
        {
          source: 'C:\\Users\\User\\Downloads\\DockerDesktopInstaller.exe',
          destination: 'C:\\Users\\User\\Downloads\\Software\\EXE\\DockerDesktopInstaller.exe',
          file_size: 13700000,
          category: 'Software',
          extension: 'exe',
        },
      ],
    } as unknown as T);
  }

  if (cmd === 'organize') {
    return Promise.resolve({
      batch_id: 'a1b2c3d4-e5f6-4788-86e6-c758d1d37ec6',
      total_files: 6,
      successful_moves: 6,
      failed_moves: 0,
      is_dry_run: args.includes('--dry-run'),
      moved_items: [],
      failed_items: [],
    } as unknown as T);
  }

  if (cmd === 'history') {
    return Promise.resolve({
      batches: [
        {
          id: 'a1b2c3d4-e5f6-4788-86e6-c758d1d37ec6',
          timestamp: new Date().toISOString(),
          total_files: 6,
          successful_moves: 6,
          failed_moves: 0,
          status: 'COMPLETED',
          notes: 'Organized via CleanDownloads',
        },
        {
          id: 'b7c8d9e0-1122-3344-5566-778899aabbcc',
          timestamp: new Date(Date.now() - 86400000 * 2).toISOString(),
          total_files: 18,
          successful_moves: 18,
          failed_moves: 0,
          status: 'COMPLETED',
          notes: 'Scheduled auto-run',
        },
      ],
    } as unknown as T);
  }

  if (cmd === 'status') {
    return Promise.resolve({
      version: '1.0.0',
      downloads_dir: 'C:\\Users\\User\\Downloads',
      app_data_dir: 'C:\\Users\\User\\AppData\\Local\\CleanDownloads',
      recursive: false,
      rules_count: 15,
      stats: {
        total_batches: 2,
        active_organized_files: 24,
        total_undone_files: 0,
        total_failed_moves: 0,
        category_breakdown: { Documents: 10, Images: 8, Archives: 4, Software: 2 },
      },
      scheduler: {
        is_registered: true,
        is_enabled: true,
        next_run_time: '2026-11-02 09:00:00',
        last_run_time: '2026-11-01 09:00:00',
      },
    } as unknown as T);
  }

  if (cmd === 'config') {
    return Promise.resolve({
      version: '1.0.0',
      downloads_dir: null,
      recursive: false,
      min_file_size_bytes: 0,
      max_file_size_bytes: null,
      conflict_strategy: 'rename',
      ignored_extensions: ['crdownload', 'part', 'tmp', 'download', 'aria2', 'opdownload'],
      excluded_directories: ['Documents', 'Images', 'Videos', 'Audio', 'Archives', 'Software', 'Code', 'Other'],
      rules: [
        { name: 'PDF Documents', category: 'Documents', subfolder: 'Documents/PDF', extensions: ['pdf'] },
        { name: 'Word Documents', category: 'Documents', subfolder: 'Documents/Word', extensions: ['doc', 'docx', 'odt', 'rtf'] },
        { name: 'PNG Images', category: 'Images', subfolder: 'Images/PNG', extensions: ['png'] },
        { name: 'Other Images', category: 'Images', subfolder: 'Images', extensions: ['jpg', 'jpeg', 'webp', 'gif'] },
        { name: 'ZIP Archives', category: 'Archives', subfolder: 'Archives/ZIP', extensions: ['zip'] },
        { name: 'Software', category: 'Software', subfolder: 'Software/EXE', extensions: ['exe', 'msi'] },
      ],
      default_fallback_folder: 'Other',
    } as unknown as T);
  }

  if (cmd === 'undo') {
    return Promise.resolve({
      success: true,
      message: 'Batch successfully restored to original locations.',
    } as unknown as T);
  }

  return Promise.resolve({} as T);
}
