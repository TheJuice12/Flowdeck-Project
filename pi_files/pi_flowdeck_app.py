import kivy
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.widget import Widget
from kivy.uix.togglebutton import ToggleButton
from kivy.properties import ListProperty, NumericProperty, BooleanProperty, StringProperty
from kivy.core.window import Window
from kivy.input.motionevent import MotionEvent
from kivy.animation import Animation
from kivy.clock import Clock
import json
import os
import sys
import threading
import requests
import time
import math

class RootWidget(FloatLayout): pass
class AudioMixerPage(GridLayout): pass
class VoiceFXPage(GridLayout): pass
class StreamDeckPage(GridLayout): pass
class MediaControlPage(GridLayout): pass 
class SliderColumn(BoxLayout): pass
class FXSlider(BoxLayout): pass


class FlowDeckApp(App):
    group_names = ListProperty(['', '', ''])
    preset_names = ListProperty(['P1', 'P2', 'P3'])
    stream_deck_buttons = ListProperty([])
    
    master_level = NumericProperty(0)
    master_muted = BooleanProperty(False)
    group_levels = ListProperty([0,0,0])
    group_mutes = ListProperty([False, False, False])
    mic_muted = BooleanProperty(False)
    active_preset = NumericProperty(0)
    fx_knobs = ListProperty([0.5, 0.0, 1.0, 0.0])
    
    _running = True

    def build(self):
        Window.fullscreen = 'auto'
        Window.show_cursor = False
        Window.bind(on_touch_down=self._on_touch_down, on_touch_up=self._on_touch_up)
        
        self.pi_config = self.load_pi_config()
        if not self.pi_config:
            sys.exit("Could not load pi-config.json")

        self.base_url = f"http://{self.pi_config['windows_hostname']}:5000"
        
        threading.Thread(target=self.state_polling_loop, daemon=True).start()
        
        return RootWidget()

    def on_start(self):
        threading.Thread(target=self.get_config_from_server, daemon=True).start()

    def on_stop(self):
        self._running = False
        Window.unbind(on_touch_down=self._on_touch_down, on_touch_up=self._on_touch_up)

    def _on_touch_down(self, window, touch):
        touch.ud['start_y'] = touch.y

    def _on_touch_up(self, window, touch):
        if 'start_y' in touch.ud:
            dy = touch.y - touch.ud['start_y']
            # If the touch started at the bottom edge and swiped up, stop the app
            if touch.ud['start_y'] < 60 and dy > 150:
                self.stop()

    def load_pi_config(self):
        try:
            config_path = os.path.join(os.path.dirname(__file__), 'pi-config.json')
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"CRITICAL ERROR loading pi-config.json: {e}")
            return None

    def get_config_from_server(self):
        try:
            response = requests.get(f"{self.base_url}/config", timeout=3)
            response.raise_for_status()
            config = response.json()
            Clock.schedule_once(lambda dt: self._populate_ui_from_config(config))
        except requests.exceptions.RequestException as e:
            print(f"Failed to get config from server: {e}")

    def state_polling_loop(self):
        while self._running:
            try:
                response = requests.get(f"{self.base_url}/state", timeout=1)
                if response.status_code == 200:
                    state = response.json()
                    Clock.schedule_once(lambda dt, s=state: self._update_ui_from_state(s))
            except requests.exceptions.RequestException:
                pass 
            time.sleep(0.001)

    def send_control_command(self, payload):
        threading.Thread(target=self._send_control_command_thread, args=(payload,), daemon=True).start()

    def _send_control_command_thread(self, payload):
        try:
            requests.post(f"{self.base_url}/control", json=payload, timeout=1)
        except requests.exceptions.RequestException as e:
            print(f"Failed to send command: {e}")
    
    def _populate_ui_from_config(self, config):
        self.group_names = [g.get('name', 'N/A') for g in config.get('audio_mixer_groups', [])[:3]]
        self.preset_names = [p.get('name', f'P{i+1}') for i, p in enumerate(config.get('voice_presets', [])[:3])]
        self.stream_deck_buttons = config.get('stream_deck_buttons', [])
    
    def _update_ui_from_state(self, state):
        self.master_level = state.get('audio',{}).get('master',{}).get('level', 0)
        self.master_muted = state.get('audio',{}).get('master',{}).get('muted', False)
        
        group_states = state.get('audio', {}).get('groups', [])
        if len(group_states) == len(self.group_levels):
            self.group_levels = [g.get('level', 0) if g.get('level', -1) != -1 else self.group_levels[i] for i, g in enumerate(group_states)]
            self.group_mutes = [g.get('muted', False) for g in group_states]

        voice_state = state.get('voice', {})
        self.mic_muted = voice_state.get('mic_mute', False)
        self.active_preset = voice_state.get('active_preset', 0)
        
        fx = voice_state.get('fx',{})
        self.fx_knobs = [
            fx.get('pitch', 0.5), 
            fx.get('reverb', 0),
            voice_state.get('mic_level', 1.0), 
            fx.get('echo', 0)
        ]

    def set_master_level(self, val): self.send_control_command({"action": "set_master_volume", "level": val})
    def set_master_mute(self): self.send_control_command({"action": "set_master_mute", "is_muted": not self.master_muted})
    def set_group_level(self, idx, val): self.send_control_command({"action": "set_group_volume", "group_index": idx, "level": val})
    def set_group_mute(self, idx): self.send_control_command({"action": "set_group_mute", "group_index": idx, "is_muted": not self.group_mutes[idx]})
    def set_mic_mute(self): self.send_control_command({"action": "set_mic_mute", "is_muted": not self.mic_muted})
    def load_preset(self, idx): self.send_control_command({"action": "load_voice_preset", "preset_index": idx})
    
    def set_fx(self, name, val):
        if name == 'mic_volume':
            payload = {"action": "set_mic_volume", "value": val}
        else:
            payload = {"action": "set_voice_fx", "fx_name": name, "value": val}
        self.send_control_command(payload)

    def media_control(self, key): self.send_control_command({"action": "media_control", "key": key})
    def stream_deck_action(self, exe): self.send_control_command({"action": "run_stream_deck_action", "executable": exe})

if __name__ == '__main__':
    FlowDeckApp().run()


