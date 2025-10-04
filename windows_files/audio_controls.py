from ctypes import cast, POINTER
from comtypes import CoInitialize, CoUninitialize
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
import subprocess
import pyautogui
import os
import json
import threading

# A lock to prevent race conditions when writing to fx_state.json
FX_STATE_LOCK = threading.Lock()

def set_master_volume(level):
    try:
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, 1, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        volume.SetMasterVolumeLevelScalar(level, None)
    except Exception: pass

def set_master_mute(is_muted):
    try:
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, 1, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        volume.SetMute(is_muted, None)
    except Exception: pass

def set_group_volume(app_names, level):
    try:
        sessions = AudioUtilities.GetAllSessions()
        for session in sessions:
            if session.Process and session.Process.name() in app_names:
                session.SimpleAudioVolume.SetMasterVolume(level, None)
    except Exception: pass

def set_group_mute(app_names, is_muted):
    try:
        sessions = AudioUtilities.GetAllSessions()
        for session in sessions:
            if session.Process and session.Process.name() in app_names:
                session.SimpleAudioVolume.SetMute(is_muted, None)
    except Exception: pass

def set_mic_mute(is_muted):
    try:
        # This uses pycaw to mute the default microphone
        mic = AudioUtilities.GetMicrophone()
        interface = mic.Activate(IAudioEndpointVolume._iid_, 1, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        volume.SetMute(is_muted, None)
    except Exception: pass

# New function to control microphone volume with nircmd
def set_mic_volume(level):
    try:
        # nircmd volume is 0-65535, so we scale the 0.0-1.0 value
        volume_level = int(float(level) * 65535)
        # Using "default_record" for compatibility with modern Windows
        subprocess.run(f"nircmd.exe setsysvolume {volume_level} default_record", shell=True, check=False, creationflags=0x08000000)
    except Exception as e:
        print(f"Error setting mic volume: {e}")


def send_media_key(key):
    try: pyautogui.press(key)
    except Exception: pass

def launch_application(executable_name):
    try: os.startfile(executable_name)
    except Exception: pass

def handle_command(command, config):
    CoInitialize()
    try:
        action = command.get("action")
        
        if action == "set_master_volume": set_master_volume(float(command.get("level", 0)))
        elif action == "set_master_mute": set_master_mute(bool(command.get("is_muted")))
        elif action == "set_group_volume":
            idx = int(command.get("group_index"))
            if 0 <= idx < len(config["audio_mixer_groups"]):
                set_group_volume(config["audio_mixer_groups"][idx]["apps"], float(command.get("level")))
        elif action == "set_group_mute":
            idx = int(command.get("group_index"))
            if 0 <= idx < len(config["audio_mixer_groups"]):
                set_group_mute(config["audio_mixer_groups"][idx]["apps"], bool(command.get("is_muted")))
        elif action == "set_mic_mute": set_mic_mute(bool(command.get("is_muted")))
        elif action == "set_mic_volume": set_mic_volume(command.get("value")) # Handle new action
        elif action == "load_voice_preset":
            idx = int(command.get("preset_index"))
            if 0 <= idx < len(config["voice_presets"]):
                with FX_STATE_LOCK:
                    with open("fx_state.json", 'w') as f: json.dump(config["voice_presets"][idx]["values"], f)
        elif action == "set_voice_fx":
            with FX_STATE_LOCK:
                # Read, update, and write the state file safely
                state = {}
                try:
                    with open("fx_state.json", 'r') as f: state = json.load(f)
                except (FileNotFoundError, json.JSONDecodeError): pass
                state[command.get("fx_name")] = float(command.get("value"))
                with open("fx_state.json", 'w') as f: json.dump(state, f)
        elif action == "media_control": send_media_key(command.get("key"))
        elif action == "run_stream_deck_action": launch_application(command.get("executable"))
    finally:
        CoUninitialize()

def update_full_state(state_dict, config):
    CoInitialize()
    try:
        master_vol_interface = AudioUtilities.GetSpeakers().Activate(IAudioEndpointVolume._iid_, 1, None)
        master_volume = cast(master_vol_interface, POINTER(IAudioEndpointVolume))
        state_dict["audio"]["master"]["level"] = master_volume.GetMasterVolumeLevelScalar()
        state_dict["audio"]["master"]["muted"] = bool(master_volume.GetMute())

        sessions = {s.Process.name(): s for s in AudioUtilities.GetAllSessions() if s.Process}
        groups = config.get("audio_mixer_groups", [])
        
        state_dict["audio"]["groups"] = []
        for group in groups:
            active_session = next((sessions[app] for app in group["apps"] if app in sessions), None)
            if active_session:
                state_dict["audio"]["groups"].append({
                    "level": active_session.SimpleAudioVolume.GetMasterVolume(),
                    "muted": bool(active_session.SimpleAudioVolume.GetMute())
                })
            else:
                state_dict["audio"]["groups"].append({"level": -1, "muted": False})
        
        # Get microphone state using pycaw
        mic_vol_interface = AudioUtilities.GetMicrophone().Activate(IAudioEndpointVolume._iid_, 1, None)
        mic_volume = cast(mic_vol_interface, POINTER(IAudioEndpointVolume))
        state_dict["voice"]["mic_mute"] = bool(mic_volume.GetMute())
        state_dict["voice"]["mic_level"] = mic_volume.GetMasterVolumeLevelScalar() # Add mic level to state

        if os.path.exists("fx_state.json"):
            with FX_STATE_LOCK:
                with open("fx_state.json", 'r') as f: state_dict["voice"]["fx"] = json.load(f)
        
        current_fx = state_dict["voice"].get("fx", {})
        state_dict["voice"]["active_preset"] = -1 # Default to no preset
        for i, preset in enumerate(config.get("voice_presets", [])):
            if preset.get("values") == current_fx:
                state_dict["voice"]["active_preset"] = i
                break
    except Exception: pass
    finally:
        CoUninitialize()

