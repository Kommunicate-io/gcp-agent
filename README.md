# 🚀 GCP Multi-Project Health Agent

Monitor CPU, memory, and VM count across multiple GCP projects.

## Features
- ✅ Average CPU utilization (last 10m)
- ✅ Average Memory % (needs Ops Agent installed on VMs)
- ✅ Number of RUNNING VMs
- ✅ Per-instance CPU+Memory breakdown

## Projects Covered
Currently configured for:
- km-prod
- km-prod-cn-443607
- km-prod-eu
- km-prod-in

(You can edit `main.py` → `PROJECTS` list to add more)

---

## 🔑 Setup

1. Enable APIs in each project:
   - Compute Engine API
   - Cloud Monitoring API

2. Create service account (done in `km-dev-434106` for example):
   - Roles required in each target project:
     - `roles/compute.viewer`
     - `roles/monitoring.viewer`

3. Download and export credentials:
```bash
export GOOGLE_APPLICATION_CREDENTIALS="~/gcp-agent-key.json"


TO RUN

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python main.py --all  #for all project

python main.py --all

python main.py --project km-prod

