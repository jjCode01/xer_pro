from flask import Flask, redirect, request, render_template, url_for
from flask_dropzone import Dropzone
import os
from datetime import datetime

from data.parse import parse_xer_file

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
    DROPZONE_UPLOAD_MULTIPLE = True,
    DROPZONE_PARALLEL_UPLOADS = 2
)

dropzone = Dropzone(app)

files = []

@app.template_filter('formatdate')
def format_date(val):
    if not val:
        return ""
    if isinstance(val, datetime):
        return datetime.strftime(val, "%d-%b-%Y")

    raise ValueError(f'ValueError: val {val} must be a datetime object')

@app.template_filter('formatnumber')
def format_int(val):
    if not val:
        return ""
    if isinstance(val, int):
        return f'{val:,}'
    if isinstance(val, float):
        return f'{val:,.2f}'
    
    return val

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

# @app.route('/', methods=['POST'])
# def upload():
#     return redirect(url_for('dashboard'))

# @app.route('/', methods=['POST'])
# def upload():
#     global schedules
#     schedules = [
#         parse_xer_file(v.read().decode(CODEC)) for k, v
#         in request.files.items() 
#         if k.startswith('file')]

#     # for s in schedules:
#     #     print(s.keys())

#     return render_template('dashboard.html')

        
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    global files
    if request.method == "POST":
        files = [
            parse_xer_file(v.read().decode(CODEC)) for k, v
            in request.files.items() 
            if k.startswith('file')]

    # for s in schedules:
    #     print(s.keys())

    return render_template('dashboard.html', schedules=files)

    # return render_template('dashboard.html')

def main():
    app.run(debug=True)


if __name__ == '__main__':
    main()