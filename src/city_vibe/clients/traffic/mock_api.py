from flask import Flask, jsonify, request

app = Flask(__name__)
@app.route("/traffic")
def get_traffic():
    city = request.args.get("city", "Unknown")
    traffic_data = {
        "city": city,
        "congestion": 0.7,
        "speed": 30,
        "incidents": 2
    }
    return jsonify(traffic_data)

if __name__ == "__main__":
    app.run(port=5001)
