from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "🎵 Server is working!"

@app.route("/callback")
def callback():
    return "🎵 Callback route is working!"

if __name__ == "__main__":
    print("🌐 Starting test server on port 8888...")
    app.run(host='0.0.0.0', port=8888, debug=True)