import json
import pytest
from unittest.mock import patch, MagicMock

from core.video_info import VideoInfo


# ==========================
# FIXTURE BASE
# ==========================

@pytest.fixture
def video_info():
    return VideoInfo()


# ==========================
# INPUT VALIDATION
# ==========================

def test_extract_deve_falhar_com_url_vazia(video_info):
    with pytest.raises(ValueError, match="URL vazia"):
        video_info.extract("")


# ==========================
# MOCK DE SUBPROCESS
# ==========================

def mock_subprocess_success(data):
    mock = MagicMock()
    mock.returncode = 0
    mock.stdout = json.dumps(data)
    mock.stderr = ""
    return mock


def mock_subprocess_error(stderr="erro qualquer"):
    mock = MagicMock()
    mock.returncode = 1
    mock.stdout = ""
    mock.stderr = stderr
    return mock


# ==========================
# TESTE DE SUCESSO
# ==========================

@patch("core.video_info.subprocess.run")
@patch("core.video_info.cookies_exists", return_value=False)
def test_extract_retorna_dados_formatados(mock_cookies, mock_run, video_info):
    fake_data = {
        "title": "Teste",
        "thumbnail": "url_thumb",
        "duration": 120,
        "formats": [
            {"format_id": "1", "vcodec": "avc", "height": 720, "ext": "mp4"},
            {"format_id": "2", "vcodec": "avc", "height": 1080, "ext": "mp4"},
            {"format_id": "3", "vcodec": "none", "acodec": "mp4a", "abr": 128, "ext": "m4a"}
        ]
    }

    mock_run.return_value = mock_subprocess_success(fake_data)

    result = video_info.extract("http://youtube.com/test")

    assert result["title"] == "Teste"
    assert result["thumbnail"] == "url_thumb"
    assert result["duration"] == 120

    # formatos de vídeo
    assert len(result["formats"]) == 2

    # formatos de áudio
    assert len(result["audio_formats"]) == 1


# ==========================
# TESTE DE JSON INVÁLIDO
# ==========================

@patch("core.video_info.subprocess.run")
def test_extract_json_invalido(mock_run, video_info):
    mock = MagicMock()
    mock.returncode = 0
    mock.stdout = "não é json"
    mock.stderr = ""

    mock_run.return_value = mock

    with pytest.raises(Exception, match="Falha ao interpretar resposta"):
        video_info.extract("http://youtube.com/test")


# ==========================
# TESTE DE ERRO DO YT-DLP
# ==========================

@patch("core.video_info.subprocess.run")
def test_extract_erro_ytdlp(mock_run, video_info):
    mock_run.return_value = mock_subprocess_error("private video")

    with pytest.raises(Exception, match="Vídeo privado"):
        video_info.extract("http://youtube.com/test")


# ==========================
# TESTE DE PARSE DE ERROS
# ==========================

@pytest.mark.parametrize("stderr, esperado", [
    ("confirm you're not a bot", "YouTube bloqueou"),
    ("captcha required", "YouTube bloqueou"),
    ("429 too many requests", "Muitas requisições"),
    ("cookies invalid", "Erro com cookies"),
    ("unsupported url", "URL não suportada"),
    ("private video", "Vídeo privado"),
    ("sign in required", "É necessário estar logado"),
])
def test_parse_error(video_info, stderr, esperado):
    result = video_info._parse_error(stderr)
    assert esperado in result


# ==========================
# TESTE DE FILTRO DE FORMATOS
# ==========================

def test_formatacao_remove_duplicados(video_info):
    fake_info = {
        "formats": [
            {"format_id": "1", "vcodec": "avc", "height": 720, "ext": "mp4"},
            {"format_id": "2", "vcodec": "avc", "height": 720, "ext": "mp4"},  # duplicado
            {"format_id": "3", "vcodec": "avc", "height": 1080, "ext": "mp4"},
        ]
    }

    result = video_info._format_response(fake_info)

    heights = [f["height"] for f in result["formats"]]

    assert heights == [720, 1080]
    assert len(result["formats"]) == 2


# ==========================
# TESTE DE AUDIO
# ==========================

def test_formatacao_audio(video_info):
    fake_info = {
        "formats": [
            {"format_id": "a1", "vcodec": "none", "acodec": "mp4a", "abr": 128, "ext": "m4a"},
            {"format_id": "a2", "vcodec": "none", "acodec": "mp4a", "abr": 128, "ext": "m4a"},  # duplicado
            {"format_id": "a3", "vcodec": "none", "acodec": "mp4a", "abr": 192, "ext": "m4a"},
        ]
    }

    result = video_info._format_response(fake_info)

    abrs = [f["abr"] for f in result["audio_formats"]]

    assert abrs == [128, 192]
    assert len(result["audio_formats"]) == 2


# ==========================
# TESTE COM COOKIES
# ==========================

@patch("core.video_info.subprocess.run")
@patch("core.video_info.cookies_exists", return_value=True)
@patch("core.video_info.get_cookies_path", return_value="cookies.txt")
def test_extract_com_cookies(mock_path, mock_cookies, mock_run, video_info):
    mock_run.return_value = mock_subprocess_success({"formats": []})

    video_info.extract("http://youtube.com/test")

    args = mock_run.call_args[0][0]

    assert "--cookies" in args
    assert "cookies.txt" in args