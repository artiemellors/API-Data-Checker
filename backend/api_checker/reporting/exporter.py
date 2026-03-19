"""JSON and CSV exporters for scan results."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime


class JsonExporter:
    @staticmethod
    def export(scan, services, probes) -> bytes:
        """Produce a JSON export of the full scan, grouped by service."""
        probe_map: dict[int | None, list] = {}
        for pr in probes:
            probe_map.setdefault(pr.service_id, []).append(pr)

        service_blocks = []
        for svc in services:
            service_probes = probe_map.get(svc.id, [])
            service_blocks.append(
                {
                    "id": svc.id,
                    "service_name": svc.service_name,
                    "category": svc.category,
                    "confidence": svc.confidence,
                    "evidence": svc.evidence,
                    "extracted_keys": svc.extracted_keys,
                    "probes": [
                        {
                            "probe_url": p.probe_url,
                            "probe_method": p.probe_method,
                            "probe_payload": p.probe_payload,
                            "response_status": p.response_status,
                            "data_fields_found": p.data_fields_found,
                            "sample_records": p.sample_records,
                            "error": p.error,
                            "probed_at": (
                                p.probed_at.isoformat() if p.probed_at else None
                            ),
                        }
                        for p in service_probes
                    ],
                }
            )

        payload = {
            "scan_id": scan.id,
            "url": scan.url,
            "domain": scan.domain,
            "status": scan.status,
            "started_at": scan.started_at.isoformat() if scan.started_at else None,
            "completed_at": scan.completed_at.isoformat() if scan.completed_at else None,
            "endpoints_discovered": scan.endpoints_discovered,
            "services_found": scan.services_found,
            "probes_completed": scan.probes_completed,
            "errors": scan.errors,
            "services": service_blocks,
        }
        return json.dumps(payload, indent=2).encode("utf-8")


class CsvExporter:
    COLUMNS = [
        "domain",
        "scan_id",
        "service_name",
        "category",
        "confidence",
        "extracted_keys",
        "probe_url",
        "response_status",
        "data_fields_count",
        "data_fields",
        "sample_record_count",
        "error",
    ]

    @staticmethod
    def export(scan, services, probes) -> bytes:
        """Produce a flat CSV — one row per probe result."""
        probe_map: dict[int | None, list] = {}
        for pr in probes:
            probe_map.setdefault(pr.service_id, []).append(pr)

        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=CsvExporter.COLUMNS)
        writer.writeheader()

        for svc in services:
            svc_probes = probe_map.get(svc.id, [])
            if not svc_probes:
                writer.writerow(
                    {
                        "domain": scan.domain,
                        "scan_id": scan.id,
                        "service_name": svc.service_name,
                        "category": svc.category,
                        "confidence": round(svc.confidence, 3),
                        "extracted_keys": "|".join(
                            f"{k}={v}" for k, v in svc.extracted_keys.items()
                        ),
                        "probe_url": "",
                        "response_status": "",
                        "data_fields_count": 0,
                        "data_fields": "",
                        "sample_record_count": 0,
                        "error": "",
                    }
                )
            for pr in svc_probes:
                writer.writerow(
                    {
                        "domain": scan.domain,
                        "scan_id": scan.id,
                        "service_name": svc.service_name,
                        "category": svc.category,
                        "confidence": round(svc.confidence, 3),
                        "extracted_keys": "|".join(
                            f"{k}={v}" for k, v in svc.extracted_keys.items()
                        ),
                        "probe_url": pr.probe_url,
                        "response_status": pr.response_status or "",
                        "data_fields_count": len(pr.data_fields_found),
                        "data_fields": "|".join(pr.data_fields_found),
                        "sample_record_count": len(pr.sample_records),
                        "error": pr.error or "",
                    }
                )

        # UTF-8 BOM for Excel compatibility
        return ("\ufeff" + buf.getvalue()).encode("utf-8")
