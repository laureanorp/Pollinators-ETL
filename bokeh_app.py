from flask import Flask, render_template

app = Flask(__name__)


@app.route('/home')
def home():
    """ Main home screen for the web app """
    return render_template('bokeh.html')


if __name__ == '__main__':
    app.run()
