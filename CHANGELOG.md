# Changelog 

All notable changes to this project will be documented in this file.

---

## [v 2.0.0] - 2026-04-03

### Added
- Refactor archtecture
- New controler
- New service
- New historic system
- New UI
- New dynamic quality selector
- Some simple tests implementation
- Instalation_Setup
- Now you can Cancel a Download

### Improved
- Better user Interface 
    - With historic (20 last videos)
    - Open file button
    - Open file folder button
    - Video info
        - Resolution 
        - Size(MBs/GBs)
        - Original video title
        - New title

### FIxed
- Now youtube need cookies to you access videos high quality data
> Now you need to provide browser cookies.txt to download a yotube video | local storage
- Also, now we have nodeJs embedded, because youtube use this to check you're not a bot
- Fix progress bar level

## [v 1.3.0] - 2026-02-13

### Added
- Embedded yt-dlp
- yt-dlp auto update resource

### Improved 
- Better user experience with embedded resources

## [v 1.0.0] - 2026-02-11

### Added
- Embedded FFmpeg and FFprobe
- Download progress percentage indicator
- Full HD (1080p) quality option
- MP4 output with H.264 + AAC
- MP3 extraction (192kbps)
- Standalone executable (no external dependencies required)

### Fixed
- Audio codec incompatibility (Opus → AAC)
- 360p limitation when FFmpeg was missing

### Improved
- Download stability
- Format selection logic
- Packaging with PyInstaller

---

## [alpha 0.1.0] - 2026-02-09

### Initial Release
- Basic video download
- MP4 and MP3 support
- Manual FFmpeg dependency
