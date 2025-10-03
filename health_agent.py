#!/usr/bin/env python3
"""
Helper functions for GCP Project Health Agent
---------------------------------------------
Provides:
- get_project_cpu_avg
- get_project_mem_avg
- list_running_vms
- get_per_instance_breakdown
"""

import datetime as dt
from typing import Dict, List, Tuple

from google.cloud import monitoring_v3
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

ALIGN_SECONDS = 600  # 10 minutes


def _now_interval(seconds: int = ALIGN_SECONDS) -> Tuple[dt.datetime, dt.datetime]:
    now = dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc)
    start = now - dt.timedelta(seconds=seconds)
    return start, now


def _ts_request_common(project_id: str, metric_type: str) -> monitoring_v3.ListTimeSeriesRequest:
    start, end = _now_interval()
    interval = monitoring_v3.TimeInterval({
        "start_time": {"seconds": int(start.timestamp())},
        "end_time": {"seconds": int(end.timestamp())},
    })
    aggregation = monitoring_v3.Aggregation({
        "alignment_period": {"seconds": ALIGN_SECONDS},
        "per_series_aligner": monitoring_v3.Aggregation.Aligner.ALIGN_MEAN,
        "cross_series_reducer": monitoring_v3.Aggregation.Reducer.REDUCE_MEAN,
    })
    flt = (
        f'metric.type = "{metric_type}" '
        f'AND resource.type = "gce_instance"'
    )
    req = monitoring_v3.ListTimeSeriesRequest(
        name=f"projects/{project_id}",
        filter=flt,
        interval=interval,
        view=monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
        aggregation=aggregation,
    )
    return req


def get_project_cpu_avg(project_id: str) -> float:
    client = monitoring_v3.MetricServiceClient()
    req = _ts_request_common(project_id, "compute.googleapis.com/instance/cpu/utilization")
    series = list(client.list_time_series(request=req))
    if not series:
        return float("nan")
    for ts in series:
        if ts.points:
            return ts.points[0].value.double_value
    return float("nan")


def get_project_mem_avg(project_id: str) -> float:
    client = monitoring_v3.MetricServiceClient()
    req = _ts_request_common(project_id, "agent.googleapis.com/memory/percent_used")
    series = list(client.list_time_series(request=req))
    if not series:
        return float("nan")
    for ts in series:
        if ts.points:
            return ts.points[0].value.double_value
    return float("nan")


def list_running_vms(project_id: str) -> Tuple[int, List[Dict]]:
    compute = build("compute", "v1", cache_discovery=False)
    req = compute.instances().aggregatedList(project=project_id)
    result = []
    while req is not None:
        resp = req.execute()
        for zone, data in resp.get("items", {}).items():
            for inst in data.get("instances", []) if data.get("instances") else []:
                if inst.get("status") == "RUNNING":
                    result.append({
                        "name": inst.get("name"),
                        "zone": inst.get("zone", "").split("/")[-1],
                        "machineType": inst.get("machineType", "").split("/")[-1],
                        "id": inst.get("id"),
                    })
        req = compute.instances().aggregatedList_next(previous_request=req, previous_response=resp)
    return len(result), result


def get_per_instance_breakdown(project_id: str) -> List[Dict]:
    """Return per-instance CPU and memory stats for running VMs with valid names."""
    start, end = _now_interval()
    interval = monitoring_v3.TimeInterval({
        "start_time": {"seconds": int(start.timestamp())},
        "end_time": {"seconds": int(end.timestamp())},
    })
    agg = monitoring_v3.Aggregation({
        "alignment_period": {"seconds": ALIGN_SECONDS},
        "per_series_aligner": monitoring_v3.Aggregation.Aligner.ALIGN_MEAN,
    })
    client = monitoring_v3.MetricServiceClient()

    def fetch(metric_type: str) -> Dict[Tuple[str, str], float]:
        flt = (
            f'metric.type = "{metric_type}" '
            f'AND resource.type = "gce_instance"'
        )
        req = monitoring_v3.ListTimeSeriesRequest(
            name=f"projects/{project_id}",
            filter=flt,
            interval=interval,
            view=monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
            aggregation=agg,
        )
        vals = {}
        for ts in client.list_time_series(request=req):
            labels = ts.resource.labels
            inst = labels.get("instance_id", "")
            zone = labels.get("zone", "")
            key = (inst, zone)
            if ts.points:
                vals[key] = ts.points[0].value.double_value
        return vals

    cpu = fetch("compute.googleapis.com/instance/cpu/utilization")
    mem = fetch("agent.googleapis.com/memory/percent_used")

    compute = build("compute", "v1", cache_discovery=False)
    name_map = {}
    req = compute.instances().aggregatedList(project=project_id)
    while req is not None:
        resp = req.execute()
        for _, data in resp.get("items", {}).items():
            for inst in data.get("instances", []) if data.get("instances") else []:
                name_map[inst.get("id")] = {
                    "name": inst.get("name"),
                    "zone": inst.get("zone", "").split("/")[-1],
                    "machineType": inst.get("machineType", "").split("/")[-1],
                }
        req = compute.instances().aggregatedList_next(previous_request=req, previous_response=resp)

    rows = []
    for (inst_id, zone), cpu_val in cpu.items():
        meta = name_map.get(inst_id)   # only keep VMs with valid names
        if not meta:
            continue   # skip orphaned metrics (numeric IDs only)
        rows.append({
            "instance": meta["name"],
            "zone": meta["zone"],
            "machineType": meta["machineType"],
            "cpu_utilization_pct": round(cpu_val * 100.0, 2),
            "memory_used_pct": round(mem.get((inst_id, zone), float("nan")), 2),
        })
    return rows
