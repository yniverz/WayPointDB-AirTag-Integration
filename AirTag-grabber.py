#!/usr/bin/env python3
import os
import json
import time
import requests
import tkinter as tk
from urllib.parse import urlencode, urlparse, urlunparse, parse_qs

###############################################################################
# Configuration File
###############################################################################

CONFIG_FILE = "my_findmy_config.json"

def load_config():
    """
    Load config from JSON or return a default structure if missing.
    Structure: {"tag_configs": [ { "serial": "...", "server_url": "...", "api_key": "..." }, ... ]}
    """
    if os.path.isfile(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading {CONFIG_FILE}: {e}")

    # Default if file not found or error
    return {
        "tag_configs": []
    }

def save_config(conf):
    """Save config dict to JSON file."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(conf, f, indent=2)
        print(f"Configuration saved to {CONFIG_FILE}")
    except Exception as e:
        print(f"Error saving {CONFIG_FILE}: {e}")

###############################################################################
# Data Models
###############################################################################

class ItemLocation:
    def __init__(self, latitude=0.0, longitude=0.0, timeStamp=0.0,
                 horizontalAccuracy=0.0, verticalAccuracy=0.0, altitude=0.0):
        self.latitude = latitude
        self.longitude = longitude
        self.timeStamp = timeStamp
        self.horizontalAccuracy = horizontalAccuracy
        self.verticalAccuracy = verticalAccuracy
        self.altitude = altitude

class FindMyItem:
    def __init__(self, name="", serialNumber="", batteryStatus=None, location=None):
        self.name = name
        self.serialNumber = serialNumber
        self.batteryStatus = batteryStatus
        self.location = location  # ItemLocation

###############################################################################
# Core Logic: Reading Items.data, Sending to Server(s)
###############################################################################

class ItemsDataMonitor:
    """
    Periodically reads `Items.data`, detects changes, sends updates for any
    tag config row that matches the item serial. If an item has multiple rows,
    multiple HTTP requests are made (one per row).
    """
    def __init__(self, config):
        # config is a dict: { "tag_configs": [ {...}, {...} ] }
        self.config = config
        self.poll_interval = 60  # seconds
        self.polling = False

        self.last_items = []  # store old items to detect location changes
        # For displaying last-sent times in the UI
        self.last_sent_timestamps = {}  # serialNumber -> float (time.time())

        # UI references
        self.items_listbox = None  # the Listbox that shows discovered items
        self.item_list = []        # local mirror of items so we know what's in each index

    def start_polling(self, root):
        self.polling = True
        self.poll(root)

    def stop_polling(self):
        self.polling = False

    def poll(self, root):
        if not self.polling:
            return
        self.check_items_data(force_send=False)
        root.after(self.poll_interval * 1000, lambda: self.poll(root))

    def force_refresh(self):
        self.check_items_data(force_send=True)

    def check_items_data(self, force_send=False):
        """
        Reads Items.data, decodes JSON, detects location changes, and sends updates.
        """
        file_path = os.path.join(
            os.path.expanduser("~"),
            "Library", "Caches",
            "com.apple.findmy.fmipcore",
            "Items.data"
        )

        try:
            with open(file_path, "rb") as f:
                raw = f.read()
            data = json.loads(raw)  # Expect a list of item dicts
        except Exception as e:
            print(f"Error reading {file_path}: {e}")

            # show error popup
            error_window = tk.Toplevel()
            error_window.title("Error")
            error_label = tk.Label(error_window, text=f"Error reading {file_path}: {e}\nCheck compatible macOS version.")
            error_label.pack(padx=10, pady=10)
            ok_button = tk.Button(error_window, text="OK", command=error_window.destroy)
            ok_button.pack(pady=(0, 10))
            
            return

        new_items = []
        for d in data:
            name = d.get("name", "")
            serial = d.get("serialNumber", "")
            battery = d.get("batteryStatus", None)
            loc_data = d.get("location", {})

            loc = ItemLocation(
                latitude=loc_data.get("latitude", 0.0),
                longitude=loc_data.get("longitude", 0.0),
                timeStamp=loc_data.get("timeStamp", 0.0),
                horizontalAccuracy=loc_data.get("horizontalAccuracy", 0.0),
                verticalAccuracy=loc_data.get("verticalAccuracy", 0.0),
                altitude=loc_data.get("altitude", 0.0)
            )
            item = FindMyItem(name, serial, battery, loc)
            new_items.append(item)

        # Check changes and send
        for item in new_items:
            if self.location_has_changed(item) or force_send:
                # Send one request per config row that has matching serial
                self.send_item_location_to_all_configs(item)

        self.last_items = new_items
        self.update_items_listbox(new_items)

    def location_has_changed(self, new_item):
        """
        Returns True if new_item's location differs from the old item with the same serial.
        """
        old_item = next((x for x in self.last_items if x.serialNumber == new_item.serialNumber), None)
        if not old_item:
            return True  # brand new
        if not old_item.location or not new_item.location:
            return False
        return (
            old_item.location.timeStamp != new_item.location.timeStamp or
            old_item.location.latitude != new_item.location.latitude or
            old_item.location.longitude != new_item.location.longitude
        )

    def send_item_location_to_all_configs(self, item):
        """
        Sends the location update to *every* config entry that has matching `serial`.
        i.e., you can have multiple rows for the same serial -> multiple requests.
        """
        item_serial = item.serialNumber
        matching_rows = [row for row in self.config.get("tag_configs", []) if row.get("serial") == item_serial]

        if not matching_rows:
            # No config row for this item
            return

        for row in matching_rows:
            self.send_item_location(item, row)

    def send_item_location(self, item, row):
        """
        Sends location with row['server_url'] and row['api_key'].
        """
        loc = item.location
        if not loc:
            print(f"No location for {item.serialNumber}, skipping send.")
            return
        server_url = row.get("server_url", "")
        api_key = row.get("api_key", "")
        if not server_url:
            print(f"No server_url for item {item.serialNumber} in row {row}, skipping.")
            return

        # Append ?api_key=... to the server_url
        parsed = urlparse(server_url)
        qdict = parse_qs(parsed.query)
        qdict["api_key"] = [api_key]
        new_query = urlencode(qdict, doseq=True)
        final_url = urlunparse(parsed._replace(query=new_query))

        # Build the JSON
        payload = {
            "gps_data": [
                {
                    "timestamp": str(loc.timeStamp),
                    "latitude": loc.latitude,
                    "longitude": loc.longitude,
                    "horizontal_accuracy": loc.horizontalAccuracy,
                    "altitude": loc.altitude,
                    "vertical_accuracy": loc.verticalAccuracy,
                    "heading": 0,
                    "heading_accuracy": 0,
                    "speed": 0,
                    "speed_accuracy": 0
                }
            ]
        }

        try:
            r = requests.post(final_url, json=payload, timeout=10)
            if r.status_code == 200:
                print(f"Location sent for serial={item.serialNumber} to {server_url} OK.")
                self.last_sent_timestamps[item.serialNumber] = time.time()
            else:
                print(f"HTTP {r.status_code} for serial={item.serialNumber} to {server_url}: {r.text}")
        except Exception as e:
            print(f"Error sending location for {item.serialNumber} to {server_url}: {e}")

    ###########################################################################
    # UI Logic for the "Tracked Items" Listbox
    ###########################################################################

    def set_items_listbox(self, lb):
        """
        Assign the Tkinter Listbox that displays discovered items.
        We'll populate it and handle double-click to add config rows.
        """
        self.items_listbox = lb
        self.items_listbox.bind("<Double-Button-1>", self.on_item_double_click)

    def update_items_listbox(self, new_items):
        """Refresh the listbox with new_items. Show name, serial, last update time."""
        self.item_list = new_items[:]  # keep a local copy
        if not self.items_listbox:
            return
        self.items_listbox.delete(0, tk.END)
        for itm in new_items:
            txt = self.format_item_listbox_entry(itm)
            self.items_listbox.insert(tk.END, txt)

    def format_item_listbox_entry(self, item):
        """
        "Name (Serial): Last Update: YYYY-MM-DD HH:MM:SS or 'None'"
        """
        last_t = self.last_sent_timestamps.get(item.serialNumber)
        if last_t:
            t_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(last_t))
            return f"{item.name} ({item.serialNumber}) - Last Update: {t_str}"
        else:
            return f"{item.name} ({item.serialNumber}) - Last Update: None"

    def on_item_double_click(self, event):
        """
        Called when user double-clicks an item in the listbox.
        -> Add a new config row for that item’s serial.
        """
        if not self.items_listbox:
            return
        idxs = self.items_listbox.curselection()
        if not idxs:
            return
        index = idxs[0]
        if index >= len(self.item_list):
            return
        clicked_item = self.item_list[index]
        # Insert a new config row with default empty server_url/api_key
        entry = {
            "serial": clicked_item.serialNumber,
            "server_url": "",
            "api_key": ""
        }
        self.config["tag_configs"].append(entry)
        # Rebuild the tag config table
        build_tag_table(tag_table_frame, self.config)
        # Optionally auto-save so user sees it right away
        # but let's not auto-save to avoid confusion. They can "Save & Refresh" when done.

###############################################################################
# Tkinter UI
###############################################################################

def build_main_ui(root, config, monitor):
    root.title("WayPointDB AirTag Integration")

    # Row 1: List of tracked items
    items_frame = tk.LabelFrame(root, text="Tracked Items (double-click to add config)")
    items_frame.pack(fill="both", expand=True, padx=10, pady=(10,5))

    listbox = tk.Listbox(items_frame, height=10)
    listbox.pack(fill="both", expand=True, padx=10, pady=10)
    monitor.set_items_listbox(listbox)

    # Row 2: Tag-Specific Config Table
    tags_frame = tk.LabelFrame(root, text="Tag-Specific Configurations", padx=10, pady=10)
    tags_frame.pack(fill="x", padx=10, pady=5)

    # We'll keep a reference so the monitor can rebuild after a double-click
    global tag_table_frame
    tag_table_frame = tk.Frame(tags_frame)
    tag_table_frame.pack(fill="x", expand=True)

    build_tag_table(tag_table_frame, config)

    # Row 3: Buttons
    bottom_frame = tk.Frame(root)
    bottom_frame.pack(fill="x", padx=10, pady=(0,10))

    def save_and_refresh():
        # Collect from table
        collect_tag_table_into_config(tag_table_frame, config)
        save_config(config)
        monitor.force_refresh()

    btn_save = tk.Button(bottom_frame, text="Save & Refresh", command=save_and_refresh)
    btn_save.pack(side="left")

    btn_force = tk.Button(bottom_frame, text="Force Refresh Now", command=monitor.force_refresh)
    btn_force.pack(side="left", padx=10)

def build_tag_table(frame, config):
    """
    Clear and rebuild the config table from config["tag_configs"].
    Each row: serial, server_url, api_key, [Delete]
    """
    for child in frame.winfo_children():
        child.destroy()

    # Header
    header = tk.Frame(frame)
    header.pack(fill="x", pady=(0,5))
    tk.Label(header, text="Serial", width=20).pack(side="left", padx=5)
    tk.Label(header, text="Server URL", width=30).pack(side="left", padx=5)
    tk.Label(header, text="API Key", width=20).pack(side="left", padx=5)
    tk.Label(header, text="Actions", width=8).pack(side="left", padx=5)

    for row in config["tag_configs"]:
        row_frame = tk.Frame(frame)
        row_frame.pack(fill="x", pady=2)

        ent_serial = tk.Entry(row_frame, width=20)
        ent_serial.pack(side="left", padx=5)
        ent_serial.insert(0, row.get("serial", ""))

        ent_server = tk.Entry(row_frame, width=30)
        ent_server.pack(side="left", padx=5)
        ent_server.insert(0, row.get("server_url", ""))

        ent_api = tk.Entry(row_frame, width=20)
        ent_api.pack(side="left", padx=5)
        ent_api.insert(0, row.get("api_key", ""))

        def delete_this(r=row):
            config["tag_configs"].remove(r)
            build_tag_table(frame, config)

        btn_del = tk.Button(row_frame, text="Delete", command=delete_this)
        btn_del.pack(side="left", padx=5)

def collect_tag_table_into_config(frame, config):
    """
    Reads the user-edited textfields back into config["tag_configs"].
    """
    # Rebuild a new list from scratch
    new_list = []
    # skip first child (header)
    children = frame.winfo_children()
    if len(children) < 2:
        config["tag_configs"] = []
        return

    for row_frame in children[1:]:
        row_kids = row_frame.winfo_children()
        if len(row_kids) < 4:
            continue
        ent_serial = row_kids[0]
        ent_server = row_kids[1]
        ent_api = row_kids[2]
        serial_val = ent_serial.get().strip()
        server_val = ent_server.get().strip()
        api_val = ent_api.get().strip()

        # If user left serial empty, skip
        if serial_val:
            new_list.append({
                "serial": serial_val,
                "server_url": server_val,
                "api_key": api_val
            })

    config["tag_configs"] = new_list

###############################################################################
# Main
###############################################################################

if __name__ == "__main__":
    config = load_config()

    root = tk.Tk()
    monitor = ItemsDataMonitor(config)

    build_main_ui(root, config, monitor)

    # Start polling
    monitor.start_polling(root)

    root.mainloop()
    monitor.stop_polling()
