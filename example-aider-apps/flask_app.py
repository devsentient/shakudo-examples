from flask import Flask

app = Flask(__name__)


@app.route('/add/<int:num1>/<int:num2>')
def add(num1, num2):
    return str(num1 + num2)
@app.route('/')
def home():
    return "Welcome to the Flask App!"
    app.run(debug=True, host='0.0.0.0', port=8787)
