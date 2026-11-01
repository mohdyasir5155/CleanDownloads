"""CleanDownloads - Smart Downloads folder organizer for Windows.

One command. Zero clutter.
"""

__app_name__ = "CleanDownloads"
__version__ = "1.0.0"
__author__ = "CleanDownloads Contributors"

from cleandownloads.classifier import ClassificationResult, Classifier
from cleandownloads.config import AppConfig, ConfigManager, RuleConfig
from cleandownloads.history import BatchRecord, HistoryDB, OperationRecord
from cleandownloads.organizer import MovePlan, MoveResult, Organizer
from cleandownloads.scanner import Scanner, ScanResult
from cleandownloads.undo import UndoEngine, UndoResult

__all__ = [
    "AppConfig",
    "BatchRecord",
    "ClassificationResult",
    "Classifier",
    "ConfigManager",
    "HistoryDB",
    "MovePlan",
    "MoveResult",
    "OperationRecord",
    "Organizer",
    "RuleConfig",
    "ScanResult",
    "Scanner",
    "UndoEngine",
    "UndoResult",
    "__app_name__",
    "__author__",
    "__version__",
]
