"""
Data Exporter - exports collected game data to various formats.

Supports:
- JSON: Full fidelity, nested structure
- CSV: Flat tabular format, one row per spin
- Parquet: Columnar format, compressed, fast reads
"""

import csv
import json
import gzip
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union, Any
from datetime import datetime


class DataExporter:
    """
    Export game data to various formats.

    Usage:
        exporter = DataExporter("/tmp/exports")

        # Export all sessions to CSV
        exporter.export_sessions(collector, format="csv")

        # Export spins to Parquet
        exporter.export_spins(collector, format="parquet")

        # Export to specific path
        exporter.export_sessions(collector, output_path="/tmp/my_data.csv")
    """

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = Path(output_dir) if output_dir else None
        if self.output_dir:
            self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_sessions(
        self,
        collector: Any,
        format: str = "json",
        output_path: Optional[Union[str, Path]] = None,
        session_ids: Optional[list[str]] = None,
        compress: bool = False,
    ) -> Optional[Path]:
        """
        Export session data.

        Args:
            collector: DataCollector instance
            format: "json", "csv", or "parquet"
            output_path: Override output path
            session_ids: Filter to specific sessions (None = all)
            compress: Gzip compress the output
        """
        sessions = collector.list_sessions()
        if session_ids:
            sessions = [s for s in sessions if s.get("session_id") in session_ids]

        if not sessions:
            return None

        if output_path:
            out_path = Path(output_path)
        else:
            out_path = self.output_dir or Path(".")
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_path = out_path / f"sessions_{ts}.{format}"

        if format == "json":
            return self._export_sessions_json(sessions, out_path, compress)
        elif format == "csv":
            return self._export_sessions_csv(sessions, out_path, compress)
        elif format == "parquet":
            return self._export_sessions_parquet(sessions, out_path)
        else:
            raise ValueError(f"Unknown format: {format}")

    def export_spins(
        self,
        collector: Any,
        format: str = "json",
        output_path: Optional[Union[str, Path]] = None,
        session_ids: Optional[list[str]] = None,
        compress: bool = False,
    ) -> Optional[Path]:
        """
        Export spin records.

        Args:
            collector: DataCollector instance
            format: "json", "csv", or "parquet"
            output_path: Override output path
            session_ids: Filter to specific sessions
            compress: Gzip compress the output
        """
        # Collect all spins across sessions
        all_spins = []
        sessions = collector.list_sessions()

        for session in sessions:
            sid = session.get("session_id")
            if session_ids and sid not in session_ids:
                continue

            spins_file = collector.storage_dir / f"spins_{sid}.json"
            if spins_file.exists():
                with open(spins_file) as f:
                    spins = json.load(f)
                    for s in spins:
                        s["session_id"] = sid
                        s["game_name"] = session.get("game_name", "unknown")
                    all_spins.extend(spins)

        if not all_spins:
            return None

        if output_path:
            out_path = Path(output_path)
        else:
            out_path = self.output_dir or Path(".")
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_path = out_path / f"spins_{ts}.{format}"

        if format == "json":
            return self._export_spins_json(all_spins, out_path, compress)
        elif format == "csv":
            return self._export_spins_csv(all_spins, out_path, compress)
        elif format == "parquet":
            return self._export_spins_parquet(all_spins, out_path)
        else:
            raise ValueError(f"Unknown format: {format}")

    def export_summary(
        self,
        collector: Any,
        format: str = "json",
        output_path: Optional[Union[str, Path]] = None,
        compress: bool = False,
    ) -> Optional[Path]:
        """
        Export aggregated summary across all sessions.
        """
        sessions = collector.list_sessions()

        # Compute aggregate stats
        total_spins = 0
        total_bet = 0.0
        total_wins = 0.0
        total_profit = 0.0

        for session in sessions:
            summary = session.get("summary", {})
            total_spins += summary.get("total_spins", 0)
            total_bet += summary.get("total_bet", 0)
            total_wins += summary.get("total_wins", 0)
            total_profit += summary.get("net_profit", 0)

        roi = ((total_wins / total_bet) - 1) * 100 if total_bet > 0 else 0.0

        summary_data = {
            "export_time": datetime.now().isoformat(),
            "total_sessions": len(sessions),
            "total_spins": total_spins,
            "total_bet": total_bet,
            "total_wins": total_wins,
            "net_profit": total_profit,
            "roi_percent": roi,
            "sessions": [
                {
                    "session_id": s.get("session_id"),
                    "game_name": s.get("game_name"),
                    "start_time": s.get("start_time"),
                    "summary": s.get("summary", {}),
                }
                for s in sessions
            ],
        }

        if output_path:
            out_path = Path(output_path)
        else:
            out_path = self.output_dir or Path(".")
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_path = out_path / f"summary_{ts}.{format}"

        if format == "json":
            return self._export_summary_json(summary_data, out_path, compress)
        elif format == "csv":
            # Flatten to one row per session
            return self._export_summary_csv(summary_data["sessions"], out_path, compress)
        else:
            raise ValueError(f"Format {format} not supported for summary")

    # -------------------------------------------------------------------------
    # JSON export
    # -------------------------------------------------------------------------

    def _export_sessions_json(
        self,
        sessions: list[dict],
        out_path: Path,
        compress: bool,
    ) -> Path:
        data = {"sessions": sessions, "export_time": datetime.now().isoformat()}
        return self._write_json(data, out_path, compress)

    def _export_spins_json(
        self,
        spins: list[dict],
        out_path: Path,
        compress: bool,
    ) -> Path:
        data = {"spins": spins, "export_time": datetime.now().isoformat()}
        return self._write_json(data, out_path, compress)

    def _export_summary_json(
        self,
        summary: dict,
        out_path: Path,
        compress: bool,
    ) -> Path:
        return self._write_json(summary, out_path, compress)

    def _write_json(self, data: dict, path: Path, compress: bool) -> Path:
        if compress:
            gz_path = Path(str(path) + ".gz")
            with gzip.open(str(gz_path), "wt", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            return gz_path
        else:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            return path

    # -------------------------------------------------------------------------
    # CSV export
    # -------------------------------------------------------------------------

    def _export_sessions_csv(
        self,
        sessions: list[dict],
        out_path: Path,
        compress: bool,
    ) -> Path:
        if not sessions:
            return out_path

        fieldnames = list(sessions[0].keys())
        # Flatten nested summary
        for s in sessions:
            summary = s.pop("summary", {})
            for k, v in summary.items():
                s[f"summary_{k}"] = v

        return self._write_csv(sessions, out_path, compress)

    def _export_spins_csv(
        self,
        spins: list[dict],
        out_path: Path,
        compress: bool,
    ) -> Path:
        if not spins:
            return out_path
        return self._write_csv(spins, out_path, compress)

    def _export_summary_csv(
        self,
        sessions: list[dict],
        out_path: Path,
        compress: bool,
    ) -> Path:
        return self._write_csv(sessions, out_path, compress)

    def _write_csv(
        self,
        records: list[dict],
        path: Path,
        compress: bool,
    ) -> Path:
        if not records:
            return path

        # Flatten nested dicts and lists
        flat_records = []
        for record in records:
            flat = self._flatten_dict(record)
            flat_records.append(flat)

        fieldnames = list(flat_records[0].keys())

        if compress:
            gz_path = Path(str(path) + ".gz")
            with gzip.open(str(gz_path), "wt", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(flat_records)
            return gz_path
        else:
            with open(path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(flat_records)
            return path

    def _flatten_dict(self, d: dict, parent_key: str = "", sep: str = "_") -> dict:
        """Flatten nested dict/list structures for CSV compatibility."""
        items: list[tuple[str, Any]] = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep).items())
            elif isinstance(v, list):
                items.append((new_key, json.dumps(v)))
            else:
                items.append((new_key, v))
        return dict(items)

    # -------------------------------------------------------------------------
    # Parquet export
    # -------------------------------------------------------------------------

    def _try_parquet(self, data: list[dict], path: Path) -> bool:
        """
        Try to export to Parquet using pandas/pyarrow.
        Returns True on success, False if dependencies missing.
        """
        try:
            import pandas as pd

            df = pd.DataFrame(data)
            df.to_parquet(path, index=False)
            return True
        except ImportError:
            return False

    def _export_sessions_parquet(
        self,
        sessions: list[dict],
        out_path: Path,
    ) -> Path:
        if not self._try_parquet(sessions, out_path):
            # Fallback to JSON
            return self._export_sessions_json(sessions, out_path.with_suffix(".json"), False)
        return out_path

    def _export_spins_parquet(
        self,
        spins: list[dict],
        out_path: Path,
    ) -> Path:
        if not self._try_parquet(spins, out_path):
            return self._export_spins_json(spins, out_path.with_suffix(".json"), False)
        return out_path

    def _export_summary_parquet(
        self,
        summary: dict,
        out_path: Path,
    ) -> Path:
        return self._export_summary_json(summary, out_path.with_suffix(".json"), False)


class SchemaValidator:
    """
    Validates game data against expected schemas.

    Usage:
        validator = SchemaValidator()

        # Register a schema
        validator.register("spin", {
            "spin_id": str,
            "balance_before": float,
            "balance_after": float,
            "bet_amount": float,
            "win_amount": float,
            "is_free_spin": bool,
        })

        # Validate
        result = validator.validate("spin", my_spin_record)
        if not result.valid:
            print("Errors:", result.errors)
    """

    @dataclass
    class ValidationResult:
        valid: bool
        errors: list[str]
        warnings: list[str]

    def __init__(self):
        self._schemas: dict[str, dict] = {}

    def register(self, schema_name: str, schema: dict) -> None:
        """Register a named schema."""
        self._schemas[schema_name] = schema

    def validate(self, schema_name: str, data: dict) -> ValidationResult:
        """Validate data against a registered schema."""
        schema = self._schemas.get(schema_name)
        if schema is None:
            return self.ValidationResult(
                valid=True,
                errors=[],
                warnings=[f"Schema '{schema_name}' not registered"],
            )

        errors = []
        warnings = []

        for field_name, expected_type in schema.items():
            if field_name not in data:
                errors.append(f"Missing required field: {field_name}")
            else:
                value = data[field_name]
                if not self._check_type(value, expected_type):
                    warnings.append(
                        f"Field '{field_name}' has type {type(value).__name__}, "
                        f"expected {expected_type}"
                    )

        return self.ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    @staticmethod
    def _check_type(value: Any, expected: Any) -> bool:
        """Check if value matches expected type annotation."""
        if expected is float:
            return isinstance(value, (int, float))
        if expected is bool:
            return isinstance(value, bool)
        if expected is str:
            return isinstance(value, str)
        if expected is int:
            return isinstance(value, int)
        if expected is dict:
            return isinstance(value, dict)
        if expected is list:
            return isinstance(value, list)
        return isinstance(value, expected)
