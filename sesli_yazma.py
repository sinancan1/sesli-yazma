# -*- coding: utf-8 -*-
"""Sesli Yazma — Windows genelinde çalışan Google ses tanıma dikte programı.

F9'a basın; konuştuğunuz her parça Google'ın ücretsiz ses tanıma servisiyle
metne çevrilip o anda **odakta olan** pencereye (Word, tarayıcı, Notepad,
sohbet uygulaması, Excel…) gerçek klavye girişi olarak yazılır.

- Metin kutusu yok; kopyala-yapıştır gerekmez.
- Uygulama uzaktan hiçbir veri toplamaz; konuşma yalnızca tanıma için Google'a gönderilir.
- Sesli komutlar: "nokta", "virgül", "yeni satır", "gönder/enter", "sil",
  "geri al", "tab" vb. ilgili işarete/tuşa çevrilir.
- Sağ üstteki mini kart durumunuzu gösterir; odağı çalmaz.

Kurulum: README.md  ·  Çalıştırma:  python sesli_yazma.py
"""

from __future__ import annotations

import ctypes
import queue
import re
import threading
import time
import tkinter as tk
from collections import deque
from math import log10
from tkinter import ttk

import numpy as np
import sounddevice as sd
import speech_recognition as sr
from pynput import keyboard as pynput_kb

# ── Sabit ayarlar ────────────────────────────────────────────────────────────
SAMPLE_RATE = 16000            # Google'a gönderilecek kayıt hızı (Hz)
CHANNELS = 1
SAMPLE_WIDTH = 2               # int16
BLOCK_MS = 100
BLOCK_SIZE = SAMPLE_RATE * BLOCK_MS // 1000
BLOCK_BYTES = BLOCK_SIZE * CHANNELS * SAMPLE_WIDTH

PRE_BLOCKS = 3                 # konuşma öncesi tutulan ön tampon
SILENCE_BLOCKS = 7             # 700 ms sessizlik → parça bitti
MIN_SPEECH_BLOCKS = 1          # en az 100 ms konuşma (kısa kelimeleri de yakala)
MAX_BLOCKS = 190               # en fazla ~19 s'de bir gönderilir
FAST_SILENCE_BLOCKS = 4       # "Hızlı mod" açıkken 400 ms

HOTKEY = pynput_kb.Key.f9      # global kısayol (örn. pynput_kb.Key.f8)
TRAILING_SPACE = True          # her parçadan sonra boşluk bırak

LANGS = {
    "Türkçe": ("tr-TR", "tr"),
    "English (US)": ("en-US", "en"),
    "English (UK)": ("en-GB", "en"),
    "Deutsch": ("de-DE", "de"),
    "Français": ("fr-FR", "fr"),
    "Español": ("es-ES", "es"),
    "Italiano": ("it-IT", "it"),
    "Русский": ("ru-RU", "ru"),
    "العربية": ("ar-SA", "ar"),
    "日本語": ("ja-JP", "ja"),
}

SENSITIVITY_LEVELS = {
    "Düşük": 3.5,
    "Orta": 2.8,
    "Yüksek": 2.2,
    "Çok yüksek": 1.6,
}
# Arayüz dili seçici: konuşma dili Türkçe ise Türkçe, aksi halde İngilizce
UI_LANGS = ["Türkçe", "English"]

_STRINGS = {
    "tr": {
        "title": "Sesli Yazma · Google",
        "status_closed": "● Kapalı — F9'a basıp konuşun",
        "status_stopped": "● Komut bekleniyor — 'başlat' deyin veya F9'a basın",
        "status_stopping": "■ Durduruluyor…",
        "status_listening": "● Dinliyor… konuşabilirsiniz",
        "status_mic_switching": "● Mikrofon değiştiriliyor…",
        "status_speech_detected": "● Konuşma algılandı…",
        "status_listening2": "● Dinliyor…",
        "status_sending": "◇ Google'a gönderiliyor…",
        "status_silent": "◇ (sessiz parça, atlandı)",
        "status_not_understood": "◇ Bu parça anlaşılamadı",
        "status_google_error": "◇ Google hizmetine ulaşılamadı: {exc}",
        "status_rec_error": "◇ Tanıma hatası: {exc}",
        "status_recognized": "◇ Tanındı: {preview}",
        "status_typed": "● Yazıldı ✓",
        "status_empty": "◇ (boş parça)",
        "status_type_error": "◇ Yazma hatası: {exc}",
        "status_fatal_mic": "Mikrofon hatası: {exc}",
        "status_fatal_hotkey": "Kısayol hatası: {exc}",
        "status_stopped_cmd": "● Komut bekleniyor — 'başlat' deyin",
        "status_paused_cmd": "■ Durduruldu (sesli komut)",
        "status_fast_on": "● Hızlı mod açık",
        "status_fast_off": "● Normal mod",
        "status_caps_on": "● BÜYÜK HARF modu açık",
        "status_caps_off": "● küçük harf modu",
        "status_mic_ready": "● Mikrofon hazır",
        "btn_start": "▶ Başlat",
        "btn_stop": "■ Durdur",
        "label_lang": "Dil",
        "label_mic": "Mik",
        "label_sens": "Hass",
        "chk_fast": "Hızlı",
        "help": "F9: başlat/durdur · F10: pencereyi geri getir · Hassasiyet: uzaktan için 'Çok yüksek'",
    },
    "en": {
        "title": "Voice Typing · Google",
        "status_closed": "● Closed — press F9 to start",
        "status_stopped": "● Waiting for command — say 'start' or press F9",
        "status_stopping": "■ Stopping…",
        "status_listening": "● Listening… you can speak",
        "status_mic_switching": "● Switching microphone…",
        "status_speech_detected": "● Speech detected…",
        "status_listening2": "● Listening…",
        "status_sending": "◇ Sending to Google…",
        "status_silent": "◇ (silent segment, skipped)",
        "status_not_understood": "◇ This segment was not understood",
        "status_google_error": "◇ Could not reach Google service: {exc}",
        "status_rec_error": "◇ Recognition error: {exc}",
        "status_recognized": "◇ Recognized: {preview}",
        "status_typed": "● Typed ✓",
        "status_empty": "◇ (empty segment)",
        "status_type_error": "◇ Typing error: {exc}",
        "status_fatal_mic": "Microphone error: {exc}",
        "status_fatal_hotkey": "Hotkey error: {exc}",
        "status_stopped_cmd": "● Waiting for command — say 'start'",
        "status_paused_cmd": "■ Stopped (voice command)",
        "status_fast_on": "● Fast mode on",
        "status_fast_off": "● Normal mode",
        "status_caps_on": "● CAPS mode on",
        "status_caps_off": "● lowercase mode",
        "status_mic_ready": "● Microphone ready",
        "btn_start": "▶ Start",
        "btn_stop": "■ Stop",
        "label_lang": "Lang",
        "label_mic": "Mic",
        "label_sens": "Sens",
        "chk_fast": "Fast",
        "help": "F9: start/stop · F10: restore window · Sensitivity: 'Very high' for distant speech",
    },
}

def _ui_lang(code: str) -> str:
    return "tr" if str(code).lower().startswith("tr") else "en"

def _tr(code: str, key: str, **kw) -> str:
    s = _STRINGS[_ui_lang(code)].get(key, key)
    try:
        return s.format(**kw) if kw else s
    except Exception:
        return s

def _norm(s: str) -> str:
    """Türkçe karakterleri ASCII'ye çevirir (komut eşleştirme için)."""
    return s.lower().strip().translate(str.maketrans("çğıöşü", "cgiosu"))


TEXT_COMMANDS: dict[str, str] = {
    "noktalı virgül": ";",
    "yeni paragraf": "\n\n",
    "yeni satır": "\n",
    "parantez aç": "(",
    "parantez kapa": ")",
    "tırnak aç": '"',
    "tırnak kapa": '"',
    "iki nokta": ":",
    "soru işareti": "?",
    "ünlem işareti": "!",
    "boşluk": " ",
    "virgül": ",",
    "nokta": ".",
    "ünlem": "!",
    "soru": "?",
}

KEY_COMMANDS: dict[str, str] = {
    "gönder": "enter",
    "enter": "enter",
    "tab": "tab",
    "sekme": "tab",
    "sil": "backspace",
    "kelime sil": "ctrl_backspace",
    "geri al": "ctrl_z",
    "tümünü sil": "ctrl_a_delete",
    "hepsini sil": "ctrl_a_delete",
    "escape": "escape",
}

# Programın kendisini yöneten sesli komutlar (yazmak yerine eylem yapar)
CONTROL_COMMANDS: dict[str, str] = {
    "başlat": "start",
    "dinlemeye başla": "start",
    "durdur": "stop",
    "programı durdur": "stop",
    "kapat": "stop",
    "bitir": "stop",
    "hızlı mod": "fast_on",
    "normal mod": "fast_off",
    "büyük harf": "caps_on",
    "küçük harf": "caps_off",
}

# Normalize edilmiş arama tabloları (ASCII varyantlar da eşleşir)
_TEXT_NORM = {_norm(k): v for k, v in TEXT_COMMANDS.items()}
_KEY_NORM = {_norm(k): v for k, v in KEY_COMMANDS.items()}
_CTRL_NORM = {_norm(k): v for k, v in CONTROL_COMMANDS.items()}

def _cmd_variants(cmd: str) -> list[str]:
    n = _norm(cmd)
    return [cmd, n] if n != cmd.lower() else [cmd]

_ALL_COMMANDS: list[str] = sorted(
    [v for cmd in (list(TEXT_COMMANDS) + list(KEY_COMMANDS) + list(CONTROL_COMMANDS))
     for v in _cmd_variants(cmd)],
    key=len, reverse=True
)
_COMMAND_RE = re.compile(
    r"(?i)\b(" + "|".join(re.escape(c) for c in _ALL_COMMANDS) + r")\b"
)


class App(tk.Tk):
    """Mini durum kartı + pencereye klavye yazan dikte motoru."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Sesli Yazma · Google")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        w, h = 470, 138
        try:
            x = max(0, self.winfo_screenwidth() - w - 24)
        except Exception:
            x = 24
        self.geometry(f"{w}x{h}+{x}+28")

        self._ui_q: queue.Queue = queue.Queue()
        self._seg_q: queue.Queue = queue.Queue()
        self._devices: list[tuple[int | None, str]] = []
        self._rec_thread: threading.Thread | None = None
        self._stt_thread: threading.Thread | None = None
        self._rec_device: int | None = None
        self._restart_rec = threading.Event()
        self.running = False
        self._ui_on = False
        self._shutdown = False
        self._lang = LANGS["Türkçe"][0]
        self._t = lambda key, **kw: _tr(self._lang, key, **kw)
        self.title(self._t("title"))
        self._last_hotkey = 0.0
        self._typist = pynput_kb.Controller()
        self.fast_mode = tk.BooleanVar(value=False)
        self.sensitivity = tk.StringVar(value="Yüksek")
        self._caps_mode = False
        self._saved_fg = None
        self._last_external_fg = None
        self._our_hwnd = None

        self._build_ui()
        self._on_lang()
        self._refresh_devices()
        self._rec_device = self._selected_device()
        self.after(80, self._poll)
        self.bind("<Map>", self._on_map)
        threading.Thread(target=self._hotkey_worker, daemon=True).start()
        # Mikrofon her zaman dinler (komut tanıma için); yazma self.running ile kontrol edilir
        self._rec_thread = threading.Thread(target=self._rec_worker, daemon=True)
        self._stt_thread = threading.Thread(target=self._stt_worker, daemon=True)
        self._rec_thread.start()
        self._stt_thread.start()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── Arayüz ───────────────────────────────────────────────────────────
    def _build_ui(self) -> None:
        main = ttk.Frame(self, padding=(10, 8))
        main.pack(fill="both", expand=True)

        self.status_var = tk.StringVar(value=self._t("status_closed"))
        ttk.Label(main, textvariable=self.status_var,
                  font=("Segoe UI", 10, "bold")).pack(anchor="w")

        row1 = ttk.Frame(main)
        row1.pack(fill="x", pady=(6, 2))
        self.start_btn = ttk.Button(row1, text=self._t("btn_start"), width=10, command=self._toggle)
        self.start_btn.pack(side="left")
        self._lbl_lang = ttk.Label(row1, text=f"  {self._t('label_lang')}:")
        self._lbl_lang.pack(side="left")
        self.langvar = tk.StringVar(value="Türkçe")
        self.langbox = ttk.Combobox(row1, textvariable=self.langvar, width=13,
                                    values=list(LANGS), state="readonly")
        self.langbox.pack(side="left", padx=(2, 12))
        self.langvar.trace_add("write", self._on_lang)
        self._lbl_mic = ttk.Label(row1, text=f"{self._t('label_mic')}:")
        self._lbl_mic.pack(side="left")
        self.devvar = tk.StringVar()
        self.devbox = ttk.Combobox(row1, textvariable=self.devvar, width=24, state="readonly")
        self.devbox.pack(side="left", padx=(2, 0))
        self.devvar.trace_add("write", self._on_device)

        row2 = ttk.Frame(main)
        row2.pack(fill="x", pady=(4, 0))
        self.bar = ttk.Progressbar(row2, maximum=100)
        self.bar.pack(side="left", fill="x", expand=True)
        self._chk_fast = ttk.Checkbutton(row2, text=self._t("chk_fast"), variable=self.fast_mode)
        self._chk_fast.pack(side="left", padx=(8, 0))
        self._lbl_sens = ttk.Label(row2, text=f" {self._t('label_sens')}:")
        self._lbl_sens.pack(side="left")
        ttk.Combobox(row2, textvariable=self.sensitivity, values=list(SENSITIVITY_LEVELS),
                     width=10, state="readonly").pack(side="left", padx=(2, 0))

        self._lbl_help = ttk.Label(main, text=self._t("help"),
                  foreground="#666")
        self._lbl_help.pack(anchor="w", pady=(6, 0))

    def _on_lang(self, *_args) -> None:
        val = LANGS.get(self.langvar.get())
        if val:
            self._lang = val[0]
            self._refresh_ui_lang()

    def _refresh_ui_lang(self) -> None:
        try:
            self.title(self._t("title"))
            if self.running:
                self.start_btn.configure(text=self._t("btn_stop"))
            else:
                self.start_btn.configure(text=self._t("btn_start"))
            if hasattr(self, "_lbl_lang"):
                self._lbl_lang.configure(text=f"  {self._t('label_lang')}:")
            if hasattr(self, "_lbl_mic"):
                self._lbl_mic.configure(text=f"{self._t('label_mic')}:")
            if hasattr(self, "_lbl_sens"):
                self._lbl_sens.configure(text=f" {self._t('label_sens')}:")
            if hasattr(self, "_chk_fast"):
                self._chk_fast.configure(text=self._t("chk_fast"))
            if hasattr(self, "_lbl_help"):
                self._lbl_help.configure(text=self._t("help"))
        except Exception:
            pass

    def _refresh_devices(self) -> None:
        self._devices = [(None, "Sistem varsayılanı")]
        try:
            apis = sd.query_hostapis()
            wasapi = [i for i, a in enumerate(apis) if "wasapi" in str(a.get("name", "")).lower()]
            mme = [i for i, a in enumerate(apis) if str(a.get("name", "")).lower() == "mme"]
            prefer = (wasapi or mme or [None])[0]
            for idx, dev in enumerate(sd.query_devices()):
                if int(dev.get("max_input_channels", 0) or 0) <= 0:
                    continue
                if prefer is not None and int(dev.get("hostapi", -1)) != prefer:
                    continue
                self._devices.append((idx, str(dev.get("name", "?")).strip()))
        except Exception:
            pass

        labels = [lbl for _, lbl in self._devices]
        self.devbox["values"] = labels
        if self.devvar.get() not in labels:
            default = None
            try:
                default = sd.default.device[1]
            except Exception:
                pass
            pos = 0
            for p, (idx, _lbl) in enumerate(self._devices):
                if idx is not None and idx == default:
                    pos = p
                    break
            self.devbox.current(pos)

    def _selected_device(self) -> int | None:
        label = self.devvar.get()
        for idx, lbl in self._devices:
            if lbl == label:
                return idx
        return None

    def _on_device(self, *_args) -> None:
        # Cihaz değişikliğini anında uygula: kayıt iş parçacığı yeni cihazla yeniden açılır
        self._rec_device = self._selected_device()
        if self._rec_thread and self._rec_thread.is_alive():
            self._restart_rec.set()
            self.status_var.set(self._t("status_mic_switching"))

    # ── Pencere odağı çalmayan kart ──────────────────────────────────────
    def _on_map(self, _event=None) -> None:
        try:
            if self.state() == "iconic":
                self.deiconify()
            self.lift()
            self.attributes("-topmost", True)
            self.update_idletasks()
        except Exception:
            pass

    # ── Global kısayol ──────────────────────────────────────────────────
    def _hotkey_worker(self) -> None:
        try:
            def on_press(key):
                if key == HOTKEY:
                    now = time.monotonic()
                    if now - self._last_hotkey < 0.5:
                        return
                    self._last_hotkey = now
                    self._ui_q.put({"t": "toggle"})
                elif key == pynput_kb.Key.f10:
                    now = time.monotonic()
                    if now - self._last_hotkey < 0.5:
                        return
                    self._last_hotkey = now
                    self._ui_q.put({"t": "show"})
            with pynput_kb.Listener(on_press=on_press) as listener:
                listener.join()
        except Exception as exc:
            self._ui_q.put({"t": "fatal", "text": self._t("status_fatal_hotkey", exc=exc)})

    # ── Başlat / durdur ─────────────────────────────────────────────────
    def _toggle(self) -> None:
        # Pencere küçültülmüşse geri aç (odağı çalmadan)
        try:
            if self.state() == "iconic":
                self.deiconify()
            self.attributes("-topmost", True)
        except Exception:
            pass
        if self.running:
            self.running = False
            self.status_var.set(self._t("status_stopping"))
            self.start_btn.configure(text=self._t("btn_start"))
        else:
            self._start_listening()
        # Yazma hedefi odakta kalsın: tıklama ile çalınan odağı geri ver
        target = self._last_external_fg
        if target:
            try:
                ctypes.windll.user32.SetForegroundWindow(target)
            except Exception:
                pass

    def _save_foreground(self, _event=None) -> None:
        pass

    def _start_listening(self) -> None:
        if self.running:
            return
        # Pencere küçültülmüşse geri aç
        try:
            if self.state() == "iconic":
                self.deiconify()
            self.lift()
            self.attributes("-topmost", True)
        except Exception:
            pass
        device = self._selected_device()
        self._rec_device = device
        self.running = True
        self._ui_on = True
        self.start_btn.configure(text=self._t("btn_stop"))
        self._push({"t": "status", "text": self._t("status_listening")})

    def _ui_off(self) -> None:
        if not self._ui_on:
            return
        self._ui_on = False
        self.start_btn.configure(text=self._t("btn_start"))
        self.devbox.configure(state="readonly")
        self.status_var.set(self._t("status_stopped"))

    def _push(self, ev: dict) -> None:
        self._ui_q.put(ev)

    # ── Kayıt iş parçacığı ───────────────────────────────────────────────
    def _rec_worker(self) -> None:
        last_status: str = ""

        def say(msg: str) -> None:
            nonlocal last_status
            if msg != last_status:
                last_status = msg
                self._push({"t": "status", "text": msg})

        while not self._shutdown:
            # Cihaz her turda yeniden okunur: mikrofon değişince akış kapanır
            # ve yeni cihazla yeniden açılır. Programı yeniden başlatmak gerekmez.
            device = self._rec_device
            self._restart_rec.clear()
            last_status = ""
            floor = 100.0
            pre: deque = deque(maxlen=PRE_BLOCKS)
            in_speech = False
            buf_seg = bytearray()
            seg_blocks = 0
            silence = 0

            try:
                with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=BLOCK_SIZE,
                                       channels=CHANNELS, dtype="int16", device=device) as stream:
                    if self.running:
                        say(self._t("status_listening"))
                    else:
                        say(self._t("status_stopped"))
                    while not self._shutdown and not self._restart_rec.is_set():
                        # hızlı mod değişikliğini anında uygula
                        silence_limit = FAST_SILENCE_BLOCKS if self.fast_mode.get() else SILENCE_BLOCKS
                        data, _overflow = stream.read(BLOCK_SIZE)
                        chunk = bytes(data)
                        x = np.frombuffer(chunk, dtype=np.int16).astype(np.float32)
                        rms = float(np.sqrt(np.mean(x * x))) if x.size else 0.0
                        db = 20.0 * log10(max(rms, 1.0) / 32767.0)
                        pct = max(0.0, min(100.0, (db + 60.0) / 50.0 * 100.0))
                        self._push({"t": "level", "v": pct})

                        if not in_speech:
                            floor = max(10.0, floor * 0.92 + rms * 0.08)
                            mult = SENSITIVITY_LEVELS.get(self.sensitivity.get(), 2.2)
                            if rms >= max(60.0, floor * mult):
                                in_speech = True
                                for c in pre:
                                    buf_seg.extend(c)
                                pre.clear()
                                buf_seg.extend(chunk)
                                seg_blocks = 1
                                silence = 0
                                say(self._t("status_speech_detected"))
                            else:
                                pre.append(chunk)
                        else:
                            buf_seg.extend(chunk)
                            seg_blocks += 1
                            mult = SENSITIVITY_LEVELS.get(self.sensitivity.get(), 2.2)
                            if rms >= max(40.0, floor * (mult * 0.6)):
                                silence = 0
                            else:
                                silence += 1
                            done = ((silence >= silence_limit and seg_blocks >= MIN_SPEECH_BLOCKS)
                                    or seg_blocks >= MAX_BLOCKS)
                            if done:
                                self._seg_q.put(bytes(buf_seg))
                                buf_seg = bytearray()
                                in_speech = False
                                seg_blocks = 0
                                silence = 0
                                pre.clear()
                                say(self._t("status_listening2"))
            except Exception as exc:
                if self._shutdown:
                    break
                self.running = False
                self._push({"t": "fatal", "text": self._t("status_fatal_mic", exc=exc)})
                # Geçersiz/meşgul cihazda bekle; yeni cihaz seçilirse yeniden dene
                while not self._shutdown and not self._restart_rec.is_set():
                    time.sleep(0.2)
            else:
                # Cihaz değişiminde PortAudio'nun eski aygıtı bırakması için kısa bekleme
                if self._restart_rec.is_set() and not self._shutdown:
                    time.sleep(0.2)

        self.running = False

    # ── Tanıma iş parçacığı ──────────────────────────────────────────────
    def _stt_worker(self) -> None:
        rec = sr.Recognizer()
        while not self._shutdown:
            try:
                seg = self._seg_q.get(timeout=0.2)
            except queue.Empty:
                continue
            self._push({"t": "status", "text": self._t("status_sending")})
            try:
                # Sessiz/kısık kayıtları Google'ın daha iyi duyması için
                # otomatik kazanç (gain) uygula
                samples = np.frombuffer(seg, dtype=np.int16).astype(np.float32)
                rms = float(np.sqrt(np.mean(samples * samples))) if samples.size else 0.0
                if rms < 5:
                    self._push({"t": "status", "text": self._t("status_silent")})
                    continue
                # Sessiz/kısık kayıtları Google'ın daha iyi duyması için
                # otomatik kazanç (gain) uygula
                if rms < 3000:
                    gain = min(8.0, 3000.0 / rms)
                    samples = np.clip(samples * gain, -32768, 32767).astype(np.int16)
                    seg = samples.tobytes()
                audio = sr.AudioData(seg, SAMPLE_RATE, SAMPLE_WIDTH)
                text = rec.recognize_google(audio, language=self._lang, show_all=False)
            except sr.UnknownValueError:
                self._push({"t": "status", "text": self._t("status_not_understood")})
                continue
            except sr.RequestError as exc:
                self._push({"t": "status", "text": self._t("status_google_error", exc=exc)})
                continue
            except Exception as exc:
                self._push({"t": "status", "text": self._t("status_rec_error", exc=exc)})
                continue
            preview = text[:60] + ("…" if len(text) > 60 else "")
            self._push({"t": "status", "text": self._t("status_recognized", preview=preview)})
            self._push({"t": "text", "text": text})

    # ── Arayüz döngüsü ───────────────────────────────────────────────────
    def _poll(self) -> None:
        # Odakta bizim pencere değilse, son harici pencereyi hatırla (yazma hedefi)
        try:
            fg = ctypes.windll.user32.GetForegroundWindow()
            if self._our_hwnd is None:
                self._our_hwnd = ctypes.windll.user32.GetAncestor(self.winfo_id(), 2)
            if fg and self._our_hwnd and fg != self._our_hwnd:
                self._last_external_fg = fg
        except Exception:
            pass
        if not self.running and self._ui_on:
            self._ui_off()
        while True:
            try:
                ev = self._ui_q.get_nowait()
            except queue.Empty:
                break
            kind = ev.get("t")
            if kind == "level":
                self.bar["value"] = ev.get("v", 0)
            elif kind == "status":
                self.status_var.set(ev["text"])
            elif kind == "text":
                threading.Thread(target=self._type_text, args=(ev["text"],), daemon=True).start()
            elif kind == "toggle":
                self._toggle()
            elif kind == "show":
                try:
                    if self.state() == "iconic":
                        self.deiconify()
                    self.lift()
                    self.attributes("-topmost", True)
                    self.update_idletasks()
                    hwnd = ctypes.windll.user32.FindWindowW(None, "Sesli Yazma · Google")
                    if hwnd:
                        ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                        ctypes.windll.user32.SetForegroundWindow(hwnd)
                except Exception:
                    pass
            elif kind == "control":
                action = ev.get("action")
                if action == "start":
                    if not self.running:
                        self._start_listening()
                elif action == "stop":
                    if self.running:
                        self.running = False
                        self._ui_off()
                        self.status_var.set(self._t("status_paused_cmd"))
                elif action == "fast_on":
                    self.fast_mode.set(True)
                    self.status_var.set(self._t("status_fast_on"))
                elif action == "fast_off":
                    self.fast_mode.set(False)
                    self.status_var.set(self._t("status_fast_off"))
                elif action == "caps_on":
                    self._caps_mode = True
                    self.status_var.set(self._t("status_caps_on"))
                elif action == "caps_off":
                    self._caps_mode = False
                    self.status_var.set(self._t("status_caps_off"))
            elif kind == "fatal":
                self.status_var.set(ev["text"])
        self.after(80, self._poll)

    # ── Odaklı pencereye yazma + sesli komutlar ──────────────────────────
    def _type_text(self, text: str) -> None:
        text = text.strip()
        if not text:
            self._push({"t": "status", "text": self._t("status_empty")})
            return
        try:
            last_was_key = False
            for part in _COMMAND_RE.split(text):
                if part == "":
                    continue
                low = part.lower().strip()
                nlow = _norm(low)
                if nlow in _CTRL_NORM:
                    self._push({"t": "control", "action": _CTRL_NORM[nlow]})
                    last_was_key = True
                    continue
                # Duraklatılmış modda (running=False) sadece komutları işle,
                # normal metni yazma
                if not self.running:
                    continue
                if nlow in _TEXT_NORM:
                    out = _TEXT_NORM[nlow]
                    if self._caps_mode and out.isalpha():
                        out = out.upper()
                    self._typist.type(out)
                    last_was_key = False
                elif nlow in _KEY_NORM:
                    self._perform_key(_KEY_NORM[nlow])
                    last_was_key = True
                else:
                    seg = part.strip()
                    if seg:
                        if self._caps_mode:
                            seg = seg.upper()
                        self._typist.type(seg)
                        last_was_key = False
            if self.running and TRAILING_SPACE and not last_was_key:
                self._typist.type(" ")
            if self.running:
                self._push({"t": "status", "text": self._t("status_typed")})
            else:
                self._push({"t": "status", "text": self._t("status_stopped_cmd")})
        except Exception as exc:
            self._push({"t": "status", "text": self._t("status_type_error", exc=exc)})

    def _perform_key(self, action: str) -> None:
        k = pynput_kb.Key
        if action == "enter":
            self._typist.press(k.enter)
            self._typist.release(k.enter)
        elif action == "tab":
            self._typist.press(k.tab)
            self._typist.release(k.tab)
        elif action == "backspace":
            self._typist.press(k.backspace)
            self._typist.release(k.backspace)
        elif action == "ctrl_backspace":
            with self._typist.pressed(k.ctrl):
                self._typist.press(k.backspace)
                self._typist.release(k.backspace)
        elif action == "ctrl_z":
            with self._typist.pressed(k.ctrl):
                self._typist.press("z")
                self._typist.release("z")
        elif action == "ctrl_a_delete":
            with self._typist.pressed(k.ctrl):
                self._typist.press("a")
                self._typist.release("a")
            self._typist.press(k.delete)
            self._typist.release(k.delete)
        elif action == "escape":
            self._typist.press(k.esc)
            self._typist.release(k.esc)

    def _on_close(self) -> None:
        self.running = False
        self._shutdown = True
        self.destroy()


def main() -> None:
    App().mainloop()


if __name__ == "__main__":
    main()
