"""Bounded, free config storage. The native client validates executable semantics before import."""
import json
import math

PROFILE_FIELDS = set("schema name game platform color cover aim devices movement input_routing hardware arbitration input_mode controller graph bindings physical_button_bindings analog_bindings groups group_names output actions calibration calibration_origin calibration_measurements mapping".split())

def validate_config(package):
    if not isinstance(package, dict) or set(package) != {"schema", "license", "author", "description", "config"}:
        raise ValueError("Only a free config package is accepted; pricing fields are forbidden.")
    if type(package["schema"]) is not int or package["schema"] != 1 or package["license"] != "CC0-1.0":
        raise ValueError("Only schema 1, free CC0 config packages are accepted.")
    for name, limit, required in (("author", 60, True), ("description", 2000, False)):
        text = package[name]
        if not isinstance(text, str) or len(text.encode()) > limit or (required and (not text.strip() or any(ord(c) < 32 for c in text))):
            raise ValueError(f"Invalid {name}.")
    config = package["config"]
    if not isinstance(config, dict) or not {"schema", "name", "game", "aim", "graph", "bindings", "output"} <= config.keys() or not config.keys() <= PROFILE_FIELDS:
        raise ValueError("Invalid config fields.")
    if type(config["schema"]) is not int or config["schema"] != 1:
        raise ValueError("Unsupported config schema.")
    if not isinstance(config["aim"], dict) or not isinstance(config.get("calibration", {}), dict):
        raise ValueError("Invalid aim or calibration object.")
    if not isinstance(config["output"], str) or config["output"] not in ("Simulator", "VirtualXbox", "PlayStation", "XboxRemote", "MakcuV4", "TitanTwo", "Makxd"):
        raise ValueError("Unknown output connection.")
    for field in ("name", "game"):
        if not isinstance(config[field], str) or not config[field].strip() or len(config[field].encode()) > 160:
            raise ValueError(f"Invalid config {field}.")
    if config.get("input_mode", "Hybrid") not in ("MouseKeyboard", "Controller", "Hybrid"):
        raise ValueError("Invalid input mode.")
    for field in ("bindings", "physical_button_bindings", "analog_bindings", "groups", "actions"):
        if field in config and (not isinstance(config[field], list) or len(config[field]) > 256):
            raise ValueError(f"Invalid {field} list.")
    count = 0
    def bounded(value, depth=0):
        nonlocal count
        count += 1
        if depth > 20 or count > 100000:
            raise ValueError("Config structure is too large.")
        if isinstance(value, dict):
            if len(value) > 256 or any(len(k.encode()) > 160 for k in value):
                raise ValueError("Config object exceeds limits.")
            for child in value.values():
                bounded(child, depth + 1)
        elif isinstance(value, list):
            if len(value) > 4096:
                raise ValueError("Config array exceeds limits.")
            for child in value:
                bounded(child, depth + 1)
        elif isinstance(value, str):
            if len(value.encode()) > 4096:
                raise ValueError("Config text exceeds limits.")
        elif type(value) in (float, int) and not math.isfinite(value):
            raise ValueError("Config numbers must be finite.")
    cover = config.get("cover")
    if cover is not None:
        if not isinstance(cover, dict) or set(cover) != {"png"} or not isinstance(cover["png"], list) or not 33 <= len(cover["png"]) <= 600000 or any(type(b) is not int or not 0 <= b <= 255 for b in cover["png"]):
            raise ValueError("Invalid config cover.")
        data = bytes(cover["png"])
        if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR" or not 1 <= int.from_bytes(data[16:20], "big") <= 720 or not 1 <= int.from_bytes(data[20:24], "big") <= 180:
            raise ValueError("Config cover must be a PNG no larger than 720 by 180.")
    bounded({key: value for key, value in config.items() if key != "cover"})
    return package

def listing(row):
    package = json.loads(row["payload"])
    config = package["config"]
    return {"id": row["id"], "name": config["name"], "game": config["game"], "author": package["author"], "input_mode": config.get("input_mode", "Hybrid"), "calibrated": bool(config.get("calibration", {}).get("measured", False))}
