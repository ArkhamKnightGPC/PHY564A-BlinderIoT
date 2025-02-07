import json
import logging
import random
import sys
import time
import threading
from datetime import datetime
from typing import Iterator
import numpy as np
from paho.mqtt import client as mqtt_client
from typing import Any

from flask import Flask, Response, render_template, request, stream_with_context

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

FS = 100 # Hz: Sampling frequency
LOCK = threading.Lock()

class WebApp:
    def __init__(self, host="0.0.0.0", port=5000, debug=True):
        self.app = Flask(__name__)
        self.host = host
        self.port = port
        self.debug = debug
        self.value = 0  # Value to be displayed on the web page

        random.seed()

        # Define routes
        self.app.add_url_rule("/", "index", self.index)
        self.app.add_url_rule("/chart-data", "chart_data", self.chart_data)

    def index(self) -> str:
        """Serve the main page."""
        return render_template("index.html")

    def update_data(self) -> Iterator[str]:
        """Stream updated data."""
        client_ip = request.headers.getlist("X-Forwarded-For")[0] if request.headers.getlist("X-Forwarded-For") else request.remote_addr or ""

        try:
            logger.info("Client %s connected", client_ip)
            while True:
                json_data = json.dumps(
                    {
                        "time": datetime.now().strftime("%H:%M:%S"),
                        "value": self.value,
                    }
                )
                yield f"data:{json_data}\n\n"
                time.sleep(1)
        except GeneratorExit:
            logger.info("Client %s disconnected", client_ip)

    def chart_data(self) -> Response:
        """Stream chart data to the frontend."""
        response = Response(stream_with_context(self.update_data()), mimetype="text/event-stream")
        response.headers["Cache-Control"] = "no-cache"
        response.headers["X-Accel-Buffering"] = "no"
        return response

    def run(self):
        """Run the Flask application."""
        try:
            self.app.run(host=self.host, port=self.port, debug=self.debug, threaded=True)
        except SystemExit:
            logger.info("Shutting down the application")
            sys.exit(0)

class MqttManager:
    """Class to handle the MQTT connection."""

    def __init__(self, broker: str, port: int, sub_topic: str, pub_topic: str):
        self.broker = broker
        self.port = port
        self.sub_topic = sub_topic
        self.pub_topic = pub_topic
        self.client_id = f'publish-{random.randint(0, 1000)}'
        self.client: mqtt_client.Client = self.connect_mqtt()
        self.subscribe()

    def connect_mqtt(self) -> mqtt_client:
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                logger.info("Connected to MQTT Broker!")
            else:
                logger.error("Failed to connect, return code %d\n", rc)

        client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION1)
        client.on_connect = on_connect
        client.connect(self.broker, self.port)
        return client
    
    def subscribe(self):
        def on_message(client: mqtt_client, userdata: None, msg: mqtt_client.MQTTMessage):
            with LOCK:
                print(f"Received `{msg.payload.decode()}` from `{self.pub_topic}` topic")
        
        self.client.subscribe(self.sub_topic)
        self.client.on_message = on_message

    def publish(self, msg: Any):
        result = self.client.publish(self.pub_topic, msg)
        status = result[0]
        if status == 0:
            print(f"Sent `{msg}` to topic `{self.pub_topic}`")
        else:
            print(f"Failed to send message  '{msg}' to topic {self.pub_topic}")

        # msg_count = 1
            # result: [0, 1]
            # status = result[0]
            # if status == 0:
            #     print(f"Send `{msg}` to topic `{topic}`")
            # else:
            #     print(f"Failed to send message to topic {topic}")
            # msg_count += 1
            # if msg_count > 5:
            #     break

    def run(self):
        self.client.loop_forever()
    
    def run_threaded(self):
        mqtt_thread = threading.Thread(target=self.run, daemon=True)
        mqtt_thread.start()
        
def background_task(app_instance: WebApp):
    """A separate thread to update app.value every second."""
    while True:
        values = get_values()
        f, X = get_fft(values, FS)
        peak = 20  # Hz (expected peak)
        max_val = get_max_around_peak(f, X, peak, 2)
        app_instance.value = max_val  # Update the value
        
        time.sleep(1)

def get_fft(data: np.ndarray, fs:float) -> np.ndarray:
    """Retrieve the FFT of the input data."""
    X = np.fft.fft(data) / len(data)
    f = np.fft.fftfreq(len(data), 1/fs)
    X, f = np.fft.fftshift(X), np.fft.fftshift(f) # apply fftshift
    return f, X

def get_max_around_peak(f: np.ndarray, X: np.ndarray, peak: float, width: float=2.0) -> float:
    """Retrieve the maximum value around the peak [peak-width, peak+width]."""
    mask = np.logical_and(f > peak - width, f < peak + width)
    return np.max(abs(X[mask]))

def get_values() -> np.ndarray:
    """Get the value"""
    return np.random.randint(0, 100, 100)


if __name__ == "__main__":
    # app = WebApp()

    # # Start the background thread
    # update_thread = threading.Thread(target=background_task, args=(app,), daemon=True)
    # update_thread.start()

    # app.run()

    mqtt_manager = MqttManager('192.168.0.107', 1883, "measures", "motor")
    mqtt_manager.run_threaded()
    with LOCK:
        print("MQTT Manager started")
        print("Press Enter to exit\n")
    input("")
