from flask import Flask, render_template, request
from health_agent import (
    get_project_cpu_avg,
    get_project_mem_avg,
    list_running_vms,
    get_per_instance_breakdown,
)

app = Flask(__name__)

PROJECTS = [
    "km-prod",
    "km-prod-cn-443607",
    "km-prod-eu",
    "km-prod-in",
    "km-prod-us",
    "km-dev-434106",
]

@app.route("/", methods=["GET", "POST"])
def index():
    project_id = request.form.get("project_id")
    result = None
    if project_id:
        cpu_avg = get_project_cpu_avg(project_id)
        mem_avg = get_project_mem_avg(project_id)
        vm_count, vms = list_running_vms(project_id)
        per_instance = get_per_instance_breakdown(project_id)

        result = {
            "project": project_id,
            "cpu_avg": f"{cpu_avg*100:.2f}%" if cpu_avg == cpu_avg else "N/A",
            "mem_avg": f"{mem_avg:.2f}%" if mem_avg == mem_avg else "N/A",
            "vm_count": vm_count,
            "instances": per_instance,
        }

    return render_template("index.html", projects=PROJECTS, result=result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
