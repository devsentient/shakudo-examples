from flask import Flask

app = Flask(__name__)

@app.route('/hello')
def hello():
    return "Hello, World!"

@app.route('/add/<int:num1>/<int:num2>')
def add(num1, num2):
    return str(num1 + num2)
@app.route('/fibonacci/<int:n>')
def fibonacci(n):
    if n <= 0:
        return "Input should be a positive integer."
    elif n == 1:
        return str(0)
    elif n == 2:
        return str(1)
    else:
        a, b = 0, 1
        for _ in range(2, n):
            a, b = b, a + b
        return str(b)
