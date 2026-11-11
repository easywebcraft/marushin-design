#!/usr/bin/env python3
"""株式会社丸信 ホームページ（作り直し）のページを書き出す。

  python3 build.py            →  確認用。リポジトリの直下に各ページと assets/ を作る（GitHub Pages でそのまま配信）
                                  「制作中」の帯・noindex・「要確認」の印・写真の仮枠が入る。check.html に要確認の一覧を出す
  python3 build.py --release [--site-url https://www.marushin-kaitai.com] [--force]
                              →  公開用を dist/ に書き出す。帯・noindex・印・仮枠を外す。
                                  要確認が残っている・フォームが未接続のときは一覧を出して止まる（--force で書き出しだけ行う）

共通部分（head・ヘッダー・メニュー・フッター・相談の案内）はここで一度だけ定義し、各ページの中身と組み合わせる。
文章・料金・事例・質問は data/*.json（今のサイト www.marushin-kaitai.com から移した内容）。足していない。
ファイル名は今のサイトと同じにしてある（about.html・price.html など）。転送の設定が少なくて済むため。
"""
import argparse
import hashlib
import html
import json
import shutil
import sys
from pathlib import Path

BASE = Path(__file__).parent
SRC = BASE / 'src'
DATA = BASE / 'data'
SITE = BASE  # GitHub Pages はリポジトリ直下を配信する。--release のときは dist/
RELEASE = False  # 公開用の書き出し（制作中の帯・noindex・要確認の印・仮枠を外す）
SITE_URL = ''  # 公開URL（末尾の / なし）。決まるまでは空で、canonical を出さない

COMPANY = '株式会社 丸信'
TEL = '0568-29-7788'
TEL_HREF = 'tel:0568297788'
FAX = '0568-29-7789'
HOURS = '営業時間 9:00〜17:00（定休日：土日曜・祝日）'  # 今のサイトの会社概要「営業時間 9:00～17:00」「定休日 土日曜・祝日」
POSTAL = '486-0932'  # 今のサイトには 480-0306 の表記もある。丸信さんに確認する（todo に出している）
ADDRESS = '愛知県春日井市松河戸町4133番2'
RECRUIT_URL = 'https://arwrk.net/recruit/yr19dq6rh1okksq'  # 今のサイトの「リクルート」のリンク先（AirWORK）
# お問い合わせフォームの送り先。決まるまでは空（＝未接続。画面に「未接続」と出し、「送信しました」とは出さない）
FORM_ENDPOINT = ''

# ページの一覧：(ファイル名, 名前, 英字, ヘッダーに出すか, 説明文)
PAGES = [
    ('index.html', 'ホーム', '', False,
     '解体のご相談なら、愛知県（春日井市・小牧市・尾張旭市・瀬戸市・名古屋市等）の株式会社丸信へ。施工事例・料金案内・施工の流れを掲載しています。'),
    ('about.html', '丸信について', 'ABOUT', True,
     '株式会社丸信の解体工事への考え方、近隣への配慮、対応する工事、対応エリアをご紹介します。'),
    ('price.html', '料金案内', 'PRICE', True,
     '木造・鉄骨造・鉄筋コンクリート造の解体工事の料金表と、庭木伐採・ブロック塀などその他の料金を掲載しています。'),
    ('case.html', '施工事例', 'WORKS', True,
     '株式会社丸信が施工した解体工事の事例を、施工前・施工後の写真でご紹介します。'),
    ('flow.html', '施工の流れ', 'FLOW', True,
     'ご相談・お見積もりから、届出、近隣へのご挨拶、解体工事、整地、工事終了のご挨拶までの流れをご説明します。'),
    ('outline.html', '会社案内', 'COMPANY', True,
     '株式会社丸信の会社概要、許可・登録、企業理念、所在地をご案内します。'),
    ('voice.html', 'お客様の声', 'VOICE', False,
     '解体工事を施工させていただいたお客様からいただいたお言葉をご紹介します。'),
    ('faq.html', 'よくある質問', 'FAQ', False,
     'お見積もり、対応エリア、工事の内容、工事前後の準備や手続きなど、解体工事についてよくいただくご質問にお答えします。'),
    ('contact.html', 'お問い合わせ', 'CONTACT', False,
     '解体工事のご相談・お見積もりは、お電話またはお問い合わせフォームからご連絡ください。'),
    ('policy.html', 'プライバシーポリシー', 'PRIVACY POLICY', False,
     '株式会社丸信のプライバシーポリシー（個人情報の取り扱い）です。'),
]
PAGE = {p[0]: p for p in PAGES}
# 下層ページの上の写真の見せる位置（同じ写真でも、ページごとに少し変える）
PH_POS = {'about.html': '70% 40%', 'price.html': '40% 55%', 'case.html': '60% 62%', 'flow.html': '80% 45%',
          'outline.html': '30% 50%', 'voice.html': '55% 35%', 'faq.html': '75% 58%', 'contact.html': '45% 42%',
          'policy.html': '65% 50%'}

ASSET_V = ''  # main() で CSS・JS の中身から決める
CUR = ''  # いま書き出しているページ（要確認の一覧に使う）
TODOS = []  # (ページ, 目印の番号, 内容)
FRAMES = []  # (ページ, 仮枠の説明)
esc = html.escape


def load(name):
    return json.loads((DATA / name).read_text(encoding='utf-8'))


def ic(name, cls='ic'):
    return f'<svg class="{cls}" aria-hidden="true" focusable="false"><use href="#i-{name}"/></svg>'


def todo(label):
    """まだ確かめられていないところの印。確認用にだけ出し、一覧（check.html）にも載せる。"""
    n = len(TODOS) + 1
    TODOS.append((CUR, n, label))
    if RELEASE:
        return ''
    return f'<span class="todo" id="todo-{n}"><span class="todo-tag">要確認</span>{esc(label)}</span>'


def frame(label, cls=''):
    """写真の仮枠。本物の写真が届いたら差し替える。公開用には出さない。"""
    FRAMES.append((CUR, label))
    if RELEASE:
        return ''
    return (f'<div class="phf {cls}" role="img" aria-label="写真を入れる場所（仮の枠）">'
            f'<span>写真を入れる場所<small>{esc(label)}</small></span></div>')


def body_html(items):
    """data の本文（段落・箇条書き・注記・囲み）を HTML にする。"""
    out = []
    for it in items:
        if isinstance(it, str):
            out.append(f'<p>{esc(it)}</p>')
        elif 'ul' in it:
            out.append('<ul class="dots">' + ''.join(f'<li>{esc(x)}</li>' for x in it['ul']) + '</ul>')
        elif 'note' in it:
            out.append(f'<p class="note">{esc(it["note"])}</p>')
        elif 'box' in it:
            out.append('<div class="box">' + ''.join(f'<p>{esc(x)}</p>' for x in it['box']) + '</div>')
    return '\n'.join(out)


# ---------- 共通の部品 ----------

SPRITE = '''<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0" style="position:absolute" aria-hidden="true" focusable="false">
<defs>
<symbol id="i-mail" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3.5 7.5l8.5 6 8.5-6"/></symbol>
<symbol id="i-phone" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2z"/></symbol>
<symbol id="i-chev" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 6l6 6-6 6"/></symbol>
<symbol id="i-chat" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M4 5h16v11H10l-5 4v-4H4z"/><path d="M8.5 10.5h.01M12 10.5h.01M15.5 10.5h.01"/></symbol>
<symbol id="i-users" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="3"/><path d="M6.5 19.5c0-3 2.5-5.5 5.5-5.5s5.5 2.5 5.5 5.5"/><circle cx="5" cy="10" r="2"/><path d="M2 17c0-1.8 1.3-3.2 3-3.4"/><circle cx="19" cy="10" r="2"/><path d="M22 17c0-1.8-1.3-3.2-3-3.4"/></symbol>
<symbol id="i-greet" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 11l9-7 9 7"/><path d="M5 9.5V20h14V9.5"/><path d="M12 17.2l-2.5-2.3a1.8 1.8 0 0 1 2.5-2.6 1.8 1.8 0 0 1 2.5 2.6z"/></symbol>
<symbol id="i-home" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 11l9-7 9 7"/><path d="M5 9.5V20h14V9.5"/><path d="M10 20v-6h4v6"/></symbol>
<symbol id="i-doc" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M6 3h9l4 4v14H6z"/><path d="M15 3v4h4"/><path d="M9 12h7M9 16h7"/></symbol>
<symbol id="i-pen" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M4 20l4.5-1L20 7.5 16.5 4 5 15.5z"/><path d="M14 6.5l3.5 3.5"/></symbol>
<symbol id="i-search" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="6"/><path d="M16 16l5 5"/></symbol>
<symbol id="i-clip" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="5" width="14" height="16" rx="2"/><rect x="9" y="3" width="6" height="4" rx="1"/><path d="M9 12h6M9 16h6"/></symbol>
<symbol id="i-excavator" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="17" width="12" height="4" rx="2"/><path d="M4 17v-6h5.5l2 6"/><path d="M9 11l4.5-7 5.5 4-1.5 5"/><path d="M17.5 13l4 1-1 4h-4z"/></symbol>
<symbol id="i-truck" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M2 7h11v9H2z"/><path d="M13 10h4l4 3v3h-8z"/><circle cx="6.5" cy="18" r="2"/><circle cx="17" cy="18" r="2"/></symbol>
<symbol id="i-ground" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M8 12.5l3 3 5-6"/></symbol>
<symbol id="i-pin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 21s7-6.2 7-11a7 7 0 1 0-14 0c0 4.8 7 11 7 11z"/><circle cx="12" cy="10" r="2.5"/></symbol>
<symbol id="i-ext" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M14 4h6v6M20 4l-9 9"/><path d="M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/></symbol>
</defs>
</svg>'''


# 冒頭の演出（トップだけ）。同じ訪問で2度目以降と、動きを減らす設定の人には出さない。
# 下の JS が動かなかったときに幕が残らないよう、6秒で必ず外す
EWL_HEAD = '''<script>
(function(){var r=document.documentElement,played=false;
try{played=sessionStorage.getItem('ms-ewl')==='1';}catch(e){}
if(played||(window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches))return;
r.classList.add('ewl-on','ewl-play');
if('scrollRestoration' in history)history.scrollRestoration='manual';
setTimeout(function(){r.classList.remove('ewl-on');},6000);})();
</script>
'''
EWL_BODY = '''<div class="ewl" id="ewl" aria-hidden="true">
<div class="ewl-p1"><svg class="ewl-ring" viewBox="0 0 120 120"><circle class="t" cx="60" cy="60" r="54"/><circle class="f" cx="60" cy="60" r="54"/></svg><span class="ewl-pct">0%</span></div>
<div class="ewl-p2"><div class="logo"><span class="logo-s">株式会社</span><span class="logo-l">丸信</span></div></div>
<span class="ewl-skip">タップでスキップ</span>
</div>
'''


def head(fname, title, desc):
    robots = '' if RELEASE else '<meta name="robots" content="noindex,nofollow">\n'
    canonical = ''
    if RELEASE and SITE_URL:
        path = '' if fname == 'index.html' else fname
        canonical = f'<link rel="canonical" href="{SITE_URL}/{path}">\n'
    return f'''<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
{robots}{canonical}<meta name="format-detection" content="telephone=no">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{esc(COMPANY)}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<link rel="stylesheet" href="assets/style.css?v={ASSET_V}">
{EWL_HEAD if fname == 'index.html' else ''}</head>'''


def header(fname):
    items = []
    for f, name, _en, in_head, _d in PAGES:
        if not in_head:
            continue
        cur = ' aria-current="page"' if f == fname else ''
        items.append(f'<li><a href="{f}"{cur}>{name}</a></li>')
    drawer = []
    for f, name, _en, _h, _d in PAGES:
        cur = ' aria-current="page"' if f == fname else ''
        drawer.append(f'<li><a href="{f}"{cur}>{name}{ic("chev")}</a></li>')
    drawer.append(f'<li><a href="{RECRUIT_URL}" target="_blank" rel="noopener">採用情報<span class="ext-note">（外部サイト）</span>{ic("ext")}</a></li>')
    draft = '' if RELEASE else ('<div class="draft"><span>制作中のページです（確認用）</span>'
                                '<a href="check.html">確認が必要なところの一覧</a></div>\n')
    return f'''<body>
{EWL_BODY if fname == 'index.html' else ''}{SPRITE}
<a class="skip" href="#main">本文へ移動</a>
{draft}<header class="hd">
<div class="hd-in">
<a class="logo" href="index.html" aria-label="{COMPANY} ホーム"><span class="logo-s">株式会社</span><span class="logo-l">丸信</span></a>
<nav class="gnav" aria-label="メインメニュー"><ul>
{''.join(items)}
</ul></nav>
<a class="btn btn-teal hd-cta" href="contact.html">{ic("mail")}お問い合わせ</a>
<button class="burger" type="button" aria-expanded="false" aria-controls="drawer" aria-label="メニューを開く"><span></span><span></span><span></span></button>
</div>
<nav class="drawer" id="drawer" aria-label="すべてのページ" hidden>
<ul>
{''.join(drawer)}
</ul>
<a class="drawer-tel" href="{TEL_HREF}">{ic("phone")}<span><b>{TEL}</b><small>{HOURS}</small></span></a>
</nav>
</header>
<main id="main">'''


def cta():
    return f'''<section class="cta" aria-labelledby="cta-h">
<div class="cta-box">
<h2 class="cta-ttl" id="cta-h">解体工事の<br>ご相談はこちら</h2>
<div class="cta-tel">
<a href="{TEL_HREF}">{ic("phone")}<span>{TEL}</span></a>
<p>{HOURS}</p>
</div>
<a class="btn btn-teal btn-lg" href="contact.html">{ic("mail")}お問い合わせ{ic("chev")}</a>
</div>
</section>'''


def footer(fname):
    links = []
    for f, name, _en, _h, _d in PAGES:
        if f == 'index.html':
            continue
        links.append(f'<li><a href="{f}">{name}</a></li>')
    links.append(f'<li><a href="{RECRUIT_URL}" target="_blank" rel="noopener">採用情報<span class="ext-note">（外部サイト）</span></a></li>')
    script = f'<script src="assets/main.js?v={ASSET_V}" defer></script>'
    return f'''</main>
<footer class="ft">
<div class="ft-in">
<div class="ft-brand">
<a class="logo logo-w" href="index.html" aria-label="{COMPANY} ホーム"><span class="logo-s">株式会社</span><span class="logo-l">丸信</span></a>
<address>〒{POSTAL} {ADDRESS}<br>TEL {TEL}　FAX {FAX}</address>
</div>
<nav class="ft-nav" aria-label="フッターメニュー"><ul>
{''.join(links)}
</ul></nav>
<a class="btn btn-white ft-cta" href="contact.html">{ic("mail")}お問い合わせ</a>
</div>
<p class="copy"><small>&copy; {COMPANY}</small></p>
</footer>
<div class="fixbar">
<a class="btn btn-white-line" href="{TEL_HREF}">{ic("phone")}電話で相談</a>
<a class="btn btn-teal" href="contact.html">{ic("mail")}お問い合わせ</a>
</div>
{script}
</body>
</html>
'''


def page_head(fname):
    """下層ページの上の帯（題・英字・写真）と、現在位置。"""
    _f, name, en, _h, _d = PAGE[fname]
    pos = PH_POS.get(fname, '50% 50%')
    return f'''<div class="ph">
<div class="ph-img"><img src="images/hero.jpg" alt="" width="1600" height="1066" style="object-position:{pos}"></div>
<div class="ph-in"><div class="ph-ttl"><h1>{name}</h1><p class="ph-en" lang="en">{en}</p></div></div>
<p class="img-note">写真はイメージです</p>
</div>
<nav class="bc" aria-label="現在位置"><ol><li><a href="index.html">ホーム</a></li><li aria-current="page">{name}</li></ol></nav>'''


def layout(fname, body, with_cta=True):
    _f, name, _en, _h, desc = PAGE[fname]
    if fname == 'index.html':
        title = f'{COMPANY}｜春日井市・名古屋市の解体工事相談室'
    else:
        title = f'{name}｜{COMPANY}（春日井市・名古屋市の解体工事）'
    return '\n'.join([head(fname, title, desc), header(fname), body, cta() if with_cta else '', footer(fname)])


def h2c(text, lead=''):
    lead = f'<p class="lead">{lead}</p>' if lead else ''
    return f'<h2 class="h2c">{text}</h2>{lead}'


def more(href, text, cls='btn-line'):
    return f'<a class="btn {cls}" href="{href}">{text}{ic("chev")}</a>'


def area_html(company):
    rows = ''.join(f'<div><dt>{esc(a["pref"])}</dt><dd>{esc(a["cities"])}</dd></div>' for a in company['area'])
    return f'<dl class="area">{rows}</dl>\n<p class="note center">{esc(company["area_note"])}</p>'


def work_card(w, lazy=True, level='h3'):
    title = f'{esc(w["place"])} {esc(w["name"])}'
    kind = f'<span class="work-kind">{esc(w["type"])}</span>' if w['type'] else ''
    note = f'<p class="note">{esc(w["note"])}</p>' if w['note'] else ''
    lz = ' loading="lazy" decoding="async"' if lazy else ''
    return f'''<article class="work">
<div class="work-ph">
<figure><img src="images/case/{w["id"]}-before.jpg" alt="施工前の写真：{title}" width="208" height="156"{lz}><figcaption>施工前</figcaption></figure>
<figure><img src="images/case/{w["id"]}-after.jpg" alt="施工後の写真：{title}" width="268" height="201"{lz}><figcaption class="after">施工後</figcaption></figure>
</div>
<div class="work-tx"><{level} class="work-ttl">{title}</{level}>{kind}{note}</div>
</article>'''


def qa_html(item, n):
    t = todo(item['todo']) if item.get('todo') else ''
    return f'''<details class="qa" id="q{n}">
<summary><span class="qa-q" aria-hidden="true">Q</span><span class="qa-t">{esc(item["q"])}</span><span class="qa-ic" aria-hidden="true"></span></summary>
<div class="qa-a"><span class="qa-m" aria-hidden="true">A</span><div class="qa-b">
{body_html(item["a"])}{t}
</div></div>
</details>'''


# ---------- 各ページ ----------

def page_index():
    company, works, flow, voice, faq = load('company.json'), load('works.json'), load('flow.json'), load('voice.json'), load('faq.json')
    cards = [
        ('chat', '解体専門の会社へ直接ご相談', '地域に根付いた解体専門の業者です。下請業者に発注するわけではありませんので、中間マージンが発生しません。'),
        ('users', '近隣への配慮', '工事前には必ず、近隣へ誠意を持って丁寧なご挨拶を行ったうえで解体工事を行います。万が一トラブルが発生した際も、速やかに対処いたします。'),
        ('greet', '工事前後のご挨拶', '解体工事の完了後にも、再度ご近所様へご挨拶をおこないます。「本当にご迷惑はなかったか？」を確認するためです。'),
    ]
    cards_html = ''.join(f'<li><span class="circ">{ic(i, "ic-l")}</span><h3>{t}</h3><p>{p}</p></li>' for i, t, p in cards)
    works_html = ''.join(work_card(w) for w in works[:3])
    steps = ''.join(f'<li><span class="circ">{ic(s["icon"], "ic-l")}</span><span class="fm-n">{i:02d}</span><span class="fm-t">{esc(s["short"])}</span></li>'
                    for i, s in enumerate(flow, 1))
    voices = ''.join(f'<li><span class="vq">{esc(v["title"])}</span><span class="vw">{esc(v["who"])}</span></li>' for v in voice)
    top_faq = [(n, it) for n, it in enumerate(faq['items'], 1) if it.get('top')]
    faq_html = ''.join(qa_html(it, n) for n, it in top_faq)
    return f'''<section class="hero">
<picture><source media="(max-width:767px)" srcset="images/hero-sp.jpg"><img class="hero-img" src="images/hero.jpg" alt="" width="1600" height="1066" fetchpriority="high"></picture>
<div class="hero-in">
<p class="hero-label">春日井市・名古屋市の解体工事相談室</p>
<h1>建物の解体は、<br>丸信へ。</h1>
<p class="hero-sub">愛知県（春日井市・小牧市・尾張旭市・瀬戸市・名古屋市等）の解体のご相談は、株式会社丸信にお任せください。</p>
<div class="hero-btns">
<a class="btn btn-teal btn-lg" href="contact.html">{ic("mail")}無料相談</a>
<a class="btn btn-white btn-lg" href="case.html">施工事例を見る{ic("chev")}</a>
</div>
</div>
<p class="img-note">写真はイメージです</p>
</section>

<section class="sec">
<div class="wrap">
{h2c('丸信の解体工事について')}
<p class="lead">当社は愛知県春日井市を中心に解体工事を承っています。<br>木造住宅、鉄骨建築、鉄筋コンクリート造や、テナント事務所・店舗など、建築様式を問わず解体工事が可能です。</p>
</div>
</section>

<section class="sec sec-pale sec-tight" aria-labelledby="h-torikumi">
<div class="wrap">
<h2 class="vh" id="h-torikumi">丸信の取り組み</h2>
<ul class="cards3">{cards_html}</ul>
<p class="center mt-l">{more('about.html', '丸信について詳しく見る')}</p>
</div>
</section>

<section class="sec">
<div class="wrap">
{h2c('施工事例', '株式会社丸信にて施工を行いました事例をご紹介します。')}
<div class="works works-3">{works_html}</div>
<p class="center mt-l">{more('case.html', '施工事例を見る')}</p>
</div>
</section>

<section class="band" aria-labelledby="h-price">
<div class="wrap band-in">
<h2 class="band-ttl" id="h-price">料金案内</h2>
<p class="band-tx">木造・鉄骨造・鉄筋コンクリート造の解体工事と、庭木伐採・ブロック塀などその他の料金表を掲載しています。</p>
{more('price.html', '料金案内を見る')}
</div>
</section>

<section class="sec">
<div class="wrap">
{h2c('施工の流れ', 'ご相談から工事完了後のご挨拶までの、主な流れです。')}
<ol class="flowmini">{steps}</ol>
<p class="center mt-l">{more('flow.html', '施工の流れを見る')}</p>
</div>
</section>

<section class="band" aria-labelledby="h-voice">
<div class="wrap band-in">
<h2 class="band-ttl" id="h-voice">お客様の声</h2>
<ul class="band-voices">{voices}</ul>
{more('voice.html', 'お客様の声を見る')}
</div>
</section>

<section class="sec sec-area">
<div class="wrap">
{h2c('対応エリア')}
{area_html(company)}
<p class="lead">上記の対応エリア以外にも柔軟に対応させていただきます。まずはお気軽にお問い合わせください。</p>
</div>
</section>

<section class="sec sec-pale">
<div class="wrap wrap-s">
{h2c('よくある質問')}
<div class="qas">{faq_html}</div>
<p class="center mt-m"><a class="tlink" href="faq.html">よくある質問をすべて見る{ic("chev")}</a></p>
</div>
</section>'''


def page_about():
    company = load('company.json')
    feats = [
        ('解体専門の会社へ直接ご依頼いただけます',
         ['一般的にハウスメーカーや工務店などは、自社内で解体工事が行えるところは少なく、多くの場合は下請けの解体業者が行います。その場合、中間マージンと呼ばれる上乗せ金が乗せられた金額が見積もりとして出ます。',
          '地域に根付いた解体専門の業者であれば、下請業者に発注するわけではありませんので、中間マージンが発生しません。'],
         '現地調査・ご相談の様子',
         '今のサイトは「解体費用は確実に安くなります」と言い切っています。この言い方を載せるか（ここでは外しています）'),
        ('近隣への配慮',
         ['解体工事は、細心の注意を払って作業を行っても振動や騒音、チリやホコリなどが必ず発生します。近隣からの苦情とトラブルが多く、しっかりとした対応が必要です。',
          '丸信では工事前には必ず、近隣へ誠意を持って丁寧な挨拶を行ったうえで解体工事を行います。また、万が一トラブルが発生した際も、速やかに対処いたしますのでご安心ください。'],
         '工事中の現場（養生シートなど）', ''),
        ('工事前後のご挨拶',
         ['株式会社 丸信では、解体工事完了後に再度ご近所様へのご挨拶をおこないます。',
          'これは、ご協力いただいて無事に工事が終わった感謝の気持ちと共に「本当にご迷惑はなかったか？」を確認するためです。'],
         '近隣へのご挨拶の様子', ''),
    ]
    feat_html = []
    for i, (t, ps, ph, td) in enumerate(feats, 1):
        fr = frame(ph, 'slant-r' if i % 2 else 'slant-l')
        cls = 'feat' + ('' if i % 2 else ' feat-rev') + ('' if fr else ' feat-nophoto')
        tdm = todo(td) if td else ''
        feat_html.append(f'''<div class="{cls}">
<div class="feat-tx"><p class="feat-num" aria-hidden="true">{i:02d}</p><div><h3>{t}</h3>{''.join(f'<p>{p}</p>' for p in ps)}{tdm}</div></div>
{fr}
</div>''')
    pol = [
        ('法令順守', '株式会社 丸信では法律・条令及びその他要求事項を順守し、社会的常識に基づき企業活動を行います。そのために社内従業員及び社外協力業者への法律・条例及びその他要求事項の周知を徹底し、お客様をはじめ利害関係者様にご迷惑をおかけすることなく、安心して工事をお任せいただける企業を目指します。'),
        ('顧客満足', 'お客様のご要望にお応えできますように、お客様との十分な対話・説明を心がけ、お客様に満足していただける解体工事を目指します。'),
        ('近隣協定', '作業現場の近隣住民の方に事前に丁寧な説明を行い、納得していただけるように努めます。また、作業中の近隣住民の方からのご意見にも誠意をもって対応し、近隣住民の方に配慮した解体工事を目指します。'),
        ('継続的な運用・改善', '法令・条例の施行、社会環境の変化に柔軟に対応し、社会と調和した成長を目指します。SDGsを目標に設け、それに向けマネジメントシステムの運用・改善を心がけ、継続的な技術・サービスの向上を目指します。'),
    ]
    pol_html = ''.join(f'<li><h3>{t}</h3><p>{p}</p></li>' for t, p in pol)
    intro_fr = frame('丸信の現場・スタッフの写真', 'slant-l')
    return f'''{page_head('about.html')}
<section class="sec">
<div class="wrap intro{'' if intro_fr else ' intro-nophoto'}">
{intro_fr}
<div class="intro-tx">
<h2 class="h2l">解体工事への想い</h2>
<p class="intro-lead">一番大切なことは、<br>ご近所様への気配りだと考えています。</p>
<p>今後も住み続ける、お客様の事を考えた時、一番大切なことはご近所様への気配りだと思います。</p>
<p>ご近所様へのご挨拶に始まり、解体工事専門としての熟練された技術と、職人一人ひとりがご近所にご迷惑をかけているという気持ちを持って作業をおこないます。</p>
<p>気配りには絶対の自信があります。どうぞ安心してご相談ください。</p>
</div>
</div>
</section>

<section class="feats" aria-labelledby="h-feats">
<h2 class="vh" id="h-feats">丸信の取り組み</h2>
{''.join(feat_html)}
</section>

<section class="sec">
<div class="wrap duo">
<div class="duo-col">
<h2 class="h2i">{ic("excavator", "ic-h")}対応する工事</h2>
<p>株式会社 丸信では、木造住宅、鉄骨建築、鉄筋コンクリート造や、テナント事務所・店舗など、建築様式を問わず解体工事が可能です。</p>
<p>思い出の詰まった建物ですが、建替えや減築、駐車場への移行など、住環境の変化により解体の必要性は生じてきます。</p>
<h3 class="h3b">手壊しによる解体</h3>
<p>隣接する建物にも注意を払い、手壊しによる解体を進めていきます。道幅が狭く、ブルドーザーや機械が入れない箇所や、家々が密接し解体を出来ない箇所、表面上には見えない細かな部分についても、手壊し解体にて作業を行います。機械では出来ない、細かな気配りの部分を人間が担当するというスタイルです。</p>
<p>価格についても㎡単価での計算ですので、お見積りの計算もスムーズです。お気軽にご相談ください。</p>
{todo('「㎡単価での計算」という説明（料金表は坪単価で載っています。どちらが正しいか）')}
<p class="mt-m">{more('price.html', '料金案内を見る')}</p>
</div>
<div class="duo-col">
<h2 class="h2i">{ic("pin", "ic-h")}対応エリア</h2>
{area_html(company)}
<p>上記の対応エリア以外にも柔軟に対応させていただきます。まずはお気軽にお問い合わせください。</p>
</div>
</div>
</section>

<section class="sec sec-pale">
<div class="wrap">
{h2c('丸信の方針')}
<ul class="pol">{pol_html}</ul>
</div>
</section>

<section class="sec">
<div class="wrap wrap-s">
{h2c('解体の悪徳業者にご注意ください')}
<p>悪徳業者の従来の手口は、施主（依頼者）が解体工事の相場を知らないことをいいことに、高額な請求をかけるというものです。ただ、最近はインターネット上で簡単に相場を調べることが出来るようになった為、同様の手口が使えなくなってきました。</p>
<p>その代わりに、非常に安価な見積もりを出して解体の依頼を受け、産業廃棄物処理費用を払わずに不法投棄をすることで利益を出しています。</p>
<p>不法投棄は違法であり、あまり知られていないことですが、業者だけでなく、施主も以下のような罰則があります。</p>
<div class="box"><p>【罰則】5年以下の懲役、または1000万円以下の罰金、またはその併科。</p></div>
{todo('罰則の書き方（「懲役」は2025年6月から法律上「拘禁刑」に変わっています）')}
<p>悪徳業者に騙されず、後悔しない解体工事にしていただければ幸いです。</p>
</div>
</section>

<section class="sec sec-pale">
<div class="wrap">
{h2c('土地活用に関するご提案')}
<div class="two">
<div class="panel"><h3>駐車場運営</h3>
<p>1世帯に2台のペースで車の所有が進んでいる世帯や地域にとって、最大の悩みは駐車場を確保する事であります。広い土地を確保出来ず、遠く離れた場所にレンタルスペースを確保される方も多いようです。</p>
<p>使わない土地、名義変更された土地を駐車場として運営する事は、ご自身にとっても、地域の活性化にとても有効です。</p></div>
<div class="panel"><h3>土木工事</h3>
<p>土地活用による土木工事をお考えの方は、ぜひ当社までご連絡ください。</p>
<p>フェンス、門扉、カーポートなどの外構・エクステリアの整備、設置から戸建てマンションへの変更まで。土地活用のご相談は何でも承ります。</p></div>
</div>
</div>
</section>'''


def page_price():
    price = load('price.json')
    rows = []
    for s in price['structures']:
        for i, (size, cost) in enumerate(s['rows']):
            th = (f'<th scope="rowgroup" rowspan="{len(s["rows"])}">{esc(s["name"])}<small>（{esc(s["unit"])}）</small></th>'
                  if i == 0 else '')
            rows.append(f'<tr>{th}<td>{esc(size)}</td><td class="num">{esc(cost)}</td></tr>')
    others = []
    for o in price['others']:
        for i, (what, cost) in enumerate(o['rows']):
            th = f'<th scope="rowgroup" rowspan="{len(o["rows"])}">{esc(o["name"])}</th>' if i == 0 else ''
            others.append(f'<tr>{th}<td>{esc(what) or "―"}</td><td class="num">{esc(cost)}</td></tr>')
    return f'''{page_head('price.html')}
<section class="sec">
<div class="wrap wrap-m">
<p class="lead">{esc(price["lead"])}</p>
{todo('料金の金額（今のサイトの料金表は2013年ごろのものです。今もこの金額でよいか）')}
{todo('税込・税別の表記（今のサイトの料金表には、どちらとも書かれていません）')}
<h2 class="h2l">建物の解体工事</h2>
<div class="tbl-wrap">
<table class="tbl tbl-price">
<caption class="vh">建物の解体工事の料金（坪単価）</caption>
<thead><tr><th scope="col">構造</th><th scope="col">坪数</th><th scope="col">費用（坪単価）</th></tr></thead>
<tbody>
{''.join(rows)}
</tbody>
</table>
</div>
<p class="incl">{esc(price["included"])}</p>

<h2 class="h2l mt-xl">その他の工事・処分</h2>
<div class="tbl-wrap">
<table class="tbl tbl-other">
<caption class="vh">その他の工事・処分の料金</caption>
<thead><tr><th scope="col">項目</th><th scope="col">内容</th><th scope="col">費用</th></tr></thead>
<tbody>
{''.join(others)}
</tbody>
</table>
</div>
<p class="note">※{esc(price["note"])}</p>
<p class="note">※解体工事着工までのご準備や、別途費用が発生する場合については、<a href="faq.html#prep">よくある質問</a>もご覧ください。</p>
</div>
</section>'''


def page_case():
    works = load('works.json')
    cards = ''.join(work_card(w, lazy=i > 1, level='h2') for i, w in enumerate(works))
    return f'''{page_head('case.html')}
<section class="sec">
<div class="wrap">
<p class="lead">株式会社丸信にて施工を行いました事例をご紹介します。<br>工事完了後の隣家外壁補修工事や駐車場整備工事など、お客様のニーズに幅広くお応えしております。</p>
<div class="works works-2">{cards}</div>
<p class="note center mt-l">※順次、施工事例を追加予定をしております。</p>
{todo('事例の写真（今のサイトの写真は小さいため、元の大きさの写真があれば差し替えます）')}
</div>
</section>'''


def page_flow():
    flow = load('flow.json')
    items = []
    for i, s in enumerate(flow, 1):
        items.append(f'''<li>
<span class="flow-num" aria-hidden="true">{i:02d}</span>
<div class="flow-body">
<h2><span class="vh">手順{i}：</span><span class="circ circ-s">{ic(s["icon"])}</span>{esc(s["title"])}</h2>
{body_html(s["body"])}
</div>
</li>''')
    return f'''{page_head('flow.html')}
<section class="sec">
<div class="wrap wrap-m">
<p>解体工事は家屋や建物などを壊すだけではありません。ご自分では処分が難しい大きな建築材の解体や、処分する為の分別作業、処分費用、運搬、手続きなどが発生します。手間、人手と莫大な労力を要するのが解体作業・解体工事であると言えます。</p>
<p>株式会社 丸信が行う解体工事の、施工の主な流れについてご説明します。</p>
<p class="note">※解体内容によっては異なる場合がございます。詳しくは<a href="contact.html">お問い合わせ</a>ください。</p>
<ol class="flow">
{''.join(items)}
</ol>
</div>
</section>

<section class="band" aria-labelledby="h-flowfaq">
<div class="wrap band-in">
<h2 class="band-ttl" id="h-flowfaq">よくある質問</h2>
<p class="band-tx">工事の内容や、工事前後の準備・手続きについて、よくいただくご質問をまとめています。</p>
{more('faq.html', 'よくある質問を見る')}
</div>
</section>'''


def page_voice():
    voice = load('voice.json')
    cards = ''.join(f'''<article class="voice">
<h2>{esc(v["title"])}</h2>
{''.join(f'<p>{esc(p)}</p>' for p in v["body"])}
<p class="voice-who">{esc(v["who"])}</p>
</article>''' for v in voice)
    return f'''{page_head('voice.html')}
<section class="sec">
<div class="wrap wrap-m">
<p class="lead">解体工事を施工させていただきましたお客様より、嬉しいお言葉をいただきましたので、ほんの一部ですがご紹介します。</p>
<div class="voices">{cards}</div>
<p class="note center mt-l">※お客様の声は今後、順次追加させていただきます。</p>
</div>
</section>'''


def page_faq():
    faq = load('faq.json')
    pills = ''.join(f'<li><a href="#{c["id"]}">{esc(c["name"])}</a></li>' for c in faq['categories'])
    secs = []
    for c in faq['categories']:
        qs = ''.join(qa_html(it, n) for n, it in enumerate(faq['items'], 1) if it['cat'] == c['id'])
        secs.append(f'<section class="faq-cat" id="{c["id"]}" aria-labelledby="h-{c["id"]}"><h2 class="h2l" id="h-{c["id"]}">{esc(c["name"])}</h2>\n<div class="qas">{qs}</div></section>')
    return f'''{page_head('faq.html')}
<section class="sec">
<div class="wrap wrap-s">
<p class="lead">解体工事について、よくいただくご質問をまとめました。質問を押すと、回答が開きます。</p>
<nav aria-label="質問の分類"><ul class="pills">{pills}</ul></nav>
{''.join(secs)}
</div>
</section>'''


def page_outline():
    c = load('company.json')

    def rows(items):
        out = []
        for r in items:
            if r.get('tel'):
                v = f'<a href="{TEL_HREF}">{esc(r["v"][0])}</a>'
            elif r.get('mail'):
                v = f'<a href="mailto:{esc(r["v"][0])}">{esc(r["v"][0])}</a>'
            else:
                v = '<br>'.join(esc(x) for x in r['v'])
            t = todo(r['todo']) if r.get('todo') else ''
            out.append(f'<div><dt>{esc(r["k"])}</dt><dd>{v}{t}</dd></div>')
        return ''.join(out)

    phil = ''.join(f'<h3 class="h3b">{esc(p["h"])}</h3>' + ''.join(f'<p>{esc(x)}</p>' for x in p['p']) for p in c['philosophy'])
    map_fr = frame('地図（住所の確認が済んでから入れます）', 'phf-map')
    return f'''{page_head('outline.html')}
<section class="sec">
<div class="wrap wrap-m">
<h2 class="h2l">社長あいさつ</h2>
{''.join(f'<p>{esc(p)}</p>' for p in c['greeting'])}
<p class="sign">株式会社 丸信　代表取締役　灰崎 信吉</p>
{todo('社長あいさつの文章（2013年ごろの文章です。このまま載せてよいか）')}
</div>
</section>

<section class="sec sec-pale">
<div class="wrap wrap-m">
<h2 class="h2l">会社概要</h2>
<dl class="dl">{rows(c['profile'])}</dl>
<h2 class="h2l mt-xl">許可・登録</h2>
<dl class="dl">{rows(c['permits'])}</dl>
<h2 class="h2l mt-xl">対象エリア</h2>
{area_html(c)}
</div>
</section>

<section class="sec">
<div class="wrap wrap-m">
<h2 class="h2l">企業理念・経営方針</h2>
{phil}
</div>
</section>

<section class="sec sec-pale">
<div class="wrap wrap-m">
<h2 class="h2l">所在地・アクセス</h2>
<p class="addr">{ic("pin")}〒{POSTAL} {ADDRESS}</p>
{map_fr}
{todo('所在地の郵便番号と地図（郵便番号が確かめられてから地図を入れます）')}
</div>
</section>'''


def page_contact():
    connected = bool(FORM_ENDPOINT)
    notice = '' if connected else ('<div class="unconnected" role="note"><b>このフォームの送信機能は未接続です。</b>'
                                   '「送信」を押しても、入力した内容はどこにも送られません。お急ぎの場合はお電話でご連絡ください。</div>')
    if not connected:
        TODOS.append((CUR, 0, 'お問い合わせフォームの送り先（未接続。送り先のメールアドレスと送信の仕組みを決める）'))

    def field(fid, label, kind='text', required=False, hint='', attrs='', area=False):
        req = '<span class="req">必須</span>' if required else '<span class="opt">任意</span>'
        hint_html = f'<p class="hint" id="{fid}-hint">{hint}</p>' if hint else ''
        desc = f'{fid}-err' + (f' {fid}-hint' if hint else '')
        r = ' required aria-required="true"' if required else ''
        if area:
            ctl = f'<textarea id="{fid}" name="{fid}" rows="7" aria-describedby="{desc}"{r}{attrs}></textarea>'
        else:
            ctl = f'<input id="{fid}" name="{fid}" type="{kind}" aria-describedby="{desc}"{r}{attrs}>'
        return f'''<div class="fld">
<label for="{fid}">{label}{req}</label>
{ctl}
{hint_html}<p class="err" id="{fid}-err" hidden></p>
</div>'''

    fields = ''.join([
        field('name', 'お名前', required=True, attrs=' autocomplete="name"'),
        field('email', 'メールアドレス', 'email', True, '半角英数でご記入ください。', ' autocomplete="email" inputmode="email"'),
        field('email2', 'メールアドレス確認用', 'email', True, 'お手数ですが、確認のため、もう一度ご記入ください。', ' autocomplete="email" inputmode="email"'),
        field('tel', '電話番号', 'tel', False, '', ' autocomplete="tel" inputmode="tel"'),
        field('fax', 'FAX番号', 'tel', False, '', ' inputmode="tel"'),
        field('zip', '郵便番号', 'text', False, '', ' autocomplete="postal-code" inputmode="numeric"'),
        field('address', '住所', 'text', False, '', ' autocomplete="street-address"'),
        field('message', 'お問合せ内容', required=True, area=True),
    ])
    endpoint = f' data-endpoint="{esc(FORM_ENDPOINT)}"' if connected else ''
    return f'''{page_head('contact.html')}
<section class="sec">
<div class="wrap wrap-m">
<p class="lead">どんな些細な事でも結構です。ご相談、お見積りなど、お気軽にご連絡ください。<br>下記のフォームからご連絡いただくか、お電話にてご連絡ください。</p>

<div class="telbox">
<h2>電話でのお問い合わせ</h2>
<a class="telbox-num" href="{TEL_HREF}">{ic("phone")}<span>{TEL}</span></a>
<p>{HOURS}</p>
<p class="note">お問い合わせの際は、電話番号をお間違いのないようお確かめください。</p>
</div>
</div>
</section>

<section class="sec sec-pale">
<div class="wrap wrap-m">
<div class="formcard">
<h2>メールでのお問い合わせ</h2>
{notice}
<p class="note">※お客様に関する個人情報につきましては「<a href="policy.html">プライバシーポリシー</a>」に基づき、適切に取り扱っております。</p>
<form id="contact-form" action="#" method="post" novalidate onsubmit="return false"{endpoint}>
<div class="form-sum" id="form-sum" role="alert" tabindex="-1" hidden></div>
{fields}
<p class="note">確認画面が出ませんので、入力内容をよくご確認の上、「送信」ボタンを押してください。</p>
<p class="center"><button class="btn btn-navy btn-lg btn-send" type="submit">送信</button></p>
<div class="form-result" id="form-result" role="status" aria-live="polite" tabindex="-1" hidden></div>
</form>
</div>

<h2 class="h2l mt-xl">個人情報の取り扱いに関して</h2>
<p>本入力フォームおよびメールでご連絡いただきました、お客様の個人情報につきましては、厳重に管理を行っております。法令等に基づき正規の手続きによって司法捜査機関による開示要求が行われた場合を除き、第三者に開示もしくは提供することはございません。</p>
</div>
</section>'''


def page_policy():
    pol = load('policy.json')
    secs = ''.join(f'<section class="pol-sec"><h2><span class="pol-n" aria-hidden="true">{i:02d}</span>{esc(s["h"])}</h2>\n{body_html(s["p"])}</section>'
                   for i, s in enumerate(pol, 1))
    return f'''{page_head('policy.html')}
<section class="sec">
<div class="wrap wrap-s">
{secs}
{todo('プライバシーポリシーの内容（2013年の文章を移しました。新しいフォームの扱いと合っているか）')}
</div>
</section>'''


# 文章の中の印では表せない、全体にかかわる確認事項（check.html と --release の案内に出す）
GENERAL = [
    'トップと各ページ上部の写真は、イメージ写真です（丸信さんの現場ではありません）。現場の写真が届いたら差し替えます',
    '今のサイトにある既製の写真・イラスト（家族の写真など）は使っていません',
    '採用情報は、今のサイトと同じ外部の採用ページ（AirWORK）へのリンクです。残すかどうかを丸信さんに確認します',
    '解体用語集（9ページ）とサイトマップのページは、新しいサイトには作っていません。古いURLは転送します',
    '今のサイトの明らかな誤字は直しています（「最新の注意」→「細心の注意」、「お待たせず」→「お待たせせず」など）',
]


def page_check():
    """要確認の一覧（確認用にだけ作る）。"""
    by = {}
    for f, n, label in TODOS:
        by.setdefault(f, []).append((n, label))
    secs = []
    for f, name, _en, _h, _d in PAGES:
        if f not in by:
            continue
        lis = ''.join(f'<li><a href="{f}{"#todo-%d" % n if n else ""}">{esc(label)}</a></li>' for n, label in by[f])
        secs.append(f'<h2 class="h2l">{name}</h2><ul class="dots">{lis}</ul>')
    fr = {}
    for f, label in FRAMES:
        fr.setdefault(f, []).append(label)
    fr_html = ''.join(f'<li><a href="{f}">{PAGE[f][1]}</a>：{esc("、".join(v))}</li>' for f, v in fr.items())
    gen = ''.join(f'<li>{esc(g)}</li>' for g in GENERAL)
    body = f'''<div class="ph ph-plain"><div class="ph-in"><div class="ph-ttl"><h1>確認が必要なところの一覧</h1><p class="ph-en">制作中の確認用ページ（公開しません）</p></div></div></div>
<section class="sec"><div class="wrap wrap-m">
<p>今のサイトから移した内容のうち、公開の前に丸信さんに確かめたいところです。各ページでは黄色の「要確認」の印が付いています。</p>
{''.join(secs)}
<h2 class="h2l mt-xl">写真の仮枠が残っているところ</h2>
<ul class="dots">{fr_html}</ul>
<h2 class="h2l mt-xl">全体にかかわること</h2>
<ul class="dots">{gen}</ul>
</div></section>'''
    return '\n'.join([head('check.html', '確認が必要なところの一覧｜' + COMPANY, '制作中の確認用ページです。'),
                      header('check.html'), body, footer('check.html')])


BUILDERS = {
    'index.html': page_index, 'about.html': page_about, 'price.html': page_price, 'case.html': page_case,
    'flow.html': page_flow, 'outline.html': page_outline, 'voice.html': page_voice, 'faq.html': page_faq,
    'contact.html': page_contact, 'policy.html': page_policy,
}


def write(rel, text):
    p = SITE / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding='utf-8')


def main():
    global RELEASE, SITE, SITE_URL, ASSET_V, CUR
    ap = argparse.ArgumentParser()
    ap.add_argument('--release', action='store_true', help='公開用を dist/ に書き出す')
    ap.add_argument('--site-url', default='', help='公開URL（canonical に使う。末尾の / なし）')
    ap.add_argument('--force', action='store_true', help='要確認が残っていても書き出す')
    args = ap.parse_args()
    RELEASE = args.release
    SITE_URL = args.site_url.rstrip('/')
    if RELEASE:
        SITE = BASE / 'dist'
        SITE.mkdir(exist_ok=True)

    css = (SRC / 'style.css').read_text(encoding='utf-8')
    js = (SRC / 'main.js').read_text(encoding='utf-8')
    ASSET_V = hashlib.md5((css + js).encode('utf-8')).hexdigest()[:8]
    write('assets/style.css', css)
    write('assets/main.js', js)

    for fname, builder in BUILDERS.items():
        CUR = fname
        write(fname, layout(fname, builder(), with_cta=(fname != 'contact.html')))

    if RELEASE:
        if (SITE / 'images').exists():
            shutil.rmtree(SITE / 'images')
        shutil.copytree(BASE / 'images', SITE / 'images')
        print(f'公開用を {SITE} に書き出しました。')
        if TODOS or FRAMES:
            print('\n公開の前に確かめることが残っています：')
            for f, _n, label in TODOS:
                print(f'  ・{PAGE[f][1]}：{label}')
            for f, label in FRAMES:
                print(f'  ・{PAGE[f][1]}：写真の仮枠（{label}）※公開用では枠を出していません')
            if not args.force:
                print('\n（書き出しは行いました。このまま公開せず、上の項目を片づけてください。--force を付けるとこの案内だけになります）')
                sys.exit(1)
    else:
        CUR = 'check.html'
        write('check.html', page_check())
        print(f'確認用を {SITE} に書き出しました。要確認 {len(TODOS)} 件・写真の仮枠 {len(FRAMES)} か所。')


if __name__ == '__main__':
    main()
