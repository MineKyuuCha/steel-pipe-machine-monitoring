"""
receiver.py
-----------
Small Flask server that receives ON/OFF events from the ESP32 over WiFi
and writes them into machines.db via database.insert_event().

Run this ALONGSIDE Streamlit, in its own terminal:
    pip install flask
    python receiver.py

It listens on port 5000 on ALL network interfaces (host="0.0.0.0"), which
is what makes it reachable from the ESP32 elsewhere on your WiFi -- not
just from this PC itself.

Find this PC's local IP (ipconfig / ifconfig) and put
    http://<that-ip>:5000/event
into the ESP32 firmware's SERVER_URL.
"""

from datetime import datetime

from flask import Flask, request, jsonify

from database import init_db, insert_event, MACHINES

app = Flask(__name__)
init_db()


@app.route("/event", methods=["POST"])
def receive_event():
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"error": "No JSON body received"}), 400

    machine = data.get("machine")
    status = data.get("status")

    if machine not in MACHINES:
        return jsonify({"error": f"Unknown machine '{machine}'. Expected one of {MACHINES}"}), 400

    if status not in ("ON", "OFF"):
        return jsonify({"error": f"Invalid status '{status}'. Expected 'ON' or 'OFF'"}), 400

    insert_event(machine, status, datetime.now())
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Received: Machine {machine} -> {status}")

    return jsonify({"ok": True, "machine": machine, "status": status}), 200


@app.route("/", methods=["GET"])
def health_check():
    """Visit http://<pc-ip>:5000/ in a browser to confirm the receiver is alive."""
    return "ESP32 receiver is running.", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
