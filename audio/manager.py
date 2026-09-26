"""
Audio — chiptune music + SFX synthesized at runtime (no external files).
"""
from __future__ import annotations
import os
import math
import numpy as np
import pygame

SAMPLE_RATE = 22050

# Note = (freq, duration); 0 = pause.
INTRO_TUNE = [
    (392, 0.32), (0, 0.06), (330, 0.32), (0, 0.06), (392, 0.5), (294, 0.32), (0, 0.12),
    (330, 0.32), (0, 0.06), (262, 0.32), (0, 0.06), (330, 0.5), (392, 0.32), (0, 0.12),
    (440, 0.32), (0, 0.06), (392, 0.32), (0, 0.06), (330, 0.5), (392, 0.55), (0, 0.22),
]

# Menú (calmada, circular, relajada)
MENU_TUNE = [
    (523, 0.36), (0, 0.08), (659, 0.36), (0, 0.08), (784, 0.55), (0, 0.12),
    (659, 0.36), (0, 0.08), (523, 0.36), (0, 0.08), (587, 0.55), (0, 0.12),
    (698, 0.36), (0, 0.08), (587, 0.36), (0, 0.08), (523, 0.55), (0, 0.24),
]

# 5 level tunes, gentle progression
LEVEL_TUNES = [
    [
        (262, 0.32), (330, 0.32), (392, 0.55), (0, 0.12),
        (392, 0.32), (330, 0.32), (262, 0.65), (0, 0.22),
    ],
    [
        (294, 0.32), (370, 0.32), (440, 0.55), (0, 0.12),
        (440, 0.32), (370, 0.32), (294, 0.65), (0, 0.22),
    ],
    [
        (262, 0.26), (330, 0.26), (392, 0.26), (523, 0.44), (0, 0.12),
        (392, 0.26), (330, 0.26), (294, 0.55), (0, 0.22),
    ],
    [
        (294, 0.26), (370, 0.26), (440, 0.26), (587, 0.44), (0, 0.12),
        (440, 0.26), (370, 0.26), (330, 0.55), (0, 0.22),
    ],
    [
        (262, 0.26), (330, 0.26), (392, 0.26), (523, 0.26), (659, 0.48), (0, 0.12),
        (523, 0.26), (392, 0.26), (330, 0.62), (0, 0.25),
    ],
]


def _synthesize(notes, volume=0.5, waveform="square"):
    """Render notes to a numpy chiptune array."""
    total_samples = 0
    for freq, dur in notes:
        total_samples += int(dur * SAMPLE_RATE)

    audio = np.zeros(total_samples, dtype=np.float32)
    write_pos = 0

    for freq, dur in notes:
        n = int(dur * SAMPLE_RATE)
        if n <= 0 or freq == 0:
            write_pos += n
            continue
        t = np.arange(n) / SAMPLE_RATE
        phase = 2 * math.pi * freq * t

        if waveform == "square":
            wave = np.sign(np.sin(phase))
        else:
            wave = np.sin(phase)

        attack = min(int((0.01 if waveform == "square" else 0.005) * SAMPLE_RATE), n)
        release = min(int((0.02 if waveform == "square" else 0.03) * SAMPLE_RATE), n)
        env = np.ones(n)
        if attack > 0:
            env[:attack] = np.linspace(0, 1, attack)
        if release > 0:
            env[-release:] = np.linspace(1, 0, release)

        end = min(write_pos + n, total_samples)
        audio[write_pos:end] += wave[: end - write_pos] * env[: end - write_pos] * volume
        write_pos += n

    mx = np.abs(audio).max()
    if mx > 0:
        audio = audio / mx * 0.7
    return (audio * 32767).astype(np.int16)


class AudioManager:
    def __init__(self):
        self.enabled = True
        self.current_track = None
        self._music_volume = 0.2
        self._sfx_volume = 0.2
        if pygame.mixer.get_init() is None:
            try:
                pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=1)
            except pygame.error:
                self.enabled = False

        self._music_dir = self._resolve_music_dir()
        try:
            os.makedirs(self._music_dir, exist_ok=True)
        except OSError:
            # Sistema de archivos de solo lectura (AppImage, /usr/share...):
            # se cae a una carpeta temporal de escritura.
            import tempfile
            self._music_dir = os.path.join(
                tempfile.gettempdir(), "pc-repair-challenge")
            os.makedirs(self._music_dir, exist_ok=True)

        self.tracks = {}
        self.sounds = {}
        self._ensure_track("intro", INTRO_TUNE, waveform="sine")
        self._ensure_track("menu", MENU_TUNE, waveform="sine")
        for i, tune in enumerate(LEVEL_TUNES):
            self._ensure_track(f"level{i}", tune, waveform="sine")
        self._ensure_sound("click", 880, 0.06)
        self._ensure_sound("place", 440, 0.1)
        self._ensure_sound("success", 1320, 0.15)
        self._ensure_sound("error", 180, 0.2)

    def _resolve_music_dir(self):
        """Carpeta donde se cachean las pistas sintetizadas.

        Se respeta PC_REPAIR_HOME; si no, se usa assets/music junto al juego
        (repositorio). La escritura ocurre igualmente en modo lectura, asi que
        __init__ cae a un directorio temporal si esa carpeta no es escribible.
        """
        home = os.environ.get("PC_REPAIR_HOME")
        if home:
            return os.path.join(home, "music")
        return os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "assets", "music")

    def _path(self, name, ext="wav"):
        return os.path.join(self._music_dir, f"{name}.{ext}")

    def _ensure_track(self, name, notes, waveform="square"):
        p = self._path(name)
        if not os.path.exists(p):
            try:
                data = _synthesize(notes, waveform=waveform)
                wav = np.vstack([data]).astype(np.int16)
                from scipy.io import wavfile
                wavfile.write(p, SAMPLE_RATE, wav)
            except Exception:
                # Fallback manual WAV write sin scipy
                try:
                    self._write_wav_manual(p, data)
                except Exception:
                    return
        try:
            self.tracks[name] = pygame.mixer.Sound(p)
        except Exception:
            pass

    def _write_wav_manual(self, path, samples):
        import struct
        n = len(samples)
        data = samples.tobytes()
        byte_rate = SAMPLE_RATE * 2
        with open(path, "wb") as f:
            f.write(b"RIFF")
            f.write(struct.pack("<I", 36 + len(data)))
            f.write(b"WAVE")
            f.write(b"fmt ")
            f.write(struct.pack("<IHHIIHH", 16, 1, 1, SAMPLE_RATE, byte_rate, 2, 16))
            f.write(b"data")
            f.write(struct.pack("<I", len(data)))
            f.write(data)

    def _ensure_sound(self, name, freq, dur, volume=0.35):
        p = self._path(name)
        if not os.path.exists(p):
            try:
                samples = _synthesize([(freq, dur)])
                self._write_wav_manual(p, samples)
            except Exception:
                return
        try:
            snd = pygame.mixer.Sound(p)
            snd.set_volume(volume)
            self.sounds[name] = snd
        except Exception:
            pass

    def play_music(self, name):
        if not self.enabled:
            return
        try:
            snd = self.tracks.get(name)
            if snd is None:
                return
            if self.current_track == name:
                return
            if pygame.mixer.get_busy():
                pygame.mixer.stop()
            if self.enabled:
                vol = getattr(self, '_music_volume', 0.5)
                snd.set_volume(vol)
                snd.play(-1)
                self.current_track = name
        except Exception:
            pass

    def play_level(self, idx):
        self.play_music(f"level{idx}")

    def set_sfx_volume(self, vol):
        self._sfx_volume = max(0.0, min(1.0, vol))
        try:
            for snd in self.sounds.values():
                snd.set_volume(self._sfx_volume)
        except Exception:
            pass

    def play_sound(self, name):
        if not self.enabled:
            return
        try:
            snd = self.sounds.get(name)
            if snd is not None:
                snd.play()
        except Exception:
            pass

    def toggle_mute(self):
        self.enabled = not self.enabled
        if not self.enabled:
            try:
                pygame.mixer.stop()
            except Exception:
                pass
        return self.enabled

    def set_music_volume(self, vol):
        self._music_volume = max(0.0, min(1.0, vol))
        try:
            if pygame.mixer.get_init():
                pygame.mixer.music.set_volume(self._music_volume)
                # Also set volume on currently playing channel
                for snd in self.tracks.values():
                    try:
                        snd.set_volume(self._music_volume)
                    except Exception:
                        pass
        except Exception:
            pass
