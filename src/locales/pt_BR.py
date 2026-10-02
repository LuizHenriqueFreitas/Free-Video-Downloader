# locales/pt_BR.py - Português (Brasil), default language (see core/i18n.py)

STRINGS = {
    # ---------------------------------------------------------------- common
    "common.error": "Erro",
    "common.cancel": "Cancelar",
    "common.close": "Fechar",
    "common.format": "Formato:",
    "common.destination_folder": "Pasta de destino:",
    "common.choose_folder": "Escolher pasta",
    "common.dont_show_again": "Não mostrar esta mensagem novamente",
    "common.dont_show_warning_again": "Não exibir este aviso novamente",
    "common.untitled": "Sem título",
    "common.untitled_entry": "(sem título)",

    # ---------------------------------------------------------------- main window
    "main.paste_link": "+ Colar link",
    "main.check_updates": "Buscar atualizações",
    "main.checking_updates": "Buscando...",
    "main.import_cookies": "Importar cookies",
    "main.remove_cookies": "Remover cookies",
    "main.cookies_unknown": "Cookies: ...",
    "main.cookies_ok": "Cookies: OK",
    "main.cookies_missing": "Cookies: NÃO CONFIGURADO",
    "main.history_limit": "Histórico:",
    "main.clear_history": "Limpar histórico",
    "main.clear_history_text": (
        "Todo o histórico de downloads será apagado, mas os vídeos "
        "continuam em seu computador, se quiser deletá-los faça manualmente."
    ),
    "main.language": "Idioma:",
    "main.language_changed_title": "Idioma alterado",
    "main.language_changed_text": (
        "O novo idioma será aplicado quando o Get Media Free for aberto novamente.\n\n"
        "Reiniciar agora interrompe os downloads em andamento."
    ),
    "main.restart_now": "Reiniciar agora",
    "main.restart_later": "Depois",
    "main.ytdlp_update_error": "Erro ao atualizar yt-dlp: {error}",
    "main.update_available_title": "Atualização disponível",
    "main.update_available_text": (
        "Nova versão ({version}) disponível para download. "
        "Atualize para novos recursos e correções.\n\n"
        "yt-dlp: {ytdlp}"
    ),
    "main.updates_title": "Atualizações",
    "main.up_to_date_text": "yt-dlp: {ytdlp}\n\nO app já está na versão mais recente (v{version}).",
    "main.select_cookies_file": "Selecionar cookies.txt",
    "main.text_files_filter": "Arquivos de texto (*.txt)",
    "main.success": "Sucesso",
    "main.cookies_imported": "Cookies importados com segurança!",
    "main.removed": "Removido",
    "main.cookies_removed": "Cookies removidos.",
    "main.info": "Info",
    "main.no_cookies_found": "Nenhum cookie encontrado.",
    "main.cookies_required_title": "Cookies necessários",
    "main.cookies_required_text": "Você precisa importar o arquivo cookies.txt antes de baixar vídeos.",
    "main.remove_from_history_title": "Remover do histórico",
    "main.remove_from_history_text": (
        'Remover "{title}" da lista?\n\n'
        "(O arquivo já baixado NÃO será apagado do disco.)"
    ),

    # ---------------------------------------------------------------- download dialog
    "dialog.title": "Novo Download",
    "dialog.url_label": "URL do vídeo (YouTube, TikTok, Instagram, etc.):",
    "dialog.advanced_mode": "Selecionar trecho do vídeo (modo avançado)",
    "dialog.quality": "Qualidade:",
    "dialog.filename_label": "Nome do arquivo (opcional):",
    "dialog.add": "Adicionar",
    "dialog.loading_info": "Carregando informações...",
    "dialog.loading": "Carregando...",
    "dialog.info_loaded": "✔ Informações carregadas",
    "dialog.error": "Erro: {error}",
    "dialog.filename_invalid_live": "O nome do arquivo não pode conter: {chars}",
    "dialog.playlist_detected_title": "Playlist detectada",
    "dialog.playlist_detected_text": (
        "🔗 **Playlist detectada!**\n\n"
        "A URL informada pertence a uma playlist do YouTube.\n\n"
        "O que você deseja baixar?"
    ),
    "dialog.only_this_video": "📹 Apenas este vídeo",
    "dialog.whole_playlist": "📋 Toda a playlist",
    "dialog.cookies_not_set": "⚠ Cookies não configurados",
    "dialog.cancelled_by_user": "Cancelado pelo usuário",
    "dialog.loading_playlist": "Carregando playlist...",
    "dialog.playlist_empty": "Nenhum vídeo encontrado na playlist.",
    "dialog.playlist_loaded": "✔ Playlist carregada: {count} vídeos",
    "dialog.playlist_error": "Erro ao carregar playlist: {error}",
    "dialog.unknown_size": "tamanho desconhecido",
    "dialog.needs_conversion_suffix": " — necessário conversão",
    "dialog.no_formats": "Nenhum formato disponível",
    "dialog.conversion_title": "Esta qualidade precisa de conversão",
    "dialog.conversion_text": (
        "O site não oferece essa resolução no formato aceito pelos editores "
        "de vídeo (Premiere, Vegas, CapCut e outros).\n\n"
        "Depois do download, o Get Media Free vai converter o vídeo no seu "
        "computador para que ele possa ser usado na edição. Isso pode levar "
        "bastante tempo, às vezes mais do que a duração do próprio vídeo, "
        "dependendo do seu computador.\n\n"
        "O progresso e o tempo restante aparecem no card do download."
    ),
    "dialog.invalid_url_or_folder": "URL ou pasta inválida",
    "dialog.load_info_first": "Carregue as informações do vídeo primeiro",
    "dialog.invalid_name_title": "Nome inválido",
    "dialog.invalid_name_text": "O nome do arquivo não pode conter os caracteres:\n\n{chars}",
    "dialog.invalid_clip_title": "Trecho inválido",
    "dialog.invalid_clip_text": "O trecho selecionado precisa ter pelo menos 1 segundo.",
    "dialog.file_exists_title": "Arquivo já existe",
    "dialog.file_exists_text": "Já existe um arquivo com este nome e tipo:\n\n{path}\n\nO que deseja fazer?",
    "dialog.replace_file": "Substituir arquivo",
    "dialog.rename_automatically": "Renomear automaticamente",
    "dialog.go_back_rename": "Voltar e trocar o nome",

    # ---------------------------------------------------------------- playlist dialog
    "playlist.title": "Baixar playlist",
    "playlist.header": "Playlist: {title}  ({count} vídeos)",
    "playlist.select_all": "Selecionar todos",
    "playlist.clear_selection": "Limpar seleção",
    "playlist.quality_notice": (
        "ℹ️ Os vídeos serão baixados na MELHOR QUALIDADE disponível (máx. 1080p) "
        "com os nomes originais do YouTube."
    ),
    "playlist.download_selected": "Baixar selecionados",
    "playlist.warning_title": "Download da playlist",
    "playlist.warning_text": (
        "📋 **Atenção ao baixar a playlist**\n\n"
        "• Todos os vídeos serão baixados na **melhor qualidade disponível até 1080p**\n"
        "• Os nomes originais do YouTube serão preservados\n"
        "• Vídeos em 4K/8K serão convertidos para 1080p para economizar espaço\n\n"
        "Deseja continuar?"
    ),
    "playlist.choose_folder_first": "Escolha a pasta de destino.",
    "playlist.select_at_least_one": "Selecione ao menos um vídeo.",
    "playlist.best_quality_label": "Melhor qualidade (até 1080p)",

    # ---------------------------------------------------------------- download card
    "card.original": "Original: {title}",
    "card.open_file": "Abrir arquivo",
    "card.open_folder": "Abrir pasta",
    "card.retry": "Tentar novamente",
    "card.copy_link": "Copiar link",
    "card.link_copied": "Link copiado!",
    "card.remove": "Remover",
    "card.status_queued": "Na fila...",
    "card.status_downloading": "Baixando...",
    "card.status_completed": "Concluído",
    "card.status_error": "Falha no download",
    "card.status_cancelled": "Cancelado",
    "card.cancelling": "Cancelando...",
    "card.cutting": "Cortando trecho…",
    "card.converting": "Convertendo para H.264…",
    "card.calculating_time": "calculando tempo…",
    "card.seconds_left": "~{seconds} s restantes",
    "card.minutes_left": "~{minutes} min restantes",
    "card.hours_left": "~{hours} h {minutes} min restantes",

    # ---------------------------------------------------------------- clip trimmer
    "trimmer.unknown_duration": "Duração desconhecida — corte indisponível.",
    "trimmer.play": "▶ Reproduzir",
    "trimmer.pause": "⏸ Pausar",
    "trimmer.preview_clip": "Pré-visualizar trecho",
    "trimmer.caption": "Trecho a baixar (arraste os marcadores):",
    "trimmer.mark_start": "Início = agora",
    "trimmer.mark_end": "Fim = agora",
    "trimmer.start": "Início: {time}",
    "trimmer.end": "Fim: {time}",
    "trimmer.hint": "Arraste os marcadores ou use os botões para definir o trecho.",
    "trimmer.loading_preview": "Carregando pré-visualização…",
    "trimmer.loading_preview_hint": "Carregando pré-visualização… a barra de corte já pode ser usada.",
    "trimmer.preview_unavailable": "Preview indisponível",
    "trimmer.preview_unavailable_link": "Preview indisponível para este link — use a barra de tempo.",
    "trimmer.preview_unavailable_error": "Preview indisponível ({error}).",
    "trimmer.fallback_hint": "{message} A seleção do trecho continua funcionando.",
    "trimmer.cant_play": "Não foi possível reproduzir o vídeo aqui.",
    "trimmer.unsupported_stream": "Formato de stream não suportado para preview.",

    # ---------------------------------------------------------------- thumbnail
    "thumbnail.no_image": "Sem imagem",

    # ---------------------------------------------------------------- download worker
    "worker.ytdlp_failed": "Falha no download (yt-dlp retornou erro)",
    "worker.ytdlp_failed_detail": "Falha no download (yt-dlp retornou erro): {detail}",
    "worker.final_file_not_found": "Arquivo final não encontrado",
    "worker.full_video_failed": "Falha no download do vídeo completo",
    "worker.full_video_failed_detail": "Falha no download do vídeo completo: {detail}",
    "worker.temp_file_not_found": "Arquivo temporário não encontrado",
    "worker.cut_failed": "ffmpeg falhou ao cortar o trecho",
    "worker.convert_failed": "Falha ao converter o vídeo para MP4 (H.264)",
    "worker.probe_failed": "Não foi possível analisar o arquivo baixado (ffprobe)",
    "worker.merge_failed": "Falha ao juntar vídeo e áudio (FFmpeg não encontrado ou com erro)",

    # ---------------------------------------------------------------- video info (yt-dlp)
    "video.empty_url": "URL vazia",
    "video.extract_failed": "Erro ao extrair informações do vídeo",
    "video.read_response_failed": "Falha ao ler a resposta do yt-dlp",
    "video.read_playlist_failed": "Falha ao ler os dados da playlist",
    "video.blocked_by_youtube": "Bloqueado pelo youtube.",
    "video.too_many_requests": "Muitas tentativas, tente \n novamente daqui algum tempo.",
    "video.cookies_error": "Erro com cookies.",
    "video.unsupported_link": "Link não suportado.",
    "video.private": "Vídeo privado/ inacessível.",
    "video.login_required": "Login necessário, tente colocar cookies mais recentes.",

    # ---------------------------------------------------------------- embedded tools
    "utils.reinstall_hint": "Reinstale o Get Media Free para restaurar os arquivos do programa.",
    "utils.ytdlp_not_found_at": "yt-dlp não encontrado em: {path}",
    "utils.ytdlp_dev_hint": "Verifique se o arquivo está em: src/bin/yt-dlp.exe",
    "utils.ytdlp_not_found_linux": "yt-dlp não encontrado. Instale com: pip install yt-dlp",
    "utils.ffmpeg_not_found_at": "FFmpeg não encontrado em: {path}",
    "utils.ffmpeg_dev_hint": (
        "Verifique se ffmpeg.exe e ffprobe.exe estão em: src/tools/ffmpeg/bin/ "
        "(rode packaging/fetch_deps.ps1)"
    ),
    "utils.ffmpeg_not_found_linux": "FFmpeg não encontrado. Instale com: sudo apt install ffmpeg",
    "utils.ffprobe_not_found": "FFprobe não encontrado. Ele deve ficar junto do ffmpeg.",
    "utils.node_outdated": (
        "Node.js encontrado em '{path}' está desatualizado "
        "(precisa ser versão {version} ou superior)."
    ),
    "utils.node_outdated_windows_hint": "baixe em https://nodejs.org/ ou rode packaging/fetch_deps.ps1",
    "utils.node_outdated_linux_hint": (
        "Linux: use nvm (https://github.com/nvm-sh/nvm) para instalar uma versão recente"
    ),
    "utils.node_not_found": "Node.js não encontrado!",
    "utils.node_dev_hint": "Coloque o node.exe em src/bin/node/ (rode packaging/fetch_deps.ps1)",
    "utils.node_linux_hint": "Linux: Instale com 'sudo apt install nodejs' ou use nvm",

    # ---------------------------------------------------------------- updater
    "updater.download_failed": "Falha ao baixar yt-dlp",
    "updater.ytdlp_updated": "yt-dlp atualizado com sucesso!",
    "updater.update_error": "Erro na atualização: {error}",
    "updater.not_found": "Não encontrado",
    "updater.version_error": "Erro: {error}",
    "updater.ytdlp_not_found": "yt-dlp não encontrado: {error}",
    "updater.timeout": "Tempo esgotado",
    "updater.unexpected_error": "Erro inesperado: {error}",

    # ---------------------------------------------------------------- audio language dialog
    "audio.title": "Idioma do áudio",
    "audio.text": "Este vídeo tem o áudio disponível em {count} idiomas.\nEscolha qual deseja baixar:",
    "audio.original": "{name} (original)",
    "audio.confirm": "Baixar neste idioma",
    # audio track languages (yt-dlp codes, lowercase) - see core/i18n.audio_language_name()
    "audio_lang.ar": "Árabe",
    "audio_lang.bn": "Bengali",
    "audio_lang.cs": "Tcheco",
    "audio_lang.da": "Dinamarquês",
    "audio_lang.de": "Alemão",
    "audio_lang.el": "Grego",
    "audio_lang.en": "Inglês",
    "audio_lang.en-gb": "Inglês (Reino Unido)",
    "audio_lang.en-us": "Inglês (EUA)",
    "audio_lang.es": "Espanhol",
    "audio_lang.es-419": "Espanhol (América Latina)",
    "audio_lang.es-es": "Espanhol (Espanha)",
    "audio_lang.es-us": "Espanhol (EUA)",
    "audio_lang.fa": "Persa",
    "audio_lang.fi": "Finlandês",
    "audio_lang.fil": "Filipino",
    "audio_lang.fr": "Francês",
    "audio_lang.fr-ca": "Francês (Canadá)",
    "audio_lang.fr-fr": "Francês (França)",
    "audio_lang.gu": "Guzerate",
    "audio_lang.he": "Hebraico",
    "audio_lang.hi": "Hindi",
    "audio_lang.hu": "Húngaro",
    "audio_lang.id": "Indonésio",
    "audio_lang.it": "Italiano",
    "audio_lang.ja": "Japonês",
    "audio_lang.kn": "Canarês",
    "audio_lang.ko": "Coreano",
    "audio_lang.ml": "Malaiala",
    "audio_lang.mr": "Marati",
    "audio_lang.ms": "Malaio",
    "audio_lang.nl": "Holandês",
    "audio_lang.no": "Norueguês",
    "audio_lang.pa": "Punjabi",
    "audio_lang.pl": "Polonês",
    "audio_lang.pt": "Português",
    "audio_lang.pt-br": "Português (Brasil)",
    "audio_lang.pt-pt": "Português (Portugal)",
    "audio_lang.ro": "Romeno",
    "audio_lang.ru": "Russo",
    "audio_lang.sv": "Sueco",
    "audio_lang.ta": "Tâmil",
    "audio_lang.te": "Telugo",
    "audio_lang.th": "Tailandês",
    "audio_lang.tr": "Turco",
    "audio_lang.uk": "Ucraniano",
    "audio_lang.ur": "Urdu",
    "audio_lang.vi": "Vietnamita",
    "audio_lang.zh": "Chinês",
    "audio_lang.zh-hans": "Chinês (simplificado)",
    "audio_lang.zh-hant": "Chinês (tradicional)",
}
