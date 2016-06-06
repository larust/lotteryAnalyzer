from flask import Flask
from flask import render_template
from flask import request

app = Flask(__name__)

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/calculate", methods=['POST'])
def calculate(calculated_value = None):
	return render_template('results.html', calculated_value=request.form['rass'])

if __name__ == "__main__":
    app.run()
