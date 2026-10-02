// ============================================
// I18N - Português / English
// ============================================
// Static texts use data-i18n (text) or data-i18n-html (trusted markup from this
// file) on the element; attributes use data-i18n-attr="attr:key;attr:key".
// Dynamic texts (script.js) use t(key, {placeholders}).

const I18N = {
    pt: {
        'meta.title': 'Get Media Free - Baixe vídeos e músicas de graça',
        'meta.description': 'Baixe vídeos e músicas do YouTube, Instagram, TikTok e outras redes em MP4 H.264 pronto para edição ou MP3. Grátis, open-source e sem telemetria.',

        'nav.features': 'Funcionalidades',
        'nav.screenshots': 'Imagens',
        'nav.videos': 'Vídeos',
        'nav.about': 'Sobre',
        'nav.language': 'Idioma do site',

        'hero.subtitle': 'Baixe conteúdo de graça das principais redes sociais.<br />Tudo roda no seu PC <span class="badge">sem telemetria</span>',
        'hero.description': 'Vídeos em MP4 H.264 pronto para edição ou músicas em MP3, na máxima qualidade disponível. Rápido, seguro e 100% gratuito.',
        'hero.downloads': 'downloads registrados',
        'hero.version': 'Última versão:',
        'hero.download': 'Download para Windows',
        'hero.downloadFile': 'Download para Windows ({file})',
        'hero.free': 'Grátis',
        'hero.offline': 'Dados em cache (offline)',
        'hero.noFile': 'Nenhum arquivo disponível',
        'hero.social': 'Redes do projeto',

        'features.title': 'Por que usar o <span class="highlight">Get Media Free</span>?',
        'features.new': 'Novo',
        'features.privacy.title': 'Privacidade total',
        'features.privacy.text': 'Tudo é processado no seu computador. Nenhum dado é enviado para servidores e não existe telemetria.',
        'features.h264.title': 'Pronto para edição',
        'features.h264.text': 'Todo vídeo sai em MP4 com H.264 + AAC, o formato aceito por Premiere, DaVinci Resolve, Vegas e CapCut. Quando o site não oferece H.264, o app converte mantendo a resolução.',
        'features.audio.title': 'Idioma do áudio',
        'features.audio.text': 'Vídeos dublados do YouTube têm várias trilhas de áudio. O app pergunta qual idioma você quer baixar e já deixa a trilha original selecionada.',
        'features.playlists.title': 'Playlists e filas',
        'features.playlists.text': 'Cole o link de uma playlist ou fila do YouTube, escolha os vídeos e baixe todos de uma vez, na melhor qualidade até 1080p.',
        'features.storage.title': 'Espaço estimado',
        'features.storage.text': 'Antes de baixar, veja quanto espaço cada qualidade vai ocupar no disco, já somando vídeo e áudio.',
        'features.queue.title': 'Fila de downloads',
        'features.queue.text': 'Adicione quantos links quiser: até 3 downloads rodam ao mesmo tempo e o restante espera na fila.',
        'features.networks.title': 'Várias redes',
        'features.networks.text': 'Compatível com YouTube, Instagram, X (Twitter), TikTok, Facebook e muitos outros sites.',
        'features.free.title': 'Grátis e open-source',
        'features.free.text': 'Sem assinaturas e sem taxas escondidas. Todo o código está aberto no GitHub.',

        'screens.title': 'Veja o <span class="highlight">Get Media Free</span> em ação',
        'screens.subtitle': 'Algumas telas do aplicativo em uso',
        'screens.main.title': 'Tela principal',
        'screens.main.text': 'Interface limpa, com histórico de downloads',
        'screens.main.alt': 'Tela principal do Get Media Free',
        'screens.download.title': 'Novo download',
        'screens.download.text': 'Escolha formato, qualidade e veja o tamanho estimado',
        'screens.download.alt': 'Janela de novo download',
        'screens.queue.title': 'Fila de downloads',
        'screens.queue.text': 'Acompanhe vários downloads ao mesmo tempo',
        'screens.queue.alt': 'Fila de downloads',
        'screens.audio.title': 'Idioma do áudio',
        'screens.audio.text': 'Escolha a trilha de vídeos dublados',
        'screens.audio.alt': 'Diálogo de idioma do áudio',
        'screens.settings.title': 'Configurações',
        'screens.settings.text': 'Idioma, cookies e limite do histórico',
        'screens.settings.alt': 'Configurações do aplicativo',
        'screens.playlists.title': 'Playlists',
        'screens.playlists.text': 'Selecione e baixe playlists inteiras',
        'screens.playlists.alt': 'Download de playlist',
        'screens.prev': 'Imagem anterior',
        'screens.next': 'Próxima imagem',
        'screens.goto': 'Ir para a imagem {n}',

        'videos.title': 'Tutoriais em <span class="highlight">vídeo</span>',
        'videos.watch': 'Assistir',
        'videos.watchYoutube': 'Assistir no YouTube',
        'videos.v1.title': 'Como baixar vídeos do YouTube',
        'videos.v1.text': 'Aprenda a usar o Get Media Free para baixar vídeos em 4K.',
        'videos.v2.title': 'Baixando Reels e TikToks',
        'videos.v2.text': 'Baixe vídeos verticais em alta qualidade em poucos passos.',
        'videos.v3.title': 'Reportando bugs e erros',
        'videos.v3.text': 'O aplicativo parou de funcionar? Siga o passo a passo.',
        'videos.close': 'Fechar vídeo',

        'about.title': 'Sobre o <span class="highlight">desenvolvimento</span>',
        'about.p1': '<strong>Get Media Free</strong> é um projeto open-source desenvolvido em <strong>Python</strong> com ferramentas da comunidade, como o motor de download <strong>yt-dlp</strong> e o <strong>FFmpeg</strong>. Todo o código está no GitHub para contribuições e estudo.',
        'about.p2': 'Desenvolvido por um estudante de Análise e Desenvolvimento de Sistemas como material de estudo, pensado para oferecer uma ferramenta estável, confiável e gratuita para profissionais de edição de vídeo.',
        'about.github': 'Ver no GitHub',
        'about.stars': 'Estrelas no GitHub',
        'about.contributors': 'Contribuidores',
        'about.updated': 'Última atualização',

        'footer.text': '&copy; 2026 Get Media Free - Feito para ser prático e grátis.<br />Projeto open-source, sem afiliação com as plataformas mencionadas.<br />Contato: luiz.h.o.freitas@gmail.com',

        'date.today': 'Hoje',
        'date.yesterday': 'Ontem',
        'date.days': '{n} dias atrás',
        'date.week': '1 semana atrás',
        'date.weeks': '{n} semanas atrás',
        'date.month': '1 mês atrás',
        'date.months': '{n} meses atrás',
        'date.year': '1 ano atrás',
        'date.years': '{n} anos atrás',
    },

    en: {
        'meta.title': 'Get Media Free - Download videos and music for free',
        'meta.description': 'Download videos and music from YouTube, Instagram, TikTok and more as edit-ready H.264 MP4 or MP3. Free, open-source and with no telemetry.',

        'nav.features': 'Features',
        'nav.screenshots': 'Screenshots',
        'nav.videos': 'Videos',
        'nav.about': 'About',
        'nav.language': 'Site language',

        'hero.subtitle': 'Download content for free from the major social networks.<br />Everything runs on your PC <span class="badge">no telemetry</span>',
        'hero.description': 'Edit-ready H.264 MP4 videos or MP3 music, in the best quality available. Fast, safe and 100% free.',
        'hero.downloads': 'downloads so far',
        'hero.version': 'Latest version:',
        'hero.download': 'Download for Windows',
        'hero.downloadFile': 'Download for Windows ({file})',
        'hero.free': 'Free',
        'hero.offline': 'Cached data (offline)',
        'hero.noFile': 'No file available',
        'hero.social': 'Project links',

        'features.title': 'Why use <span class="highlight">Get Media Free</span>?',
        'features.new': 'New',
        'features.privacy.title': 'Full privacy',
        'features.privacy.text': 'Everything is processed on your computer. No data is sent to any server and there is no telemetry.',
        'features.h264.title': 'Ready for editing',
        'features.h264.text': 'Every video comes out as MP4 with H.264 + AAC, the format Premiere, DaVinci Resolve, Vegas and CapCut accept. When a site doesn\'t offer H.264, the app converts it and keeps the resolution.',
        'features.audio.title': 'Audio language',
        'features.audio.text': 'Dubbed YouTube videos have several audio tracks. The app asks which language you want and preselects the original track.',
        'features.playlists.title': 'Playlists and queues',
        'features.playlists.text': 'Paste a YouTube playlist or queue link, pick the videos and download them all at once, in the best quality up to 1080p.',
        'features.storage.title': 'Storage estimate',
        'features.storage.text': 'Before downloading, see how much disk space each quality will take, video and audio included.',
        'features.queue.title': 'Download queue',
        'features.queue.text': 'Add as many links as you want: up to 3 downloads run at the same time and the rest wait in line.',
        'features.networks.title': 'Many platforms',
        'features.networks.text': 'Works with YouTube, Instagram, X (Twitter), TikTok, Facebook and many other sites.',
        'features.free.title': 'Free and open-source',
        'features.free.text': 'No subscriptions and no hidden fees. All the code is open on GitHub.',

        'screens.title': 'See <span class="highlight">Get Media Free</span> in action',
        'screens.subtitle': 'A few screens of the app in use',
        'screens.main.title': 'Main screen',
        'screens.main.text': 'A clean interface with your download history',
        'screens.main.alt': 'Get Media Free main screen',
        'screens.download.title': 'New download',
        'screens.download.text': 'Pick format and quality and see the estimated size',
        'screens.download.alt': 'New download window',
        'screens.queue.title': 'Download queue',
        'screens.queue.text': 'Follow several downloads at once',
        'screens.queue.alt': 'Download queue',
        'screens.audio.title': 'Audio language',
        'screens.audio.text': 'Choose the track of dubbed videos',
        'screens.audio.alt': 'Audio language dialog',
        'screens.settings.title': 'Settings',
        'screens.settings.text': 'Language, cookies and history limit',
        'screens.settings.alt': 'App settings',
        'screens.playlists.title': 'Playlists',
        'screens.playlists.text': 'Select and download whole playlists',
        'screens.playlists.alt': 'Playlist download',
        'screens.prev': 'Previous screenshot',
        'screens.next': 'Next screenshot',
        'screens.goto': 'Go to screenshot {n}',

        'videos.title': 'Video <span class="highlight">tutorials</span>',
        'videos.watch': 'Watch',
        'videos.watchYoutube': 'Watch on YouTube',
        'videos.v1.title': 'How to download YouTube videos',
        'videos.v1.text': 'Learn how to use Get Media Free to download videos in 4K.',
        'videos.v2.title': 'Downloading Reels and TikToks',
        'videos.v2.text': 'Download vertical videos in high quality in a few steps.',
        'videos.v3.title': 'Reporting bugs and errors',
        'videos.v3.text': 'The app stopped working? Follow the step by step.',
        'videos.close': 'Close video',

        'about.title': 'About the <span class="highlight">project</span>',
        'about.p1': '<strong>Get Media Free</strong> is an open-source project built with <strong>Python</strong> and community tools such as the <strong>yt-dlp</strong> download engine and <strong>FFmpeg</strong>. All the code is on GitHub for contributions and study.',
        'about.p2': 'Built by a Systems Analysis and Development student as study material, designed to offer a stable, reliable and free tool for video editing professionals.',
        'about.github': 'View on GitHub',
        'about.stars': 'GitHub stars',
        'about.contributors': 'Contributors',
        'about.updated': 'Last update',

        'footer.text': '&copy; 2026 Get Media Free - Made to be practical and free.<br />Open-source project, not affiliated with the platforms mentioned.<br />Contact: luiz.h.o.freitas@gmail.com',

        'date.today': 'Today',
        'date.yesterday': 'Yesterday',
        'date.days': '{n} days ago',
        'date.week': '1 week ago',
        'date.weeks': '{n} weeks ago',
        'date.month': '1 month ago',
        'date.months': '{n} months ago',
        'date.year': '1 year ago',
        'date.years': '{n} years ago',
    },
};

const LANG_STORAGE_KEY = 'gmf_lang';
const SUPPORTED_LANGS = ['pt', 'en'];
const HTML_LANG = { pt: 'pt-BR', en: 'en' };
const NUMBER_LOCALE = { pt: 'pt-BR', en: 'en-US' };

// saved choice, else browser language (Portuguese -> pt, anything else -> en)
function detectLanguage() {
    try {
        const saved = localStorage.getItem(LANG_STORAGE_KEY);
        if (SUPPORTED_LANGS.includes(saved)) return saved;
    } catch (e) { /* storage blocked: fall through */ }
    const browser = (navigator.language || 'pt').toLowerCase();
    return browser.startsWith('pt') ? 'pt' : 'en';
}

let currentLang = detectLanguage();

function t(key, vars = {}) {
    const text = (I18N[currentLang] && I18N[currentLang][key]) ?? I18N.pt[key] ?? key;
    return text.replace(/\{(\w+)\}/g, (m, name) => (name in vars ? vars[name] : m));
}

function numberLocale() {
    return NUMBER_LOCALE[currentLang];
}

// fills every translatable element of the page
function applyTranslations() {
    document.documentElement.lang = HTML_LANG[currentLang];
    document.title = t('meta.title');
    const description = document.querySelector('meta[name="description"]');
    if (description) description.setAttribute('content', t('meta.description'));

    document.querySelectorAll('[data-i18n]').forEach(el => {
        el.textContent = t(el.dataset.i18n);
    });
    document.querySelectorAll('[data-i18n-html]').forEach(el => {
        el.innerHTML = t(el.dataset.i18nHtml);
    });
    document.querySelectorAll('[data-i18n-attr]').forEach(el => {
        el.dataset.i18nAttr.split(';').forEach(pair => {
            const [attr, key] = pair.split(':').map(s => s.trim());
            if (attr && key) el.setAttribute(attr, t(key));
        });
    });

    document.querySelectorAll('.lang-option').forEach(btn => {
        const active = btn.dataset.lang === currentLang;
        btn.classList.toggle('active', active);
        btn.setAttribute('aria-pressed', active ? 'true' : 'false');
    });
}

function setLanguage(lang) {
    if (!SUPPORTED_LANGS.includes(lang) || lang === currentLang) return;
    currentLang = lang;
    try { localStorage.setItem(LANG_STORAGE_KEY, lang); } catch (e) { /* ignore */ }
    applyTranslations();
    document.dispatchEvent(new CustomEvent('languagechange', { detail: { lang } }));
}

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.lang-option').forEach(btn => {
        btn.addEventListener('click', () => setLanguage(btn.dataset.lang));
    });
    applyTranslations();
});
