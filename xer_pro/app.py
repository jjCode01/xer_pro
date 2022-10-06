import sched
from flask import Flask, redirect, request, render_template, url_for
from flask_dropzone import Dropzone
from datetime import datetime
import os

from xer_pro.data.schedule import Schedule
from xer_pro.data.task import Task

from xer_pro.data.parse import parse_xer_file, find_xer_errors
from xer_pro.services.schedule_services import (
    parse_schedule_cash_flow,
    parse_schedule_work_flow,
)
from xer_pro.services.schedule_services import (
    parse_float_chart_data,
    parse_status_chart_data,
)
from xer_pro.services.comparison_services import get_schedule_changes
from xer_pro.services.warning_services import get_schedule_warnings

CODEC = "cp1252"  # Encoding standard for xer file

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ["CPM_PRO_KEY"]
app.config.update(
    DROPZONE_ALLOWED_FILE_CUSTOM=True,
    DROPZONE_ALLOWED_FILE_TYPE=".xer",
    DROPZONE_MAX_FILE_SIZE=15,
    DROPZONE_TIMEOUT=5 * 60 * 1000,
    DROPZONE_MAX_FILES=2,
)

dropzone = Dropzone(app)

files = []
new_files = []
schedules = dict()

cash_flow = dict()
work_flow = dict()
float_data = dict()
status_data = dict()
changes = dict()
warnings = dict()
longest_path = dict()


@app.context_processor
def inject_today_date():
    return {"today_date": datetime.today()}


@app.template_filter("formatdate")
def format_date(val):
    if isinstance(val, datetime):
        return datetime.strftime(val, "%d-%b-%Y")
    return val


@app.template_filter("weekday")
def format_date_weekday(val):
    if isinstance(val, datetime):
        return datetime.strftime(val, "%A")
    return val


@app.template_filter("formatnumber")
def format_int(val):
    if isinstance(val, int):
        return f"{val:,}"
    if isinstance(val, float):
        return f"{val:,.2f}"
    if val is None:
        return "-"
    return val


@app.template_filter("formatabs")
def format_abs(val):
    if isinstance(val, int):
        return f"{abs(val):,}"
    if isinstance(val, float):
        return f"{abs(val):,.2f}"
    return val


@app.template_filter("formatvariance")
def format_var(val):
    if isinstance(val, int):
        return f"{val:+,}"
    if isinstance(val, float):
        return f"{val:+,.2f}"
    return val


@app.template_filter("currenttask")
def curr_task(task: Task):
    if not task:
        return None

    global schedules
    if not schedules["current"]:
        return None

    return schedules["current"].tasks_by_id.get(task.activity_id)


@app.template_filter("taskimage")
def task_img(task: Task):
    if not task:
        return "deleted.png"

    if not isinstance(task, Task):
        return ""

    pre = "ms-" if task.is_milestone else ""
    post = "-lp.png" if task.is_longest_path and not task.is_completed else ".png"

    if task.is_not_started:
        return f"{pre}open{post}"
    if task.is_in_progress:
        return f"{pre}active{post}"
    if task.is_completed:
        return f"{pre}complete{post}"


@app.template_filter("sortbystart")
def sort_by_start(tasks: list[Task]):
    return sorted(tasks, key=lambda t: (t.start, t.finish))


@app.template_filter("sortbyfinish")
def sort_by_finish(tasks: list[Task]):
    return sorted(tasks, key=lambda t: (t.finish, t.start))


@app.route("/", methods=["GET", "POST"])
def index():
    global files

    if request.method == "GET":
        files = []
    if request.method == "POST":
        if len(files) > 2:
            files = []
        file = parse_xer_file(request.files.get("file").read().decode(CODEC))
        if not (errors := find_xer_errors(file)) is None:
            error_str = "\r\n".join(errors)
            return error_str, 400

        export_xer_projects = tuple(
            p for p in file.get("PROJECT", []) if p["export_flag"]
        )
        if len(export_xer_projects) != 1:
            return "XER contains multiple schedules!", 400

        proj_id = export_xer_projects[0]["proj_id"]
        files.append(Schedule(proj_id, **file))

    return render_template("index.html")


@app.route("/dashboard")
def dashboard():
    global files
    global schedules
    global cash_flow
    global work_flow
    global float_data
    global status_data
    global changes
    global warnings
    global longest_path

    if files:
        if files[0] >= files[1]:
            schedules["current"] = files[0]
            schedules["previous"] = files[1]
        else:
            schedules["current"] = files[1]
            schedules["previous"] = files[0]

        for version in ["current", "previous"]:
            cash_flow[version] = parse_schedule_cash_flow(schedules[version])
            work_flow[version] = parse_schedule_work_flow(
                schedules[version], schedules[version].start, schedules[version].finish
            )

        float_data = parse_float_chart_data(
            schedules["current"].tasks(), schedules["previous"].tasks()
        )
        status_data = parse_status_chart_data(
            schedules["current"].tasks(), schedules["previous"].tasks()
        )

        changes = get_schedule_changes(schedules["current"], schedules["previous"])
        warnings = get_schedule_warnings(schedules["current"])

        longest_path["current"] = sorted(
            [
                (task, schedules["previous"].tasks_by_id.get(task.activity_id))
                for task in schedules["current"].tasks()
                if task.is_longest_path and not task.is_completed
            ],
            key=lambda t: (t[0].start, t[0].finish),
        )
        longest_path["previous"] = sorted(
            [
                (task, schedules["current"].tasks_by_id.get(task.activity_id))
                for task in schedules["previous"].tasks()
                if task.is_longest_path and not task.is_completed
            ],
            key=lambda t: (t[0].start, t[0].finish),
        )

        files = []

    if not schedules:
        return redirect(url_for("index"))

    return render_template(
        "dashboard.html",
        schedules=schedules,
        cash_flow=cash_flow,
        work_flow=work_flow,
        float_data=float_data,
        status_data=status_data,
        changes=changes,
    )


@app.route("/comparison")
def comparison():
    global schedules
    global changes
    if not schedules:
        return redirect(url_for("index"))

    return render_template("compare.html", schedules=schedules, task_changes=changes)


@app.route("/warnings")
def warnings():
    global schedules
    global warnings
    if not schedules:
        return redirect(url_for("index"))
    return render_template("warnings.html", schedules=schedules, warnings=warnings)


@app.route("/critical")
def critical():
    global schedules
    global longest_path
    if not schedules:
        return redirect(url_for("index"))

    return render_template("critical.html", schedules=schedules, critical=longest_path)
