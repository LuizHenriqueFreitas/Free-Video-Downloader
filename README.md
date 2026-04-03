# Video-Downloader 🎬

This project is a graphical UI video downloader based on **yt-dlp**.  
It uses yt-dlp as the core downloading engine and provides a clean, simple interface developed with **PySide6**, making it easier to download videos without using the command line.
Official yt-dlp repository: https://github.com/yt-dlp/yt-dlp

---


## 🪛 Resources

### **For user**

The application is fully self-contained and:
-  Does NOT require Python installed
-  Does NOT require FFmpeg installed
-  Does NOT require NodeJs installed
-  Works on any **Windows 11** machine (no data about linux and Mac)
>***This version can auto-update the yt-dlp tool - you can try it with the button***

### **For devs**
You'll need Python, FFmpeg and Node install to develop new features, ***or the binary files***, their paths are:
 > ffmpeg_path = tools/ffmpeg/bin/ffmpeg.exe and ffprobe.exe

 > node_path = bin/node/ <here you put all node binary files, like node.exe>

**If you want to compile** i recomend you has the binary files to compile embed, or the .exe will just work on PCs with node and ffmpeg installed.
---

## ⚙️ Executable

You can find the most new oficial version of Video Downloader on the Release Page of this repository - just download it and open .exe file

## 🪁 Features and Functionality

- Select output folder
- Download videos in **MP4 format (H.264 + AAC)**
- Dynamic video quality avalable by vídeo (**max 4k or better**)
- Extract audio in **MP3 (192 kbps)**
- Automatic audio + video merging
- File renaming before download
- 20 videos download history display by list with data
- Queue download system
- Download status indicator
- Open file **and** open file folder button
- Download progress indicator (%)
- Embedded resources (ffmpeg, ffprobe, node, yt-dlp)
- Clean and simple user interface 

---

## 🛠 Built With

- Python
- PySide6 (Qt for Python)
- yt-dlp
- FFmpeg (embedded)
- NodeJs
- PyInstaller

---

## 📦 How It Works

- yt-dlp handles video downloading
- FFmpeg merges video/audio streams and converts formats
- PySide6 provides the graphical interface
- PyInstaller packages everything into a single executable

---

## 📌 Project Structure

>core/ → Download logic and utilities <br>
>ui/ → Interface files <br>
>assets/ → Icons and UI resources <br>
>tools/ → FFmpeg binaries (development only) <br>
>main.py → Application entry point <br>

---

## 📄 License

This project uses yt-dlp under its respective license.  
FFmpeg is distributed according to its official license terms.