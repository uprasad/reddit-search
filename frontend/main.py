from flask import Flask, render_template, request

app = Flask(__name__)


@app.route("/", methods=['GET'])
def main():
    args = request.args
    print(args)
    return render_template("index.html", args=args)


if __name__ == "__main__":
    app.run()
