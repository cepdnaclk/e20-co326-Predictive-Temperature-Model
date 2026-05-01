import json
import time
from datetime import datetime
import paho.mqtt.client as mqtt
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.console import Console
from rich.progress import BarColumn, Progress
from rich import box

# Configuration
BROKER = "localhost"
PORT = 1883
TOPIC = "sensors/+/project33/+/data"

class MQTTVisualizer:
    def __init__(self):
        self.data = {}
        self.console = Console()
        self.last_update = "Never"

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            device_id = payload.get("device_id", "unknown")
            self.data[device_id] = payload
            self.last_update = datetime.now().strftime("%H:%M:%S")
        except Exception:
            pass

    def make_device_table(self):
        table = Table(box=box.DOUBLE_EDGE, expand=True)
        table.add_column("Device ID", style="cyan", no_wrap=True)
        table.add_column("Actual", style="bold white")
        table.add_column("Predicted", style="yellow")
        table.add_column("Trend", style="magenta")
        table.add_column("Anomaly", style="red")
        table.add_column("Last Update", style="dim")

        for dev_id, info in sorted(self.data.items()):
            actual = info.get("actual_temp", 0)
            pred = info.get("predicted_temp", 0)
            trend = info.get("trend", "N/A").upper()
            anomaly = "⚠️ YES" if info.get("is_anomaly") else "OK"
            ts = info.get("timestamp", "").split("T")[-1][:8]

            # Color coding trend
            trend_style = "green" if "STABLE" in trend else "yellow"
            if "WARMING" in trend: trend_style = "bold red"
            if "COOLING" in trend: trend_style = "bold blue"

            table.add_row(
                dev_id,
                f"{actual:.2f} °C",
                f"{pred:.2f} °C" if pred else "---",
                f"[{trend_style}]{trend}[/]",
                anomaly,
                ts
            )
        return table

    def make_gauge_panel(self):
        progress = Progress(
            "{task.description}",
            BarColumn(bar_width=None),
            "[progress.percentage]{task.percentage:>3.0f}%",
        )
        
        for dev_id, info in sorted(self.data.items()):
            temp = info.get("actual_temp", 0)
            # Map 20-50 degrees to 0-100%
            percentage = max(0, min(100, (temp - 20) * 3.33))
            color = "green" if temp < 35 else "red"
            progress.add_task(f"[bold]{dev_id}[/]", total=100, completed=percentage)
            
        return Panel(progress, title="[bold]Temperature Gauges (20°C - 50°C)[/]", border_style="blue")

    def run(self):
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        client.on_message = self.on_message
        
        try:
            client.connect(BROKER, PORT, 60)
            client.subscribe(TOPIC)
            client.loop_start()
        except Exception as e:
            self.console.print(f"[red]Error connecting to MQTT: {e}[/]")
            return

        layout = Layout()
        layout.split_column(
            Layout(name="upper", size=10),
            Layout(name="lower")
        )

        with Live(layout, refresh_per_second=4, screen=True) as live:
            while True:
                layout["upper"].update(self.make_gauge_panel())
                layout["lower"].update(
                    Panel(
                        self.make_device_table(),
                        title=f"Live MQTT Stream: {TOPIC} | Last Rx: {self.last_update}",
                        subtitle="[dim]Press Ctrl+C to Exit[/]",
                        border_style="cyan"
                    )
                )
                time.sleep(0.2)

if __name__ == "__main__":
    visualizer = MQTTVisualizer()
    visualizer.run()
