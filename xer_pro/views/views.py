from flask import Blueprint, render_template, request, redirect, url_for
import os

blueprint = Blueprint('views', __name__, template_folder='templates')

@blueprint.route('/', methods=['POST','GET'])
def index():
    if request.method == "GET":
        return render_template('index.html')

    f = request.files.get('file')
    f.save(os.path.join(app.config(UPLOADED_PATH)))