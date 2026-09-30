# locales/en.py - English (international)

STRINGS = {
    # ---------------------------------------------------------------- common
    "common.error": "Error",
    "common.cancel": "Cancel",
    "common.close": "Close",
    "common.format": "Format:",
    "common.destination_folder": "Destination folder:",
    "common.choose_folder": "Choose folder",
    "common.dont_show_again": "Don't show this message again",
    "common.dont_show_warning_again": "Don't show this warning again",
    "common.untitled": "Untitled",
    "common.untitled_entry": "(untitled)",

    # ---------------------------------------------------------------- main window
    "main.paste_link": "+ Paste link",
    "main.check_updates": "Check for updates",
    "main.checking_updates": "Checking...",
    "main.import_cookies": "Import cookies",
    "main.remove_cookies": "Remove cookies",
    "main.cookies_unknown": "Cookies: ...",
    "main.cookies_ok": "Cookies: OK",
    "main.cookies_missing": "Cookies: NOT SET UP",
    "main.history_limit": "History:",
    "main.clear_history": "Clear history",
    "main.clear_history_text": (
        "Your whole download history will be cleared, but the videos stay "
        "on your computer. If you want to delete them, do it manually."
    ),
    "main.language": "Language:",
    "main.language_changed_title": "Language changed",
    "main.language_changed_text": (
        "The new language will be applied the next time Get Media Free is opened.\n\n"
        "Restarting now will stop any downloads in progress."
    ),
    "main.restart_now": "Restart now",
    "main.restart_later": "Later",
    "main.ytdlp_update_error": "Failed to update yt-dlp: {error}",
    "main.update_available_title": "Update available",
    "main.update_available_text": (
        "A new version ({version}) is available for download. "
        "Update to get new features and fixes.\n\n"
        "yt-dlp: {ytdlp}"
    ),
    "main.updates_title": "Updates",
    "main.up_to_date_text": "yt-dlp: {ytdlp}\n\nThe app is already up to date (v{version}).",
    "main.select_cookies_file": "Select cookies.txt",
    "main.text_files_filter": "Text files (*.txt)",
    "main.success": "Success",
    "main.cookies_imported": "Cookies imported securely!",
    "main.removed": "Removed",
    "main.cookies_removed": "Cookies removed.",
    "main.info": "Info",
    "main.no_cookies_found": "No cookies found.",
    "main.cookies_required_title": "Cookies required",
    "main.cookies_required_text": "You need to import the cookies.txt file before downloading videos.",
    "main.remove_from_history_title": "Remove from history",
    "main.remove_from_history_text": (
        'Remove "{title}" from the list?\n\n'
        "(The downloaded file will NOT be deleted from disk.)"
    ),

    # ---------------------------------------------------------------- download dialog
    "dialog.title": "New Download",
    "dialog.url_label": "Video URL (YouTube, TikTok, Instagram, etc.):",
    "dialog.advanced_mode": "Select a part of the video (advanced mode)",
    "dialog.quality": "Quality:",
    "dialog.filename_label": "File name (optional):",
    "dialog.add": "Add",
    "dialog.loading_info": "Loading information...",
    "dialog.loading": "Loading...",
    "dialog.info_loaded": "✔ Information loaded",
    "dialog.error": "Error: {error}",
    "dialog.filename_invalid_live": "The file name can't contain: {chars}",
    "dialog.playlist_detected_title": "Playlist detected",
    "dialog.playlist_detected_text": (
        "🔗 **Playlist detected!**\n\n"
        "This URL belongs to a YouTube playlist.\n\n"
        "What do you want to download?"
    ),
    "dialog.only_this_video": "📹 Only this video",
    "dialog.whole_playlist": "📋 The whole playlist",
    "dialog.cookies_not_set": "⚠ Cookies not set up",
    "dialog.cancelled_by_user": "Cancelled by user",
    "dialog.loading_playlist": "Loading playlist...",
    "dialog.playlist_empty": "No videos found in the playlist.",
    "dialog.playlist_loaded": "✔ Playlist loaded: {count} videos",
    "dialog.playlist_error": "Failed to load playlist: {error}",
    "dialog.unknown_size": "unknown size",
    "dialog.needs_conversion_suffix": " — conversion needed",
    "dialog.no_formats": "No formats available",
    "dialog.conversion_title": "This quality needs conversion",
    "dialog.conversion_text": (
        "The site doesn't offer this resolution in the format accepted by video "
        "editors (Premiere, Vegas, CapCut and others).\n\n"
        "After the download, Get Media Free will convert the video on your "
        "computer so it can be used for editing. This can take quite a while, "
        "sometimes longer than the video itself, depending on your computer.\n\n"
        "The progress and the time left are shown on the download card."
    ),
    "dialog.invalid_url_or_folder": "Invalid URL or folder",
    "dialog.load_info_first": "Load the video information first",
    "dialog.invalid_name_title": "Invalid name",
    "dialog.invalid_name_text": "The file name can't contain these characters:\n\n{chars}",
    "dialog.invalid_clip_title": "Invalid clip",
    "dialog.invalid_clip_text": "The selected part must be at least 1 second long.",
    "dialog.file_exists_title": "File already exists",
    "dialog.file_exists_text": "A file with this name and type already exists:\n\n{path}\n\nWhat do you want to do?",
    "dialog.replace_file": "Replace file",
    "dialog.rename_automatically": "Rename automatically",
    "dialog.go_back_rename": "Go back and rename",

    # ---------------------------------------------------------------- playlist dialog
    "playlist.title": "Download playlist",
    "playlist.header": "Playlist: {title}  ({count} videos)",
    "playlist.select_all": "Select all",
    "playlist.clear_selection": "Clear selection",
    "playlist.quality_notice": (
        "ℹ️ Videos will be downloaded in the BEST QUALITY available (up to 1080p) "
        "with their original YouTube names."
    ),
    "playlist.download_selected": "Download selected",
    "playlist.warning_title": "Playlist download",
    "playlist.warning_text": (
        "📋 **Before downloading the playlist**\n\n"
        "• All videos will be downloaded in the **best quality available, up to 1080p**\n"
        "• The original YouTube names will be kept\n"
        "• 4K/8K videos will be downloaded in 1080p to save space\n\n"
        "Do you want to continue?"
    ),
    "playlist.choose_folder_first": "Choose the destination folder.",
    "playlist.select_at_least_one": "Select at least one video.",
    "playlist.best_quality_label": "Best quality (up to 1080p)",

    # ---------------------------------------------------------------- download card
    "card.original": "Original: {title}",
    "card.open_file": "Open file",
    "card.open_folder": "Open folder",
    "card.retry": "Try again",
    "card.copy_link": "Copy link",
    "card.link_copied": "Link copied!",
    "card.remove": "Remove",
    "card.status_queued": "Queued...",
    "card.status_downloading": "Downloading...",
    "card.status_completed": "Completed",
    "card.status_error": "Download failed",
    "card.status_cancelled": "Cancelled",
    "card.cancelling": "Cancelling...",
    "card.cutting": "Trimming clip…",
    "card.converting": "Converting to H.264…",
    "card.calculating_time": "estimating time…",
    "card.seconds_left": "~{seconds} s left",
    "card.minutes_left": "~{minutes} min left",
    "card.hours_left": "~{hours} h {minutes} min left",

    # ---------------------------------------------------------------- clip trimmer
    "trimmer.unknown_duration": "Unknown duration — trimming unavailable.",
    "trimmer.play": "▶ Play",
    "trimmer.pause": "⏸ Pause",
    "trimmer.preview_clip": "Preview clip",
    "trimmer.caption": "Part to download (drag the markers):",
    "trimmer.mark_start": "Start = now",
    "trimmer.mark_end": "End = now",
    "trimmer.start": "Start: {time}",
    "trimmer.end": "End: {time}",
    "trimmer.hint": "Drag the markers or use the buttons to set the clip.",
    "trimmer.loading_preview": "Loading preview…",
    "trimmer.loading_preview_hint": "Loading preview… you can already use the trim bar.",
    "trimmer.preview_unavailable": "Preview unavailable",
    "trimmer.preview_unavailable_link": "Preview unavailable for this link — use the time bar.",
    "trimmer.preview_unavailable_error": "Preview unavailable ({error}).",
    "trimmer.fallback_hint": "{message} Clip selection still works.",
    "trimmer.cant_play": "Couldn't play the video here.",
    "trimmer.unsupported_stream": "Stream format not supported for preview.",

    # ---------------------------------------------------------------- thumbnail
    "thumbnail.no_image": "No image",

    # ---------------------------------------------------------------- download worker
    "worker.ytdlp_failed": "Download failed (yt-dlp returned an error)",
    "worker.ytdlp_failed_detail": "Download failed (yt-dlp returned an error): {detail}",
    "worker.final_file_not_found": "Final file not found",
    "worker.full_video_failed": "Failed to download the full video",
    "worker.full_video_failed_detail": "Failed to download the full video: {detail}",
    "worker.temp_file_not_found": "Temporary file not found",
    "worker.cut_failed": "ffmpeg failed to trim the clip",
    "worker.convert_failed": "Failed to convert the video to MP4 (H.264)",
    "worker.probe_failed": "Couldn't analyze the downloaded file (ffprobe)",
    "worker.merge_failed": "Failed to merge video and audio (FFmpeg missing or failed)",

    # ---------------------------------------------------------------- video info (yt-dlp)
    "video.empty_url": "Empty URL",
    "video.extract_failed": "Failed to get the video information",
    "video.read_response_failed": "Failed to read the yt-dlp response",
    "video.read_playlist_failed": "Failed to read the playlist data",
    "video.blocked_by_youtube": "Blocked by YouTube.",
    "video.too_many_requests": "Too many requests, please try \n again in a while.",
    "video.cookies_error": "Cookies error.",
    "video.unsupported_link": "Unsupported link.",
    "video.private": "Private/unavailable video.",
    "video.login_required": "Sign-in required, try importing more recent cookies.",

    # ---------------------------------------------------------------- embedded tools
    "utils.reinstall_hint": "Reinstall Get Media Free to restore the program files.",
    "utils.ytdlp_not_found_at": "yt-dlp not found at: {path}",
    "utils.ytdlp_dev_hint": "Check that the file is at: src/bin/yt-dlp.exe",
    "utils.ytdlp_not_found_linux": "yt-dlp not found. Install it with: pip install yt-dlp",
    "utils.ffmpeg_not_found_at": "FFmpeg not found at: {path}",
    "utils.ffmpeg_dev_hint": (
        "Check that ffmpeg.exe and ffprobe.exe are at: src/tools/ffmpeg/bin/ "
        "(run packaging/fetch_deps.ps1)"
    ),
    "utils.ffmpeg_not_found_linux": "FFmpeg not found. Install it with: sudo apt install ffmpeg",
    "utils.ffprobe_not_found": "FFprobe not found. It must be in the same folder as ffmpeg.",
    "utils.node_outdated": (
        "The Node.js found at '{path}' is outdated "
        "(version {version} or later is required)."
    ),
    "utils.node_outdated_windows_hint": "download it from https://nodejs.org/ or run packaging/fetch_deps.ps1",
    "utils.node_outdated_linux_hint": (
        "Linux: use nvm (https://github.com/nvm-sh/nvm) to install a recent version"
    ),
    "utils.node_not_found": "Node.js not found!",
    "utils.node_dev_hint": "Put node.exe in src/bin/node/ (run packaging/fetch_deps.ps1)",
    "utils.node_linux_hint": "Linux: install it with 'sudo apt install nodejs' or use nvm",

    # ---------------------------------------------------------------- updater
    "updater.download_failed": "Failed to download yt-dlp",
    "updater.ytdlp_updated": "yt-dlp updated successfully!",
    "updater.update_error": "Update error: {error}",
    "updater.not_found": "Not found",
    "updater.version_error": "Error: {error}",
    "updater.ytdlp_not_found": "yt-dlp not found: {error}",
    "updater.timeout": "Timed out",
    "updater.unexpected_error": "Unexpected error: {error}",

    # ---------------------------------------------------------------- audio language dialog
    "audio.title": "Audio language",
    "audio.text": "This video has audio in {count} languages.\nChoose the one you want to download:",
    "audio.original": "{name} (original)",
    "audio.confirm": "Download in this language",
    # audio track languages (yt-dlp codes, lowercase) - see core/i18n.audio_language_name()
    "audio_lang.ar": "Arabic",
    "audio_lang.bn": "Bengali",
    "audio_lang.cs": "Czech",
    "audio_lang.da": "Danish",
    "audio_lang.de": "German",
    "audio_lang.el": "Greek",
    "audio_lang.en": "English",
    "audio_lang.en-gb": "English (UK)",
    "audio_lang.en-us": "English (US)",
    "audio_lang.es": "Spanish",
    "audio_lang.es-419": "Spanish (Latin America)",
    "audio_lang.es-es": "Spanish (Spain)",
    "audio_lang.es-us": "Spanish (US)",
    "audio_lang.fa": "Persian",
    "audio_lang.fi": "Finnish",
    "audio_lang.fil": "Filipino",
    "audio_lang.fr": "French",
    "audio_lang.fr-ca": "French (Canada)",
    "audio_lang.fr-fr": "French (France)",
    "audio_lang.gu": "Gujarati",
    "audio_lang.he": "Hebrew",
    "audio_lang.hi": "Hindi",
    "audio_lang.hu": "Hungarian",
    "audio_lang.id": "Indonesian",
    "audio_lang.it": "Italian",
    "audio_lang.ja": "Japanese",
    "audio_lang.kn": "Kannada",
    "audio_lang.ko": "Korean",
    "audio_lang.ml": "Malayalam",
    "audio_lang.mr": "Marathi",
    "audio_lang.ms": "Malay",
    "audio_lang.nl": "Dutch",
    "audio_lang.no": "Norwegian",
    "audio_lang.pa": "Punjabi",
    "audio_lang.pl": "Polish",
    "audio_lang.pt": "Portuguese",
    "audio_lang.pt-br": "Portuguese (Brazil)",
    "audio_lang.pt-pt": "Portuguese (Portugal)",
    "audio_lang.ro": "Romanian",
    "audio_lang.ru": "Russian",
    "audio_lang.sv": "Swedish",
    "audio_lang.ta": "Tamil",
    "audio_lang.te": "Telugu",
    "audio_lang.th": "Thai",
    "audio_lang.tr": "Turkish",
    "audio_lang.uk": "Ukrainian",
    "audio_lang.ur": "Urdu",
    "audio_lang.vi": "Vietnamese",
    "audio_lang.zh": "Chinese",
    "audio_lang.zh-hans": "Chinese (Simplified)",
    "audio_lang.zh-hant": "Chinese (Traditional)",
}
