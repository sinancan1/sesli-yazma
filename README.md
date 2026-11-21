# 🎙️ Voice Typing (Sesli Yazma)

**Free, open-source, system-wide voice dictation for Windows.**

Speak and your words are typed into **whichever window has focus** — Word, browser, Notepad, Excel, WhatsApp Web, Discord… anywhere a text cursor exists. No text box, no copy-paste.

[![Download](https://img.shields.io/badge/Download-Installer-success?style=for-the-badge)](https://github.com/sinancan1/sesli-yazma/releases/latest)
[![Platform](https://img.shields.io/badge/platform-Windows%2010%20%2F%2011-blue?style=flat-square)](#)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue?style=flat-square)](#)
[![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)

![Voice Typing screenshot](docs/screenshot.png)

---

## ✨ Features

- **System-wide dictation:** Press F9 to start/stop; text goes to the focused window.
- **No text box:** No copy-paste needed — types exactly where the cursor is.
- **Voice start:** Say "start" to begin listening even when paused.
- **Voice commands:** "period", "comma", "new line", "send/enter", "delete", "undo", etc.
- **Turkish character support:** ş, ğ, ı, ç, ö, ü in both commands and text.
- **Distant speech:** Sensitivity control + automatic gain (AGC).
- **Instant microphone switching:** Change the input device without restarting the app.
- **Mini card:** Stays on top without stealing focus; restore with F10.
- **Fast mode:** Lowers the silence threshold from 500 ms to 300 ms.
- **One-file installer:** No Python required — all dependencies are bundled.

The interface follows your speech language: Turkish UI for Turkish, English UI otherwise.

---

## 📥 Download & install

1. Download `SesliYazma_Kurulum.exe` from the [**Releases**](https://github.com/sinancan1/sesli-yazma/releases/latest) page.
2. Double-click → **Next → Install → Finish**.
3. Optionally check "Create desktop shortcut" during setup.
4. Launch **Sesli Yazma** from the desktop shortcut or Start menu.

> **Windows SmartScreen:** The app is free and open source, so it is not digitally signed. If you see "Windows protected your PC", click **More info → Run anyway**.

**System requirements:** Windows 10/11 (64-bit), internet connection, microphone.

> The installer also checks for **Microsoft Visual C++ 2015–2022 (x64) Runtime** and installs it automatically if missing. You don't need to do anything.

### Run from source

Requires Python 3.10+:

```bash
git clone https://github.com/sinancan1/sesli-yazma.git
cd sesli-yazma
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe sesli_yazma.py
```

On Windows, `setup.bat` does this automatically; then run `start.bat`.

---

## 🚀 Usage

1. Open the app. The mini card appears in the top-right corner.
2. Click into the target application (cursor must be in a text field).
3. Press **F9** or say **"start"**. The card shows "● Listening…".
4. Speak. Each sentence/segment is recognized and typed into the focused window.
5. Press **F9** again or say **"stop"** when done.

| Shortcut | Action |
|---|---|
| **F9** | Start / stop listening |
| **F10** | Restore the mini card |
| Closing the card | Exits the program |

> **Tip:** For distant speech, set **Sensitivity → Very high**. In noisy environments, "High" or "Medium" may work better.

### Microphone selection

Pick the input device from the **Mic** dropdown on the card. The change is applied **instantly** - no restart required. While switching, the card briefly shows "Switching microphone…".

> **Languages:** Recognition works in all 10 supported languages — speak in the selected language. The interface is shown in Turkish or English.

---

## 🗣️ Voice commands

These words are not typed as text; they trigger the corresponding action.

### Punctuation & formatting

| Say | Result |
|---|---|
| period | `.` |
| comma | `,` |
| question mark / question | `?` |
| exclamation mark / exclamation | `!` |
| colon | `:` |
| semicolon | `;` |
| open parenthesis / close parenthesis | `(` / `)` |
| open quote / close quote | `"` |
| space | space |
| new line | Enter |
| new paragraph | Double Enter |

### Keys & editing

| Say | Result |
|---|---|
| send / enter | Enter |
| tab | Tab |
| delete | Backspace |
| delete word | Ctrl + Backspace |
| undo | Ctrl + Z |
| delete all / delete everything | Select all + delete |
| escape | Esc |

### Program control

| Say | Result |
|---|---|
| start / begin listening | Start listening |
| stop / stop program / close / finish | Stop listening |
| fast mode | Fast mode (300 ms silence) |
| normal mode | Normal mode (500 ms silence) |
| caps / capital letters | CAPS mode |
| lowercase | Normal case mode |

> Everyday words like "okay", "yes", "no" are typed as normal text, not commands.

---

## 🛠️ Troubleshooting

| Problem | Solution |
|---|---|
| **"Microphone error"** | Windows Settings → Privacy & security → Microphone → "Let apps access your microphone" must be on. |
| **"Could not reach Google service"** | Check your internet connection; corporate networks/VPNs may block it. |
| **Not detecting distant speech** | Set Sensitivity to **Very high**; face the microphone. |
| **Wrong device selected** | Pick the correct device from the **Mic** dropdown — no restart needed. |
| **Card disappeared** | Press **F10** or click the taskbar icon. |
| **SmartScreen warning** | Click **More info → Run anyway**. |

---

## 🔒 Privacy

- **The app collects no remote data.** Speech segments are sent only to Google's free Web Speech endpoint for recognition; nothing else is transmitted to any server, analytics service, or third party. All text is generated locally on your computer.
- Speech segments are sent to **Google's free Web Speech endpoint** for recognition. No separate API key is required.
- The app has no connection to Google, Microsoft, or any other company.
- The Google endpoint is an unofficial, free service and may change or be rate-limited in the future. For heavy use, consider an official API such as Google Cloud Speech-to-Text.

---

## 🧑‍💻 Development

### Build (single-file EXE)

```bash
.venv\Scripts\python.exe -m pip install pyinstaller
.venv\Scripts\pyinstaller.exe --noconsole --onefile --name SesliYazma ^
  --hidden-import sounddevice --hidden-import speech_recognition ^
  --hidden-import pynput --hidden-import pynput.keyboard ^
  --hidden-import numpy sesli_yazma.py
```

### Installer (Inno Setup)

1. Install [Inno Setup 6](https://jrsoftware.org/isinfo.php).
2. Open `installer.iss` and compile, or from the command line:

```bash
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
```

Output: `installer_output\SesliYazma_Kurulum.exe`

The installer bundles the Microsoft Visual C++ 2015–2022 (x64) Runtime and installs it automatically if missing.

---

## 🤝 Contributing

Bug reports, suggestions, and pull requests are welcome. Please open an issue first; for large changes, let's discuss the approach together.

## 📄 License

[MIT](LICENSE) — free to use, modify, and distribute.

---

<details>
<summary><b>Türkçe özet</b></summary>

**Sesli Yazma**, Windows'ta her yerde çalışan ücretsiz ve açık kaynaklı sistem geneli dikte uygulamasıdır. Google'ın ücretsiz Web Speech uç noktasıyla konuşmanızı metne çevirir ve odaktaki pencereye gerçek klavye girişi olarak yazar. **F9** ile başlat/durdur, **"başlat"** diyerek sesli başlatma, noktalama/tuş sesli komutları, 10 dil desteği ve hazır kurulum dosyası. Uygulama uzaktan hiçbir veri toplamaz.

</details>
