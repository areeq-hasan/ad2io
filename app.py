import io
import atexit

from flask import Flask, Response, request
from flask_cors import CORS

import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

from device import Devices, Waveform, Pulse

devices = Devices()

app = Flask(__name__)
CORS(app)


@app.route("/devices")
def enumerate_devices():
    devices.load()
    return devices.available


@atexit.register
@app.route("/devices/close")
def close_devices():
    devices.close()
    return "Closed all devices."


@app.route("/device/activate")
def activate_device():
    devices.activate(int(request.args.get("index")))
    return f"Activated device {devices.active.index} (handle: {devices.active.handle})."


@app.route("/device/deactivate")
def deactivate_device():
    devices.deactivate()
    return "Deactivated device."


@app.route("/device/start")
def start():
    channel = int(request.args.get("channel"))
    waveform = Waveform(
        function=int(request.args.get("function")),
        frequency=int(request.args.get("frequency")),
        amplitude=float(request.args.get("amplitude")),
        offset=float(request.args.get("offset")),
        symmetry=float(request.args.get("symmetry")),
        phase=float(request.args.get("phase")),
    )

    devices.active.start(channel, waveform)

    return "Started."


def acquisition():
    for figure in devices.active.acquire_plots():
        image = io.BytesIO()
        figure.savefig(image, format="svg")

        yield (
            b"--frame\r\n"
            b"Content-Type: image/svg+xml\r\n\r\n" + image.getvalue() + b"\r\n"
        )


@app.route("/device/acquire")
def acquire():
    return Response(
        acquisition(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@app.route("/device/pulse/start")
def start_pulsing():
    devices.active.start_pulsing(
        Pulse(
            channel=int(request.args.get("channel")),
        )
    )
    return "Started pulsing."


@app.route("/device/pulse/stop")
def stop_pulsing():
    devices.active.stop_pulsing(
        Pulse(
            channel=int(request.args.get("channel")),
        )
    )
    return "Stopped pulsing."


@app.route("/device/stop")
def stop():
    devices.active.stop()
    return "Stopped."
