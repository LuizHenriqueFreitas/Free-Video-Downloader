<!-- Last Review 2026-27-07 -->

# Video-Downloader 🎬

This project is a graphical UI video downloader based on **yt-dlp**.  
It uses yt-dlp as the core downloading engine and provides a clean, simple interface developed with **PySide6**, making it easier to download videos without using the command line.
Official yt-dlp repository: https://github.com/yt-dlp/yt-dlp

### If you wanto to contributing with this projetc
Thank you!   
Read the CONTRIBUTING.md and let's start!

---

## 🪛 Resources

## **For user**

The application is fully self-contained and:
-  Does NOT require Python installed  
-  Does NOT require yt-dlp installed    
-  Does NOT require FFmpeg installed   
-  Does NOT require NodeJs installed    
-  Works on **Windows 11** machine (and probably windows 10)
    ### Maybe it works by code on linux - i develop using mint 22.3 (Zena)
    1. If you are a **linux user** you can try use this runnig on a development environment, a code IDE like VS code is enough.   
    
    2. You need to clone this repo to a local folder, so maybe you need git installed on your machine i supose.   
    
    3. Also is necessary for linux users on that way, has all the exernal tool installed on yout machine, like ffmpeg, NodeJs, yt-dlp, and Python.   
    
    4. You also will need to configure the local develop environment, with all the packages and dependencies these project uses, like pyside6 and others.

### ⚠️ Important: Cookies are required for YouTube
Due to YouTube's restrictions, you **must** provide your browser's cookies to download any video.  
Here's how to do it safely:

1. Install a browser extension like **"Get cookies.txt LOCALLY"** (open source). 

2. Log into YouTube in your browser **(you could use a secondary accounte)**.

3. Export the cookies to a `cookies.txt` file (choose *Netscape format*).  

4. In Video Downloader, click **"Import cookies"** and select that file.

> ⚠️**Security note:**⚠️  
>
> The `cookies.txt` file contains your logged‑in session.  
> - Never share this file. Consider using a secondary YouTube account.
> - We recomend you delete this file after import to Video Downloader

To remove the cookies at any time, press **"Remove cookies"** button.

### **For devs**
You'll need Python, FFmpeg and Node install to develop new features, ***or the binary files***, their paths are:
 > ffmpeg_path = src/tools/ffmpeg/bin/ffmpeg.exe and ffprobe.exe

 > node_path = src/bin/node/node.exe

 > yt-dlp_path = src/bin/yt-dlp.exe

On Windows you don't need to download them by hand:
```
pip install -r src/requirements.txt
powershell -ExecutionPolicy Bypass -File packaging\fetch_deps.ps1
python src/main.py
```

### Build the installer
Needs Python with `src/requirements.txt` and [Inno Setup 6](https://jrsoftware.org/isinfo.php) (`winget install JRSoftware.InnoSetup`).
```
powershell -ExecutionPolicy Bypass -File packaging\build.ps1
```
It downloads the third-party binaries (`fetch_deps.ps1`), runs the tests, packs the app with PyInstaller (`GetMediaFree.spec`, one folder with everything embedded) and builds the installer (`installer.iss`):
- `packaging/out/dist/GetMediaFree/` - app folder, runs without installing
- `packaging/out/installer/GetMediaFree-<version>-Setup.exe` - installer

The version comes from `APP_VERSION` at `src/services/updater.py`.   
Useful options: `-SkipInstaller`, `-SkipTests`, `-SkipFetch`, `-UpdateYtDlp`.

The app icon (`src/assets/icon.ico`) is generated from `website/assets/app-icon.png` by `python packaging/make_icon.py` - run it again if the artwork changes.

The installed app saves user data (history, settings, cookies, updated yt-dlp) at `%LOCALAPPDATA%\GetMediaFree`, so it doesn't need admin rights.

---

## 📣 Frequent errors

### if permission problem
Since the installer version, user data is saved at `%LOCALAPPDATA%\GetMediaFree` and the app doesn't need admin rights. If it still happens, check if that folder is writable.

### cookies problem
Try:   
1. Certify you impot the correct cookie files.
2. try export your cookies again using a browser extension and reimport to app.

### high quality not avaliable
Probably, that is a problem of yt-dlp with youtube, will be fix at next version, stay tuned.

---

## ⚙️ Executable

You can find the most new oficial version of Video Downloader on the Release Page of this repository - just download it and run the installer.

## 🪁 Features and Functionality

- Multiple plataforms support
    - Youtube
    - Instagram
    - X (Twitter)
    - a lot more options
- Youtube Playlists support 
- Download videos in **MP4 format (H.264 + AAC)**
- Dynamic video quality avalable by vídeo (**max 4k or better**)
- Embbed Trimm tool (just for youtube content)
- Extract audio in **MP3 (best quality avalabe)**
- Automatic audio + video merging
- File renaming before download
- Changeble videos download history display by list with data
- Queue download system
- Select output folder
- Download **status** indicator
- Download **progress** indicator (%)
- Open file **and** open file folder button
- Embedded resources (ffmpeg, ffprobe, node, yt-dlp)
- Clean and simple user interface 

---

## 🛠 Built With

- Python
- PySide6 (Qt for Python)
- Pytest
- yt-dlp
- FFmpeg (embedded)
- NodeJs
- PyInstaller
- Inno Setup to build the installer

---

## 📦 How It Works

- yt-dlp handles video downloading
- FFmpeg merges video/audio streams and converts formats
- PySide6 provides the graphical interface
- PyInstaller packages everything into one app folder, and Inno Setup turns it into a single installer

---

## 📄 License

This project uses yt-dlp under its respective license.<br>
This project uses node under its respective license.<br>
FFmpeg is distributed according to its official license terms (the embedded build is GPLv3).<br>
All third-party licenses and source links: [licenses/THIRD_PARTY_NOTICES.txt](licenses/THIRD_PARTY_NOTICES.txt).