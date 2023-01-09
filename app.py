import io
import atexit

from flask import Flask, Response, request
from flask_cors import CORS

from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import matplotlib.pyplot as plt

from device import Devices, Waveform

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


def acquisition():
    for data in devices.active.acquire():
        figure = Figure()
        axes = figure.add_subplot(1, 1, 1)
        axes.plot(data)
        axes.set_title("Analog Acqusition (CH1)")
        axes.set_ylabel("Voltage (V)")
        axes.set_xlabel("Time (seconds)")

        image = io.BytesIO()
        FigureCanvas(figure).print_jpeg(image)

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + image.getvalue() + b"\r\n"
        )


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


@app.route("/device/stream")
def stream():
    return Response(
        acquisition(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@app.route("/device/stop")
def stop():
    devices.active.stop()
    return "Stopped."
