This file, Roadmap, is the plans to next versions of this application.


See, the x.x.x already has what is write above implemented,
this things are what the version need to have to be released.

>PS: this was created after v2.0.0 release.


---


### ALpha 0.1.0
Make yt-dlp work through python and pyside GUI.
(Very Non stable!).
>*nothing embbed yet*


---


### v1.0.0
Make the application compatible with any windows 10, or higher, PC.
Embedd ffmpeg to application.


---


### v1.3.0
Embedd yt-dlp with auto-update resource implemented.
auto-upadete of yt-dlp, not the full applicatino.


---


### v2.0.0
The biggest update until now.   

Rebuild all the software with new screens, new UI and more user resources.   

About development, that version implements a installer, embbed nodejs runtime, yt-dlp and ffmpeg, also historic of donwloads was system implemented,download queue and visual feedbacks to user.      


---


### v2.5.0
Allows donwloads from instagram, X, Tiktok in addition to youtube.

Allows downloads of youtube playlists or queues.

Provides a trimmer tool for any site yt-dlp can download (preview with sound and time-bar), you can cut a clip and get only this.

Code review and documentation for new versions and more reability of the app.

v2.5.1: trimmer tool (advanced mode) restricted to single youtube videos - hidden for other sites and playlists.


---


### v2.6.0
Localization: the whole interface is available in Portuguese (Brazil) and English.

The installer asks the language and the app starts in it; it can also be changed later on the app ("Idioma" / "Language" selector, applied after a restart).

trimmer preview player uses software decoding only (GPU decoding crashed the app on some video drivers when playing); native crashes are written to data/crash.log.

v2.6.2: fixed the crash when opening the advanced mode - background threads (preview, video info, playlist, thumbnails, update check, downloads) were destroyed while still running; they are now released only after they really end (services/thread_keeper.py).


---


### v3.0.0
Full auto-update and more durability enhancement implementation.

All code translated to english.

Add to projetc a landingpage and github page to new people find the software.


---