# Translate and revise

"""
Testes para core/video_info.py

Cobrem:
    - VideoInfo.extract() (montagem do comando yt-dlp, timeout, erros, parsing)
    - VideoInfo._format_response() (filtragem, ordenação e deduplicação de formatos)
    - VideoInfo._parse_error() (mapeamento de mensagens de erro)
    - VideoInfo.extract_playlist() (montagem do comando, parsing de entradas)
    - pick_preview_url() (seleção do melhor formato progressivo para preview)
"""

import json
import subprocess
import sys

import pytest

from core import video_info as vi
from core.video_info import VideoInfo, PreviewDownloader


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

class FakeCompletedProcess:
    """Substitui subprocess.CompletedProcess para os testes."""
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


@pytest.fixture
def video(monkeypatch):
    """Instância de VideoInfo com todas as dependências externas mockadas
    com valores 'felizes' por padrão. Cada teste sobrescreve o que precisar."""
    monkeypatch.setattr(vi, "get_ytdlp_path", lambda: "/fake/yt-dlp")
    monkeypatch.setattr(vi, "get_node_path", lambda: "/fake/node")
    monkeypatch.setattr(vi, "get_cookies_path", lambda: "/fake/data/cookies.txt")
    monkeypatch.setattr(vi, "cookies_exists", lambda: False)
    monkeypatch.setattr(vi, "is_youtube", lambda url: "youtube.com" in url)
    monkeypatch.setattr(vi.sys, "platform", "linux")
    return VideoInfo()


# ---------------------------------------------------------------------------
# VideoInfo.extract
# ---------------------------------------------------------------------------

class TestExtract:

    def test_raises_on_empty_url(self, video):
        with pytest.raises(ValueError, match="URL vazia"):
            video.extract("")

    def test_raises_on_none_url(self, video):
        with pytest.raises(ValueError, match="URL vazia"):
            video.extract(None)

    def test_youtube_command_includes_user_agent_and_extractor_args(self, video, monkeypatch):
        captured = {}

        def fake_run(command, **kwargs):
            captured["command"] = command
            return FakeCompletedProcess(returncode=0, stdout=json.dumps({"title": "t"}))

        monkeypatch.setattr(vi.subprocess, "run", fake_run)
        video.extract("https://www.youtube.com/watch?v=abc")

        cmd = captured["command"]
        assert "--user-agent" in cmd
        assert "Mozilla/5.0" in cmd
        # client settings are empty today (the fixed clients returned HTTP 403)
        assert "--extractor-args" not in cmd

    def test_youtube_command_uses_client_settings_when_set(self, video, monkeypatch):
        monkeypatch.setattr(vi, "YOUTUBE_CLIENT_SETTINGS", ["--extractor-args", "youtube:test"])
        captured = {}

        def fake_run(command, **kwargs):
            captured["command"] = command
            return FakeCompletedProcess(returncode=0, stdout=json.dumps({"title": "t"}))

        monkeypatch.setattr(vi.subprocess, "run", fake_run)
        video.extract("https://www.youtube.com/watch?v=abc")
        assert "youtube:test" in captured["command"]

    def test_non_youtube_command_excludes_youtube_specific_args(self, video, monkeypatch):
        captured = {}

        def fake_run(command, **kwargs):
            captured["command"] = command
            return FakeCompletedProcess(returncode=0, stdout=json.dumps({"title": "t"}))

        monkeypatch.setattr(vi.subprocess, "run", fake_run)
        video.extract("https://www.tiktok.com/@user/video/1")

        cmd = captured["command"]
        assert "--user-agent" not in cmd
        assert "--extractor-args" not in cmd

    def test_command_always_includes_base_flags(self, video, monkeypatch):
        captured = {}

        def fake_run(command, **kwargs):
            captured["command"] = command
            return FakeCompletedProcess(returncode=0, stdout=json.dumps({"title": "t"}))

        monkeypatch.setattr(vi.subprocess, "run", fake_run)
        url = "https://www.tiktok.com/@user/video/1"
        video.extract(url)

        cmd = captured["command"]
        assert cmd[0] == "/fake/yt-dlp"
        assert "--js-runtimes" in cmd
        assert "node:/fake/node" in cmd
        assert "--no-playlist" in cmd
        assert "--skip-download" in cmd
        assert "-j" in cmd
        assert cmd[-1] == url

    def test_includes_cookies_when_present(self, video, monkeypatch):
        monkeypatch.setattr(vi, "cookies_exists", lambda: True)
        captured = {}

        def fake_run(command, **kwargs):
            captured["command"] = command
            return FakeCompletedProcess(returncode=0, stdout=json.dumps({"title": "t"}))

        monkeypatch.setattr(vi.subprocess, "run", fake_run)
        video.extract("https://www.tiktok.com/@user/video/1")

        cmd = captured["command"]
        assert "--cookies" in cmd
        assert "/fake/data/cookies.txt" in cmd

    def test_excludes_cookies_when_absent(self, video, monkeypatch):
        monkeypatch.setattr(vi, "cookies_exists", lambda: False)
        captured = {}

        def fake_run(command, **kwargs):
            captured["command"] = command
            return FakeCompletedProcess(returncode=0, stdout=json.dumps({"title": "t"}))

        monkeypatch.setattr(vi.subprocess, "run", fake_run)
        video.extract("https://www.tiktok.com/@user/video/1")

        assert "--cookies" not in captured["command"]

    def test_windows_sets_creationflags(self, video, monkeypatch):
        monkeypatch.setattr(vi.sys, "platform", "win32")
        monkeypatch.setattr(vi.subprocess, "CREATE_NO_WINDOW", 0x08000000, raising=False)
        captured = {}

        def fake_run(command, **kwargs):
            captured["kwargs"] = kwargs
            return FakeCompletedProcess(returncode=0, stdout=json.dumps({"title": "t"}))

        monkeypatch.setattr(vi.subprocess, "run", fake_run)
        video.extract("https://www.tiktok.com/@user/video/1")

        assert captured["kwargs"]["creationflags"] == 0x08000000

    def test_linux_creationflags_is_zero(self, video, monkeypatch):
        captured = {}

        def fake_run(command, **kwargs):
            captured["kwargs"] = kwargs
            return FakeCompletedProcess(returncode=0, stdout=json.dumps({"title": "t"}))

        monkeypatch.setattr(vi.subprocess, "run", fake_run)
        video.extract("https://www.tiktok.com/@user/video/1")

        assert captured["kwargs"]["creationflags"] == 0

    def test_timeout_expired_raises_generic_exception(self, video, monkeypatch):
        def fake_run(command, **kwargs):
            raise subprocess.TimeoutExpired(cmd=command, timeout=90)

        monkeypatch.setattr(vi.subprocess, "run", fake_run)
        with pytest.raises(Exception, match="Erro ao extrair"):
            video.extract("https://www.tiktok.com/@user/video/1")

    def test_nonzero_returncode_raises_parsed_error(self, video, monkeypatch):
        def fake_run(command, **kwargs):
            return FakeCompletedProcess(returncode=1, stderr="Video is private")

        monkeypatch.setattr(vi.subprocess, "run", fake_run)
        with pytest.raises(Exception, match="privado"):
            video.extract("https://www.tiktok.com/@user/video/1")

    def test_invalid_json_stdout_raises_exception(self, video, monkeypatch):
        def fake_run(command, **kwargs):
            return FakeCompletedProcess(returncode=0, stdout="not-json{{{")

        monkeypatch.setattr(vi.subprocess, "run", fake_run)
        with pytest.raises(Exception, match="Falha ao ler a resposta"):
            video.extract("https://www.tiktok.com/@user/video/1")

    def test_successful_extract_returns_formatted_response(self, video, monkeypatch):
        raw_info = {
            "title": "Meu Video",
            "thumbnail": "http://thumb.jpg",
            "duration": 120,
            "formats": [],
        }

        def fake_run(command, **kwargs):
            return FakeCompletedProcess(returncode=0, stdout=json.dumps(raw_info))

        monkeypatch.setattr(vi.subprocess, "run", fake_run)
        result = video.extract("https://www.tiktok.com/@user/video/1")

        assert result["title"] == "Meu Video"
        assert result["thumbnail"] == "http://thumb.jpg"
        assert result["duration"] == 120
        assert result["formats"] == []
        assert result["audio_formats"] == []
        assert result["raw_formats"] == []


# ---------------------------------------------------------------------------
# VideoInfo._format_response
# ---------------------------------------------------------------------------

class TestFormatResponse:

    def test_default_title_when_missing(self):
        result = VideoInfo()._format_response({})
        assert result["title"] == "Sem título"
        assert result["thumbnail"] is None
        assert result["duration"] is None
        assert result["formats"] == []
        assert result["audio_formats"] == []

    def test_separates_video_and_audio_formats(self):
        info = {
            "formats": [
                {"vcodec": "avc1", "acodec": "none", "height": 720, "ext": "mp4", "format_id": "v1"},
                {"vcodec": "none", "acodec": "mp4a", "height": None, "ext": "m4a", "abr": 128, "format_id": "a1"},
                {"vcodec": "none", "acodec": "none", "height": None, "ext": "mhtml", "format_id": "storyboard"},
            ]
        }
        result = VideoInfo()._format_response(info)
        assert len(result["formats"]) == 1
        assert result["formats"][0]["format_id"] == "v1"
        assert len(result["audio_formats"]) == 1
        assert result["audio_formats"][0]["format_id"] == "a1"

    def test_video_formats_require_height(self):
        # vcodec presente mas sem height -> não deve entrar na lista de vídeos
        info = {
            "formats": [
                {"vcodec": "avc1", "acodec": "none", "height": None, "ext": "mp4", "format_id": "v1"},
            ]
        }
        result = VideoInfo()._format_response(info)
        assert result["formats"] == []

    def test_sorts_video_formats_by_height_ascending(self):
        info = {
            "formats": [
                {"vcodec": "avc1", "acodec": "none", "height": 1080, "ext": "mp4", "format_id": "v1080"},
                {"vcodec": "avc1", "acodec": "none", "height": 360, "ext": "mp4", "format_id": "v360"},
                {"vcodec": "avc1", "acodec": "none", "height": 720, "ext": "mp4", "format_id": "v720"},
            ]
        }
        result = VideoInfo()._format_response(info)
        heights = [f["height"] for f in result["formats"]]
        assert heights == [360, 720, 1080]

    def test_sorts_audio_formats_by_abr_ascending(self):
        info = {
            "formats": [
                {"vcodec": "none", "acodec": "mp4a", "height": None, "ext": "m4a", "abr": 192, "format_id": "a192"},
                {"vcodec": "none", "acodec": "mp4a", "height": None, "ext": "m4a", "abr": 64, "format_id": "a64"},
                {"vcodec": "none", "acodec": "mp4a", "height": None, "ext": "m4a", "abr": 128, "format_id": "a128"},
            ]
        }
        result = VideoInfo()._format_response(info)
        abrs = [f["abr"] for f in result["audio_formats"]]
        assert abrs == [64, 128, 192]

    def test_one_entry_per_resolution(self):
        info = {
            "formats": [
                {"vcodec": "avc1", "acodec": "none", "height": 720, "ext": "mp4",
                 "format_id": "v720_a", "tbr": 1000},
                {"vcodec": "vp9", "acodec": "none", "height": 720, "ext": "webm",
                 "format_id": "v720_b", "tbr": 2000},
            ]
        }
        result = VideoInfo()._format_response(info)
        assert len(result["formats"]) == 1

    def test_prefers_h264_on_same_resolution(self):
        # same choice of yt-dlp with "-S res,vcodec:h264": the size shown is real
        info = {
            "formats": [
                {"vcodec": "vp09.00.40.08", "acodec": "none", "height": 1080, "ext": "mp4",
                 "format_id": "303", "filesize": 100},
                {"vcodec": "avc1.64002a", "acodec": "none", "height": 1080, "ext": "mp4",
                 "format_id": "299", "filesize": 200},
                {"vcodec": "av01.0.09M.08", "acodec": "none", "height": 1080, "ext": "mp4",
                 "format_id": "399", "filesize": 50},
            ]
        }
        f = VideoInfo()._format_response(info)["formats"][0]
        assert f["format_id"] == "299"
        assert f["h264"] is True

    def test_h264_false_when_resolution_has_no_h264(self):
        info = {"formats": [
            {"vcodec": "vp9", "acodec": "none", "height": 2160, "ext": "webm", "format_id": "315"},
        ]}
        assert VideoInfo()._format_response(info)["formats"][0]["h264"] is False

    def test_h264_none_when_codec_unknown(self):
        # some sites don't inform the codec: can't know before the download
        info = {"formats": [{"height": 720, "ext": "mp4", "format_id": "hd"}]}
        assert VideoInfo()._format_response(info)["formats"][0]["h264"] is None

    def test_size_includes_best_aac_audio(self):
        info = {"formats": [
            {"vcodec": "avc1", "acodec": "none", "height": 1080, "ext": "mp4",
             "format_id": "299", "filesize": 1000},
            {"vcodec": "none", "acodec": "opus", "ext": "webm", "abr": 130,
             "format_id": "251", "filesize": 70},
            {"vcodec": "none", "acodec": "mp4a.40.2", "ext": "m4a", "abr": 129,
             "format_id": "140", "filesize": 50},
        ]}
        f = VideoInfo()._format_response(info)["formats"][0]
        assert f["audio_format_id"] == "140"
        assert f["filesize"] == 1050

    def test_size_without_audio_when_video_already_has_audio(self):
        info = {"formats": [
            {"vcodec": "avc1", "acodec": "mp4a", "height": 360, "ext": "mp4",
             "format_id": "18", "filesize": 500},
            {"vcodec": "none", "acodec": "mp4a", "ext": "m4a", "abr": 129,
             "format_id": "140", "filesize": 50},
        ]}
        f = VideoInfo()._format_response(info)["formats"][0]
        assert f["audio_format_id"] is None
        assert f["filesize"] == 500

    def test_size_none_when_audio_size_unknown(self):
        info = {"formats": [
            {"vcodec": "avc1", "acodec": "none", "height": 720, "ext": "mp4",
             "format_id": "v", "filesize": 500},
            {"vcodec": "none", "acodec": "mp4a", "ext": "m4a", "format_id": "a"},
        ]}
        assert VideoInfo()._format_response(info)["formats"][0]["filesize"] is None

    def test_size_estimated_by_bitrate_and_duration(self):
        info = {"duration": 100, "formats": [
            {"vcodec": "avc1", "acodec": "none", "height": 720, "ext": "mp4",
             "format_id": "v", "tbr": 800},
        ]}
        # 800 kbit/s * 100 s = 10_000_000 bytes
        assert VideoInfo()._format_response(info)["formats"][0]["filesize"] == 10_000_000

    def test_direct_formats_preferred_over_hls(self):
        info = {"formats": [
            {"vcodec": "avc1", "acodec": "none", "height": 720, "ext": "mp4",
             "format_id": "hls", "protocol": "m3u8_native", "tbr": 9000},
            {"vcodec": "avc1", "acodec": "none", "height": 720, "ext": "mp4",
             "format_id": "https", "protocol": "https", "tbr": 1000},
        ]}
        assert VideoInfo()._format_response(info)["formats"][0]["format_id"] == "https"

    def test_none_bitrate_and_height_do_not_crash(self):
        # regression: HLS audio formats come with "abr": None (TypeError on sort)
        info = {"formats": [
            {"vcodec": "none", "acodec": "mp4a", "ext": "mp4", "abr": None, "format_id": "233"},
            {"vcodec": "none", "acodec": "mp4a", "ext": "mp4", "abr": None, "format_id": "234"},
            {"vcodec": "avc1", "acodec": "none", "height": None, "ext": "mp4", "format_id": "x"},
            {"vcodec": "avc1", "acodec": "none", "height": 360, "ext": "mp4",
             "format_id": "134", "fps": None, "tbr": None},
        ]}
        result = VideoInfo()._format_response(info)
        assert [f["height"] for f in result["formats"]] == [360]

    def test_deduplicates_audio_formats_by_ext_and_abr(self):
        info = {
            "formats": [
                {"vcodec": "none", "acodec": "mp4a", "height": None, "ext": "m4a",
                 "abr": 128, "format_id": "a1", "filesize": 500},
                {"vcodec": "none", "acodec": "mp4a", "height": None, "ext": "m4a",
                 "abr": 128, "format_id": "a2", "filesize": 600},
            ]
        }
        result = VideoInfo()._format_response(info)
        assert len(result["audio_formats"]) == 1

    def test_uses_filesize_approx_when_filesize_missing(self):
        info = {
            "formats": [
                {"vcodec": "avc1", "acodec": "none", "height": 480, "ext": "mp4",
                 "format_id": "v1", "filesize_approx": 12345},
            ]
        }
        result = VideoInfo()._format_response(info)
        assert result["formats"][0]["filesize"] == 12345

    def test_filesize_none_when_both_missing(self):
        info = {
            "formats": [
                {"vcodec": "avc1", "acodec": "none", "height": 480, "ext": "mp4", "format_id": "v1"},
            ]
        }
        result = VideoInfo()._format_response(info)
        assert result["formats"][0]["filesize"] is None

    def test_raw_formats_preserved_untouched(self):
        formats = [
            {"vcodec": "avc1", "acodec": "none", "height": 480, "ext": "mp4", "format_id": "v1"},
        ]
        info = {"formats": formats}
        result = VideoInfo()._format_response(info)
        assert result["raw_formats"] == formats

    def test_missing_formats_key_defaults_to_empty_list(self):
        result = VideoInfo()._format_response({"title": "x"})
        assert result["raw_formats"] == []


# ---------------------------------------------------------------------------
# VideoInfo._parse_error
# ---------------------------------------------------------------------------

class TestParseError:

    @pytest.mark.parametrize("stderr, expected_substring", [
        ("ERROR: Confirm you're not a bot", "Bloqueado pelo youtube"),
        ("some CAPTCHA required", "Bloqueado pelo youtube"),
        ("HTTP Error 429: Too Many Requests", "Muitas tentativas"),
        ("invalid cookies file provided", "Erro com cookies"),
        ("Unsupported URL: foo", "Link não suportado"),
        ("This video is Private", "Vídeo privado"),
        ("ERROR: Sign in to confirm your age", "Login necessário"),
    ])
    def test_known_error_patterns(self, stderr, expected_substring):
        result = VideoInfo()._parse_error(stderr)
        assert expected_substring in result

    def test_unknown_error_returns_original_stderr(self):
        stderr = "some completely unknown failure occurred"
        assert VideoInfo()._parse_error(stderr) == stderr

    def test_matching_is_case_insensitive(self):
        result = VideoInfo()._parse_error("VIDEO IS PRIVATE")
        assert "privado" in result

    def test_empty_stderr_returns_empty_string(self):
        assert VideoInfo()._parse_error("") == ""


# ---------------------------------------------------------------------------
# VideoInfo.extract_playlist
# ---------------------------------------------------------------------------

class TestExtractPlaylist:

    def test_raises_on_empty_url(self, video):
        with pytest.raises(ValueError, match="null URL"):
            video.extract_playlist("")

    def test_command_includes_flat_playlist_flags(self, video, monkeypatch):
        captured = {}

        def fake_run(command, **kwargs):
            captured["command"] = command
            return FakeCompletedProcess(
                returncode=0,
                stdout=json.dumps({"_type": "playlist", "title": "PL", "entries": []}),
            )

        monkeypatch.setattr(vi.subprocess, "run", fake_run)
        video.extract_playlist("https://www.youtube.com/playlist?list=PL123")

        cmd = captured["command"]
        assert "--flat-playlist" in cmd
        assert "--no-warnings" in cmd
        assert "-J" in cmd

    def test_includes_cookies_when_present(self, video, monkeypatch):
        monkeypatch.setattr(vi, "cookies_exists", lambda: True)
        captured = {}

        def fake_run(command, **kwargs):
            captured["command"] = command
            return FakeCompletedProcess(
                returncode=0,
                stdout=json.dumps({"_type": "playlist", "title": "PL", "entries": []}),
            )

        monkeypatch.setattr(vi.subprocess, "run", fake_run)
        video.extract_playlist("https://www.youtube.com/playlist?list=PL123")

        assert "--cookies" in captured["command"]

    def test_nonzero_returncode_raises_parsed_error(self, video, monkeypatch):
        def fake_run(command, **kwargs):
            return FakeCompletedProcess(returncode=1, stderr="captcha required")

        monkeypatch.setattr(vi.subprocess, "run", fake_run)
        with pytest.raises(Exception, match="Bloqueado"):
            video.extract_playlist("https://www.youtube.com/playlist?list=PL123")

    def test_invalid_json_raises_exception(self, video, monkeypatch):
        def fake_run(command, **kwargs):
            return FakeCompletedProcess(returncode=0, stdout="not json")

        monkeypatch.setattr(vi.subprocess, "run", fake_run)
        with pytest.raises(Exception, match="Falha ao ler os dados da playlist"):
            video.extract_playlist("https://www.youtube.com/playlist?list=PL123")

    def test_returns_none_when_not_a_playlist_type(self, video, monkeypatch):
        def fake_run(command, **kwargs):
            return FakeCompletedProcess(
                returncode=0,
                stdout=json.dumps({"_type": "video", "title": "single"}),
            )

        monkeypatch.setattr(vi.subprocess, "run", fake_run)
        result = video.extract_playlist("https://www.youtube.com/watch?v=abc")
        assert result is None

    def test_returns_none_when_entries_empty(self, video, monkeypatch):
        def fake_run(command, **kwargs):
            return FakeCompletedProcess(
                returncode=0,
                stdout=json.dumps({"_type": "playlist", "title": "PL", "entries": []}),
            )

        monkeypatch.setattr(vi.subprocess, "run", fake_run)
        result = video.extract_playlist("https://www.youtube.com/playlist?list=PL123")
        assert result is None

    def test_parses_entries_with_full_data(self, video, monkeypatch):
        entries = [
            {
                "url": "https://www.youtube.com/watch?v=xyz",
                "title": "Video 1",
                "id": "xyz",
                "duration": 100,
                "thumbnail": "https://img.example.com/xyz.jpg",
            }
        ]

        def fake_run(command, **kwargs):
            return FakeCompletedProcess(
                returncode=0,
                stdout=json.dumps({"_type": "playlist", "title": "My Playlist", "entries": entries}),
            )

        monkeypatch.setattr(vi.subprocess, "run", fake_run)
        result = video.extract_playlist("https://www.youtube.com/playlist?list=PL123")

        assert result["title"] == "My Playlist"
        assert len(result["entries"]) == 1
        entry = result["entries"][0]
        assert entry["url"] == "https://www.youtube.com/watch?v=xyz"
        assert entry["title"] == "Video 1"
        assert entry["id"] == "xyz"
        assert entry["duration"] == 100
        assert entry["thumbnail"] == "https://img.example.com/xyz.jpg"

    def test_skips_falsy_entries(self, video, monkeypatch):
        entries = [None, {}, {"id": "abc123", "title": "valid"}]

        def fake_run(command, **kwargs):
            return FakeCompletedProcess(
                returncode=0,
                stdout=json.dumps({"_type": "playlist", "title": "PL", "entries": entries}),
            )

        monkeypatch.setattr(vi.subprocess, "run", fake_run)
        result = video.extract_playlist("https://www.youtube.com/playlist?list=PL123")
        # None é pulado; {} ainda é um dict truthy? {} é falsy em Python!
        # então tanto None quanto {} são ignorados, sobrando só o terceiro
        assert len(result["entries"]) == 1
        assert result["entries"][0]["id"] == "abc123"

    def test_builds_youtube_url_from_id_when_not_http(self, video, monkeypatch):
        entries = [{"id": "abc123", "title": "Video"}]

        def fake_run(command, **kwargs):
            return FakeCompletedProcess(
                returncode=0,
                stdout=json.dumps({"_type": "playlist", "title": "PL", "entries": entries}),
            )

        monkeypatch.setattr(vi.subprocess, "run", fake_run)
        result = video.extract_playlist("https://www.youtube.com/playlist?list=PL123")
        assert result["entries"][0]["url"] == "https://www.youtube.com/watch?v=abc123"

    def test_non_http_id_kept_as_is_for_non_youtube(self, video, monkeypatch):
        monkeypatch.setattr(vi, "is_youtube", lambda url: False)
        entries = [{"id": "abc123", "title": "Video"}]

        def fake_run(command, **kwargs):
            return FakeCompletedProcess(
                returncode=0,
                stdout=json.dumps({"_type": "playlist", "title": "PL", "entries": entries}),
            )

        monkeypatch.setattr(vi.subprocess, "run", fake_run)
        result = video.extract_playlist("https://vimeo.com/showcase/123")
        # não é youtube, então a URL não é reconstruída, permanece o id puro
        assert result["entries"][0]["url"] == "abc123"

    def test_prefers_webpage_url_over_id(self, video, monkeypatch):
        entries = [{"id": "abc123", "webpage_url": "https://www.youtube.com/watch?v=abc123", "title": "V"}]

        def fake_run(command, **kwargs):
            return FakeCompletedProcess(
                returncode=0,
                stdout=json.dumps({"_type": "playlist", "title": "PL", "entries": entries}),
            )

        monkeypatch.setattr(vi.subprocess, "run", fake_run)
        result = video.extract_playlist("https://www.youtube.com/playlist?list=PL123")
        assert result["entries"][0]["url"] == "https://www.youtube.com/watch?v=abc123"

    def test_builds_thumbnail_when_missing_for_youtube(self, video, monkeypatch):
        entries = [{"id": "abc123", "title": "V"}]

        def fake_run(command, **kwargs):
            return FakeCompletedProcess(
                returncode=0,
                stdout=json.dumps({"_type": "playlist", "title": "PL", "entries": entries}),
            )

        monkeypatch.setattr(vi.subprocess, "run", fake_run)
        result = video.extract_playlist("https://www.youtube.com/playlist?list=PL123")
        assert result["entries"][0]["thumbnail"] == "https://img.youtube.com/vi/abc123/mqdefault.jpg"

    def test_no_thumbnail_built_for_non_youtube(self, video, monkeypatch):
        monkeypatch.setattr(vi, "is_youtube", lambda url: False)
        entries = [{"id": "abc123", "webpage_url": "https://vimeo.com/abc123", "title": "V"}]

        def fake_run(command, **kwargs):
            return FakeCompletedProcess(
                returncode=0,
                stdout=json.dumps({"_type": "playlist", "title": "PL", "entries": entries}),
            )

        monkeypatch.setattr(vi.subprocess, "run", fake_run)
        result = video.extract_playlist("https://vimeo.com/showcase/123")
        assert result["entries"][0]["thumbnail"] is None

    def test_default_title_when_missing(self, video, monkeypatch):
        entries = [{"id": "abc123", "title": "V"}]

        def fake_run(command, **kwargs):
            return FakeCompletedProcess(
                returncode=0,
                stdout=json.dumps({"_type": "playlist", "entries": entries}),
            )

        monkeypatch.setattr(vi.subprocess, "run", fake_run)
        result = video.extract_playlist("https://www.youtube.com/playlist?list=PL123")
        assert result["title"] == "Playlist"

    def test_default_entry_title_when_missing(self, video, monkeypatch):
        entries = [{"id": "abc123"}]

        def fake_run(command, **kwargs):
            return FakeCompletedProcess(
                returncode=0,
                stdout=json.dumps({"_type": "playlist", "title": "PL", "entries": entries}),
            )

        monkeypatch.setattr(vi.subprocess, "run", fake_run)
        result = video.extract_playlist("https://www.youtube.com/playlist?list=PL123")
        assert result["entries"][0]["title"] == "(sem título)"


# ---------------------------------------------------------------------------
# PreviewDownloader (trimmer preview, local file with sound)
# ---------------------------------------------------------------------------

class FakePopen:
    def __init__(self, returncode=0, on_wait=None):
        self.returncode = returncode
        self.pid = 1234
        self._on_wait = on_wait
        self.killed = False

    def wait(self, timeout=None):
        if self._on_wait:
            self._on_wait()
        return self.returncode

    def poll(self):
        return None

    def kill(self):
        self.killed = True


@pytest.fixture
def preview_env(monkeypatch):
    monkeypatch.setattr(vi, "get_ytdlp_path", lambda: "/fake/yt-dlp")
    monkeypatch.setattr(vi, "get_node_path", lambda: "/fake/node")
    monkeypatch.setattr(vi, "get_ffmpeg_path", lambda: "/fake/ffmpeg")
    monkeypatch.setattr(vi, "get_cookies_path", lambda: "/fake/data/cookies.txt")
    monkeypatch.setattr(vi, "cookies_exists", lambda: True)
    monkeypatch.setattr(vi.sys, "platform", "linux")


class TestPreviewDownloader:

    def _run(self, monkeypatch, tmp_path, url="https://vimeo.com/1", returncode=0, create=".mp4"):
        captured = {}

        def fake_popen(cmd, **kwargs):
            captured["cmd"] = cmd
            captured["kwargs"] = kwargs

            def on_wait():
                if create:
                    (tmp_path / f"preview_x{create}").write_text("data")
            return FakePopen(returncode=returncode, on_wait=on_wait)

        monkeypatch.setattr(vi.subprocess, "Popen", fake_popen)
        result = PreviewDownloader().download(url, str(tmp_path), "preview_x")
        return result, captured

    def test_command_downloads_small_file_with_sound(self, preview_env, monkeypatch, tmp_path):
        _, captured = self._run(monkeypatch, tmp_path)
        cmd = captured["cmd"]
        assert cmd[0] == "/fake/yt-dlp"
        assert cmd[cmd.index("-f") + 1] == "bv*+ba/b"
        assert cmd[cmd.index("-S") + 1] == "res:240,vcodec:h264,acodec:aac,+br"
        assert "--no-playlist" in cmd
        assert "--cookies" in cmd

    def test_output_does_not_block_on_pipes(self, preview_env, monkeypatch, tmp_path):
        _, captured = self._run(monkeypatch, tmp_path)
        assert captured["kwargs"]["stdout"] == vi.subprocess.DEVNULL
        assert captured["kwargs"]["stderr"] == vi.subprocess.DEVNULL

    def test_returns_downloaded_file(self, preview_env, monkeypatch, tmp_path):
        result, _ = self._run(monkeypatch, tmp_path)
        assert result == str(tmp_path / "preview_x.mp4")

    def test_any_extension_is_accepted(self, preview_env, monkeypatch, tmp_path):
        # archive.org delivers a single .ogv - QMediaPlayer plays it
        result, _ = self._run(monkeypatch, tmp_path, create=".ogv")
        assert result == str(tmp_path / "preview_x.ogv")

    def test_failure_returns_none_and_cleans(self, preview_env, monkeypatch, tmp_path):
        result, _ = self._run(monkeypatch, tmp_path, returncode=1)
        assert result is None
        assert list(tmp_path.iterdir()) == []

    def test_no_file_returns_none(self, preview_env, monkeypatch, tmp_path):
        result, _ = self._run(monkeypatch, tmp_path, create=None)
        assert result is None

    def test_client_settings_only_for_youtube(self, preview_env, monkeypatch, tmp_path):
        monkeypatch.setattr(vi, "YOUTUBE_CLIENT_SETTINGS", ["--extractor-args", "youtube:test"])
        _, captured = self._run(monkeypatch, tmp_path, url="https://vimeo.com/1")
        assert "--extractor-args" not in captured["cmd"]
        _, captured = self._run(monkeypatch, tmp_path, url="https://www.youtube.com/watch?v=a")
        assert "--extractor-args" in captured["cmd"]

    def test_cancel_kills_process_and_returns_none(self, preview_env, monkeypatch, tmp_path):
        downloader = PreviewDownloader()
        procs = []

        def fake_popen(cmd, **kwargs):
            def on_wait():
                (tmp_path / "preview_x.mp4").write_text("data")
                downloader.cancel()
            procs.append(FakePopen(on_wait=on_wait))
            return procs[-1]

        monkeypatch.setattr(vi.subprocess, "Popen", fake_popen)
        assert downloader.download("https://vimeo.com/1", str(tmp_path), "preview_x") is None
        assert procs[0].killed is True
        assert list(tmp_path.iterdir()) == []

    def test_error_building_command_returns_none(self, preview_env, monkeypatch, tmp_path):
        def raise_error():
            raise Exception("Node.js não encontrado")
        monkeypatch.setattr(vi, "get_node_path", raise_error)
        assert PreviewDownloader().download("https://vimeo.com/1", str(tmp_path), "preview_x") is None
