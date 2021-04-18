import os

from flask import Flask, render_template, request, redirect, url_for

# from werkzeug import secure_filename


UPLOAD_FOLDER = "server_uploads"

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


@app.route('/home')
def home():
    return render_template('file_input.html')


@app.route('/success/<name>')
def success(name):
    return render_template('upload_successful.html', file_name=name)


@app.route('/upload', methods=['POST', 'GET'])
def upload():
    if request.method == 'POST':
        f = request.files['csv_file']
        f.save(os.path.join(app.config['UPLOAD_FOLDER'], f.filename))
        return redirect(url_for('success', name=f.filename))


if __name__ == '__main__':
    app.run()
