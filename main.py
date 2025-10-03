#!/usr/bin/env python3
"""
Multi-Project GCP Health Agent
------------------------------
Monitors multiple GCP projects in one run.

Usage:
  python main.py --all
  python main.py --project <PROJECT_ID>
"""

import argparse
from google.api_core import exceptions as gax_exceptions
from googleapiclient.errors import HttpError
from health_agent import (
    get_project_cpu_avg,
    get_project_mem_avg,
    list_running_vms,
    get_per_instance_breakdown,
)

# 🔹 Define the projects you want to monitor
PROJECTS = [
    "km-prod",
    "km-prod-cn-443607",
    "km-prod-eu",
    "km-prod-in",
    "km-prod-us",
    "km-dev-434106",   # include dev for testing
]

def run_for_project(project_id: str):
    try:
        cpu_avg = get_project_cpu_avg(project_id)
    except gax_exceptions.GoogleAPICallError as e:
        print(f"[!] CPU query failed for {project_id}: {e}")
        cpu_avg = float("nan")

    try:
        mem_avg = get_project_mem_avg(project_id)
    except gax_exceptions.GoogleAPICallError as e:
        print(f"[!] Memory query failed for {project_id}: {e}")
        mem_avg = float("nan")

    try:
        vm_count, vms = list_running_vms(project_id)
    except HttpError as e:
        print(f"[!] VM list failed for {project_id}: {e}")
        vm_count, vms = 0, []

    print("\n=== GCP Project Health (last 10 minutes) ===")
    print(f"Project: {project_id}")
    print(f"Average CPU Utilization: {('%.2f%%' % (cpu_avg*100)) if cpu_avg==cpu_avg else 'N/A'}")
    print(f"Average Memory Used: {('%.2f%%' % (mem_avg)) if mem_avg==mem_avg else 'N/A'}")
    print(f"RUNNING VMs: {vm_count}")

    if vm_count == 0:
        return

    # 🔹 Always print per-instance results
    print("\n-- Per-instance (avg of last 10m) --")
    rows = get_per_instance_breakdown(project_id)
    if not rows:
        print("No per-instance metrics found (ensure Ops Agent is installed).")
    else:
        print(f"{'INSTANCE':32} {'ZONE':15} {'TYPE':20} {'CPU%':>8} {'MEM%':>8}")
        for r in sorted(rows, key=lambda x: (x['zone'], x['instance'])):
            print(f"{r['instance'][:32]:32} {r['zone'][:15]:15} {r['machineType'][:20]:20} {r['cpu_utilization_pct']:8.2f} {r['memory_used_pct']:8.2f}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", help="Run for a single project ID")
    parser.add_argument("--all", action="store_true", help="Run for all projects in PROJECTS list")
    args = parser.parse_args()

    if args.all:
        for pid in PROJECTS:
            run_for_project(pid)
    elif args.project:
        run_for_project(args.project)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
