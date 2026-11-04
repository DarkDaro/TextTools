# -*- coding: utf-8 -*-
"""Заменяет оставшиеся эмодзи-иконки в deepseek_html_TD.html на inline-SVG
в тёмно-фэнтезийном стиле (золото/кровь/лёд). Запуск: python replace_emoji_icons.py
Скрипт идемпотентен: повторный запуск ничего не меняет. Бэкап: *.html.bak
"""
import io, os, shutil, re

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'deepseek_html_TD.html')
BAK = SRC + '.bak'

def svg(body, vb='0 0 24 24'):
    return '<svg class="sicon" viewBox="' + vb + '" xmlns="http://www.w3.org/2000/svg">' + body + '</svg>'

GOLD='#ffcf7a'; GOLD_D='#9a6a10'; RED='#ff5a4a'; BLUE='#8ecbff'
MANA='#a58cff'; GREEN='#7dd87a'; FIRE='#ff8a3c'; STONE='#c9c2b4'

ICONS = {}
ICONS['💰'] = '<span class="ic ic-gold">' + svg('<circle cx="12" cy="12" r="8" fill="' + GOLD + '" stroke="' + GOLD_D + '" stroke-width="2"/><circle cx="12" cy="12" r="4.5" fill="none" stroke="' + GOLD_D + '" stroke-width="1.5"/><path d="M12 9v6" stroke="' + GOLD_D + '" stroke-width="1.5"/>') + '</span>'
ICONS['❤️'] = '<span class="ic ic-red">' + svg('<path d="M12 20C6 15 3.5 11.5 3.5 8.5 3.5 6 5.5 4 8 4c1.7 0 3.2 1 4 2.4C12.8 5 14.3 4 16 4c2.5 0 4.5 2 4.5 4.5 0 3-2.5 6.5-8.5 11.5z" fill="' + RED + '" stroke="#5a0e0e" stroke-width="1.4"/>') + '</span>'
ICONS['🌊'] = '<span class="ic ic-blue">' + svg('<path d="M2 15c2.5 0 2.5-2 5-2s2.5 2 5 2 2.5-2 5-2 2.5 2 5 2" fill="none" stroke="' + BLUE + '" stroke-width="2.2" stroke-linecap="round"/><path d="M2 19c2.5 0 2.5-2 5-2s2.5 2 5 2 2.5-2 5-2 2.5 2 5 2" fill="none" stroke="' + BLUE + '" stroke-width="2.2" stroke-linecap="round" opacity="0.6"/>') + '</span>'
ICONS['🔮'] = '<span class="ic ic-mana">' + svg('<circle cx="12" cy="12" r="8" fill="' + MANA + '" stroke="#3a2470" stroke-width="2"/><ellipse cx="9.5" cy="9" rx="2.6" ry="1.6" fill="#ffffff" opacity="0.75"/><path d="M6 19l6 3 6-3" fill="none" stroke="#3a2470" stroke-width="2" stroke-linecap="round"/>') + '</span>'
ICONS['⏯️'] = '<span class="ic">' + svg('<rect x="5" y="5" width="4.5" height="14" rx="1" fill="' + STONE + '"/><rect x="14.5" y="5" width="4.5" height="14" rx="1" fill="' + STONE + '"/>') + '</span>'
ICONS['▶'] = '<span class="ic">' + svg('<path d="M7 4l13 8-13 8z" fill="' + STONE + '"/>') + '</span>'
ICONS['⏩'] = '<span class="ic">' + svg('<path d="M4 4l9 8-9 8z" fill="' + STONE + '"/><path d="M12 4l9 8-9 8z" fill="' + STONE + '"/>') + '</span>'
ICONS['🔁'] = '<span class="ic">' + svg('<path d="M6 12a6 6 0 0110.5-4" fill="none" stroke="' + STONE + '" stroke-width="2.4" stroke-linecap="round"/><path d="M17 4v4h-4" fill="none" stroke="' + STONE + '" stroke-width="2.4" stroke-linecap="round"/><path d="M18 12a6 6 0 01-10.5 4" fill="none" stroke="' + STONE + '" stroke-width="2.4" stroke-linecap="round"/><path d="M7 20v-4h4" fill="none" stroke="' + STONE + '" stroke-width="2.4" stroke-linecap="round"/>') + '</span>'
ICONS['🔄'] = '<span class="ic">' + svg('<path d="M20 12a8 8 0 11-2.3-5.6" fill="none" stroke="' + GOLD + '" stroke-width="2.6" stroke-linecap="round"/><path d="M20 3v5h-5" fill="none" stroke="' + GOLD + '" stroke-width="2.6" stroke-linecap="round"/>') + '</span>'
ICONS['🔊'] = '<span class="ic ic-gold">' + svg('<path d="M4 9v6h4l5 4V5L8 9z" fill="' + STONE + '"/><path d="M16 9a4 4 0 010 6" fill="none" stroke="' + GOLD + '" stroke-width="2" stroke-linecap="round"/><path d="M18.5 6.5a8 8 0 010 11" fill="none" stroke="' + GOLD + '" stroke-width="2" stroke-linecap="round"/>') + '</span>'
ICONS['🔇'] = '<span class="ic ic-dim">' + svg('<path d="M4 9v6h4l5 4V5L8 9z" fill="' + STONE + '"/><path d="M16 9l6 6M22 9l-6 6" stroke="' + RED + '" stroke-width="2.2" stroke-linecap="round"/>') + '</span>'
ICONS['⚡'] = '<span class="ic ic-gold">' + svg('<path d="M13 2L5 14h5l-1.5 8L19 9h-5.5z" fill="' + GOLD + '" stroke="' + GOLD_D + '" stroke-width="1.2"/>') + '</span>'
ICONS['❄️'] = '<span class="ic ic-blue">' + svg('<g stroke="' + BLUE + '" stroke-width="2" stroke-linecap="round"><path d="M12 2v20M4 6l16 12M20 6L4 18"/></g>') + '</span>'
ICONS['🔥'] = '<span class="ic ic-fire">' + svg('<path d="M12 2c1 4-3 5.5-3 9a3 3 0 006 0c0-1.5-.8-2.5-.8-2.5 2.3 1 4.3 3.4 4.3 6A6.5 6.5 0 015.5 15C5.5 9 11 7.5 12 2z" fill="' + FIRE + '" stroke="#7a2400" stroke-width="1.3"/><path d="M12 21a3 3 0 01-3-3c0-1.6 1.6-2.6 3-4 1.4 1.4 3 2.4 3 4a3 3 0 01-3 3z" fill="#ffd75e"/>') + '</span>'
ICONS['💨'] = '<span class="ic ic-dim">' + svg('<path d="M3 9h11a2.5 2.5 0 10-2.5-2.5M3 13h15a2.5 2.5 0 11-2.5 2.5M3 17h8" fill="none" stroke="' + STONE + '" stroke-width="2" stroke-linecap="round"/>') + '</span>'
ICONS['🛡️'] = '<span class="ic ic-blue">' + svg('<path d="M12 3l7 3v5c0 5-3.2 8.4-7 10-3.8-1.6-7-5-7-10V6z" fill="#4a6a9a" stroke="' + BLUE + '" stroke-width="1.6"/><path d="M12 3v18" stroke="' + BLUE + '" stroke-width="1.2"/>') + '</span>'
ICONS['💚'] = '<span class="ic">' + svg('<path d="M12 20C6 15 3.5 11.5 3.5 8.5 3.5 6 5.5 4 8 4c1.7 0 3.2 1 4 2.4C12.8 5 14.3 4 16 4c2.5 0 4.5 2 4.5 4.5 0 3-2.5 6.5-8.5 11.5z" fill="' + GREEN + '" stroke="#1d4a1d" stroke-width="1.4"/>') + '</span>'
ICONS['✨'] = '<span class="ic ic-gold">' + svg('<path d="M12 3l1.6 5.4L19 10l-5.4 1.6L12 17l-1.6-5.4L5 10l5.4-1.6z" fill="' + GOLD + '"/><circle cx="19" cy="18" r="1.6" fill="' + GOLD + '"/><circle cx="5" cy="17" r="1.2" fill="' + GOLD + '"/>') + '</span>'
ICONS['🌙'] = '<span class="ic ic-blue">' + svg('<path d="M20 14.5A8.5 8.5 0 019.5 4 8.5 8.5 0 1020 14.5z" fill="' + BLUE + '" stroke="#2a4a70" stroke-width="1.4"/>') + '</span>'
ICONS['🌫️'] = '<span class="ic ic-dim">' + svg('<path d="M3 9c3 0 3-2 6-2s3 2 6 2 3-2 6-2M3 14c3 0 3-2 6-2s3 2 6 2 3-2 6-2M3 19c3 0 3-2 6-2s3 2 6 2 3-2 6-2" fill="none" stroke="' + STONE + '" stroke-width="1.8" stroke-linecap="round" opacity="0.85"/>') + '</span>'

ORDER = sorted(ICONS.keys(), key=len, reverse=True)

CSS = '''
        /* --- SVG-иконки фэнтези-UI (replace_emoji_icons.py) --- */
        .ic { display: inline-flex; vertical-align: -0.18em; }
        .ic .sicon { width: 1.12em; height: 1.12em; display: block; filter: drop-shadow(0 1px 1px rgba(0,0,0,0.8)); }
        .ic-gold { color: #ffcf7a; }
        .ic-red { color: #ff5a4a; }
        .ic-blue { color: #8ecbff; }
        .ic-mana { color: #a58cff; }
        .ic-fire { color: #ff8a3c; }
        .ic-dim { color: #c9c2b4; opacity: 0.85; }
'''

def main():
    s = io.open(SRC, encoding='utf-8').read()
    if '.ic .sicon' in s:
        print('Уже обработано, выходим'); return
    shutil.copyfile(SRC, BAK)

    lines = s.split('\n')
    out = []
    emoji_pat = re.compile('|'.join(re.escape(e) for e in ORDER))
    converted = 0
    for ln in lines:
        if '.textContent = ' in ln and (emoji_pat.search(ln) or 'wave-display' in ln or 't.textContent = msg' in ln):
            ln = ln.replace('.textContent = ', '.innerHTML = ', 1)
            converted += 1
        out.append(ln)
    s = '\n'.join(out)

    counts = {}
    def rep(m):
        e = m.group(0); counts[e] = counts.get(e, 0) + 1
        return ICONS[e]
    s = emoji_pat.sub(rep, s)

    s = s.replace('</style>', CSS + '    </style>', 1)

    io.open(SRC, 'w', encoding='utf-8').write(s)
    print('textContent->innerHTML:', converted)
    for e, c in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(' ', repr(e), c, 'замены')
    print('Бэкап:', BAK)

if __name__ == '__main__':
    main()
