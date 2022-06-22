from flask import Flask, redirect, request, render_template, url_for
from flask_dropzone import Dropzone
# import os
from datetime import datetime

from data.schedule import Schedule

from data.parse import parse_xer_file, find_xer_errors
from services.schedule_services import parse_schedule_cash_flow, parse_schedule_work_flow, parse_float_chart_data

CODEC = 'cp1252'  # Encoding standard for xer file

# basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)

#### DO NOT SHARE THIS SECRET KEY - HIDE IF POST TO GITHUB
app.config['SECRET_KEY'] = "this is the secret key to my web app"
app.config.update(
    # UPLOADED_PATH = os.path.join(basedir,'uploads'),
    DROPZONE_ALLOWED_FILE_CUSTOM = True,
    DROPZONE_ALLOWED_FILE_TYPE = '.xer',
    DROPZONE_MAX_FILE_SIZE = 15,
    DROPZONE_TIMEOUT = 5*60*1000,
    DROPZONE_MAX_FILES = 2,
    # DROPZONE_UPLOAD_MULTIPLE = True,
    # DROPZONE_PARALLEL_UPLOADS = 2
)

dropzone = Dropzone(app)

files = []
new_files = []

cash_flow = {}
work_flow = {}

@app.context_processor
def inject_today_date():
    return {'today_date': datetime.today()}

@app.template_filter('formatdate')
def format_date(val):
    if isinstance(val, datetime):
        return datetime.strftime(val, "%d-%b-%Y")

    return val

@app.template_filter('formatnumber')
def format_int(val):
    if isinstance(val, int):
        return f'{val:,}'
    if isinstance(val, float):
        return f'{val:,.2f}'
    
    return val

@app.template_filter('formatabs')
def format_int(val):
    if isinstance(val, int):
        return f'{abs(val):,}'
    if isinstance(val, float):
        return f'{abs(val):,.2f}'
    
    return val

@app.template_filter('formatvariance')
def format_var(val):
    if isinstance(val, int):
        return f'{val:+,}'
    if isinstance(val, float):
        return f'{val:+,.2f}'
    
    return val

@app.route('/', methods=['GET', 'POST'])
def index():
    global files
    global new_files

    if request.method == 'GET':
        new_files = []
    if request.method == 'POST':
        file = parse_xer_file(request.files.get('file').read().decode(CODEC))
        if not (errors:=find_xer_errors(file)) is None:
            error_str = '\r\n'.join(errors)
            return f'XER contains errors!\r\n{error_str}', 400

        export_xer_projects = tuple(p for p in file.get('PROJECT', []) if p['export_flag'])
        if len(export_xer_projects) != 1:
            return f'XER contains multiple schedules!', 400

        proj_id = export_xer_projects[0]['proj_id']
        new_files.append(Schedule(proj_id, **file))

    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    global files
    global new_files
    schedules = {}

    if new_files:
        files = new_files[:]
        new_files = []

    if not files:
        return redirect(url_for('index'))

    if files[0] >= files[1]:
        schedules['current'] = files[0]
        schedules['previous'] = files[1]
    else:
        schedules['current'] = files[1]
        schedules['previous'] = files[0]

    for version in ['current', 'previous']:
        cash_flow[version] = parse_schedule_cash_flow(schedules[version])
        work_flow[version] = parse_schedule_work_flow(schedules[version], schedules[version].start, schedules[version].finish)

    float_data = parse_float_chart_data(schedules['current'].tasks(), schedules['previous'].tasks())

    return render_template(
        'dashboard.html',
        schedules=schedules,
        cash_flow=cash_flow,
        work_flow=work_flow,
        float_data=float_data)

def main():
    app.run(debug=True)

if __name__ == '__main__':
    main()