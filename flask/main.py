from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)


@app.route('/hello', methods=['GET'])
def hello():
    return "<h1>Just: Hello</h1>"


@app.route('/home')
def home():
    return render_template('file_input.html')


@app.route('/success/<name>')
def success(name):
    return render_template('upload_successful.html', file_name=name)


@app.route('/upload', methods=['POST', 'GET'])
def upload():
    if request.method == 'POST':
        form_text = request.form['name_textbox']
        return redirect(url_for('success', name=form_text))


if __name__ == '__main__':
    app.run()
