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
import re
import sys
from pathlib import Path
from urllib.parse import quote

BASE = Path(__file__).parent
SRC = BASE / 'src'
DATA = BASE / 'data'
SITE = BASE  # GitHub Pages はリポジトリ直下を配信する。--release のときは dist/
RELEASE = False  # 公開用の書き出し（制作中の帯・noindex・要確認の印・仮枠を外す）
SITE_URL = ''  # 公開URL（末尾の / なし）。決まるまでは空で、canonical を出さない
PREVIEW_URL = 'https://easywebcraft.github.io/marushin-design'  # 確認用の公開先（OGP画像の場所に使う）

COMPANY = '株式会社 丸信'
TEL = '0568-29-7788'
TEL_HREF = 'tel:0568297788'
FAX = '0568-29-7789'
HOURS = '営業時間 9:00〜17:00（定休日：土日曜・祝日）'  # 今のサイトの会社概要「営業時間 9:00～17:00」「定休日 土日曜・祝日」
POSTAL = '486-0932'  # 今のサイトには 480-0306 の表記もあったが、2026-11-18 松本さんが 486-0932 と確認
ADDRESS = '愛知県春日井市松河戸町4133番2'
RECRUIT_URL = 'https://arwrk.net/recruit/yr19dq6rh1okksq'  # 今のサイトの「リクルート」のリンク先（AirWORK）。2026-11-17 当面は AirWORK を続ける（松本さん）
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
    ('faq.html', 'よくある質問', 'FAQ', True,
     'お見積もり、対応エリア、工事の内容、工事前後の準備や手続きなど、解体工事についてよくいただくご質問にお答えします。'),
    ('contact.html', 'お問い合わせ', 'CONTACT', False,
     '解体工事のご相談・お見積もりは、お電話またはお問い合わせフォームからご連絡ください。'),
    ('policy.html', 'プライバシーポリシー', 'PRIVACY POLICY', False,
     '株式会社丸信のプライバシーポリシー（個人情報の取り扱い）です。'),
]
PAGE = {p[0]: p for p in PAGES}
# 下層ページの上の写真の見せる位置（同じ写真でも、ページごとに少し変える）
PH_POS = '75% 58%'   # 下層ページ上の写真の切り取り位置。2026-11-20 松本さん「見え方を統一して」で全ページ同じに（重機の全体が入る位置）

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
    box = (f'<div class="phf {cls}" role="img" aria-label="写真を入れる場所（仮の枠）">'
           f'<span>写真を入れる場所<small>{esc(label)}</small></span></div>')
    # 斜めに切った枠は影が切り取られるので、外側の箱に影を付ける（2026-11-12 全ページを立体的に）
    return f'<div class="phw">{box}</div>' if cls.startswith('slant') else box


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
<symbol id="i-calc" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="3" width="14" height="18" rx="2"/><rect x="8" y="6" width="8" height="3.5" rx=".5"/><path d="M8.5 13h.01M12 13h.01M15.5 13h.01M8.5 16.5h.01M12 16.5h.01M15.5 16.5h.01"/></symbol>
<symbol id="i-clip" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="5" width="14" height="16" rx="2"/><rect x="9" y="3" width="6" height="4" rx="1"/><path d="M9 12h6M9 16h6"/></symbol>
<symbol id="i-excavator" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="17" width="12" height="4" rx="2"/><path d="M4 17v-6h5.5l2 6"/><path d="M9 11l4.5-7 5.5 4-1.5 5"/><path d="M17.5 13l4 1-1 4h-4z"/></symbol>
<symbol id="i-truck" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M2 7h11v9H2z"/><path d="M13 10h4l4 3v3h-8z"/><circle cx="6.5" cy="18" r="2"/><circle cx="17" cy="18" r="2"/></symbol>
<symbol id="i-ground" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M8 12.5l3 3 5-6"/></symbol>
<symbol id="i-pin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 21s7-6.2 7-11a7 7 0 1 0-14 0c0 4.8 7 11 7 11z"/><circle cx="12" cy="10" r="2.5"/></symbol>
<symbol id="i-ext" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M14 4h6v6M20 4l-9 9"/><path d="M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/></symbol>
</defs>
</svg>'''


# 冒頭の演出（トップだけ）。同じ訪問で2度目以降と、動きを減らす設定の人には出さない。
# 下の JS が動かなかったときに幕が残らないよう、6秒たっても動き出していなければ外す。
# 先頭の js の印は、ヘッダーを写真の上に重ねてよい合図（JS が動かないと白地に戻せないため）
EWL_HEAD = '''<script>
(function(){var r=document.documentElement,played=false;
r.classList.add('js');
try{played=sessionStorage.getItem('ms-ewl')==='1';}catch(e){}
if(played||(window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches))return;
r.classList.add('ewl-on','ewl-play');
if('scrollRestoration' in history)history.scrollRestoration='manual';
setTimeout(function(){if(!window.__ewl)r.classList.remove('ewl-on');},6000);})();
</script>
'''
EWL_BODY = '''<div class="ewl" id="ewl" aria-hidden="true">
<div class="ewl-p1"><svg class="ewl-ring" viewBox="0 0 120 120"><circle class="t" cx="60" cy="60" r="54"/><circle class="f" cx="60" cy="60" r="54"/></svg><span class="ewl-pct">0%</span></div>
<div class="ewl-p2"><div class="logo"><span class="logo-s">株式会社</span><span class="logo-l">丸信</span></div></div>
<span class="ewl-skip">タップでスキップ</span>
</div>
'''


def href(f):
    """ページへのリンク先。トップは ./ にする（index.html だとトップに2つのアドレスができる）"""
    return './' if f == 'index.html' else f


# ---- 色の切り替え（確認用だけ。2026-11-20 松本さん「ボタンでお客様に切り替えてもらい、好みの色を選んでもらいたい」）----
# 主に使う色（--navy＝濃い色、--teal 系＝差し色、--pale 系＝薄い地の色）だけを入れ替える。公開用には入らない。
THEMES = [
    ('base', '紺×青緑（今の色）', '#17354B', '#147F8D', {}),
    ('brick', '紺×赤茶', '#1E2B3C', '#A9502A', {'navy': '#1E2B3C', 'navy-d': '#141E2B', 'teal': '#D0784F', 'teal-d': '#A9502A', 'teal-dd': '#8A3E1F',
                                           'pale': '#F4ECE6', 'pale2': '#FAF6F2', 'line': '#E5D8CE', 'tint': '#F2DCCF', 'bg1': '#F8F2EE', 'bg2': '#EBDFD6'}),
    ('orange', '黒×オレンジ（重機の色）', '#24282D', '#C66A0A', {'navy': '#24282D', 'navy-d': '#17191C', 'teal': '#F29A2E', 'teal-d': '#C66A0A', 'teal-dd': '#A3560A',
                                                  'pale': '#F5F1EA', 'pale2': '#FAF8F4', 'line': '#E4DDD2', 'tint': '#FBE3C4', 'bg1': '#F9F6F1', 'bg2': '#ECE5DA'}),
    ('green', '深緑×緑', '#1E3A2F', '#2F7A4A', {'navy': '#1E3A2F', 'navy-d': '#142820', 'teal': '#5E9C6E', 'teal-d': '#2F7A4A', 'teal-dd': '#22603A',
                                          'pale': '#E9F2EC', 'pale2': '#F4F9F5', 'line': '#D3E3D8', 'tint': '#D4EBDC', 'bg1': '#F0F6F2', 'bg2': '#DCE9E0'}),
]


def theme_head():
    """色の切り替えの見た目と、ページを開いた直後に選んだ色を当てる短い処理（ちらつかないよう head に置く）"""
    css = ''.join(f':root[data-theme="{k}"]{{' + ''.join(f'--{n}:{v};' for n, v in vs.items()) + '}' for k, _n, _a, _b, vs in THEMES if vs)
    css += ('.tsw{position:fixed;right:14px;bottom:14px;z-index:80;font-size:13px}'
            '.tsw-btn{display:flex;align-items:center;gap:8px;min-height:44px;padding:0 16px;border:0;border-radius:999px;background:#fff;color:#22313C;font:inherit;font-weight:700;'
            'box-shadow:0 6px 18px rgba(0,0,0,.18);cursor:pointer}'
            '.tsw-dot{width:18px;height:18px;border-radius:50%;background:linear-gradient(135deg,var(--navy) 50%,var(--teal-d) 50%)}'
            '.tsw-list{position:absolute;right:0;bottom:calc(100% + 8px);width:280px;margin:0;padding:8px;list-style:none;background:#fff;border-radius:10px;box-shadow:0 10px 30px rgba(0,0,0,.2)}'
            '.tsw-list[hidden]{display:none}'
            '.tsw-list p{margin:4px 8px 6px;color:#566874;font-size:12px}'
            '.tsw-list button{display:flex;align-items:center;gap:10px;width:100%;min-height:44px;padding:4px 8px;border:0;border-radius:6px;background:none;color:#22313C;font:inherit;text-align:left;cursor:pointer}'
            '.tsw-list button:hover{background:#F3F5F7}'
            '.tsw-list button[aria-pressed="true"]{background:#EEF3F6;font-weight:700}'
            '.tsw-sw{flex:none;width:34px;height:22px;border-radius:4px;box-shadow:inset 0 0 0 1px rgba(0,0,0,.1)}'
            '.tsw-list p.tsw-h{margin:8px 8px 2px;color:#22313C;font-weight:700;font-size:12px}'
            '.tsw-bi{flex:none;display:grid;place-items:center;width:34px;height:22px;border-radius:4px;background:#22313C;color:#fff;font-weight:700;font-size:12px}'
            '@media (max-width:767px){.tsw{right:10px;bottom:84px}}'
            '@media print{.tsw{display:none}}')
    keys = [k for k, *_ in THEMES]
    js = ('(function(){var k=null;try{var m=location.search.match(/[?&]color=([a-z]+)/);if(m){k=m[1];localStorage.setItem("mstheme",k)}else{k=localStorage.getItem("mstheme")}}catch(e){}'
          f'if(k&&{keys!r}.indexOf(k)>0)document.documentElement.setAttribute("data-theme",k);'
          'var bn=null;try{if(/[?&]banner=open(&|$)/.test(location.search)){bn="open";localStorage.setItem("msbanner",bn)}else if(/[?&]banner=tab(&|$)/.test(location.search)){bn="tab";localStorage.setItem("msbanner",bn)}else{bn=localStorage.getItem("msbanner")}}catch(e){}'
          'if(bn==="open")document.documentElement.setAttribute("data-banner","open")})();')
    return f'<style>{css}</style>\n<script>{js}</script>\n'


def theme_body():
    """右下の「色を選ぶ」ボタン。選んだ色はこの端末に覚え、ほかのページでも同じ色にする"""
    items = ''.join(f'<li><button type="button" data-k="{k}" aria-pressed="false"><span class="tsw-sw" style="background:linear-gradient(135deg,{a} 50%,{c} 50%)"></span>{esc(n)}</button></li>'
                    for k, n, a, c, _v in THEMES)
    banners = ('<li><p class="tsw-h">採用バナーの見せ方</p></li>'
               '<li><button type="button" data-b="tab" aria-pressed="false"><span class="tsw-bi">A</span>札を押すとバナーが開く（今の形）</button></li>'
               '<li><button type="button" data-b="open" aria-pressed="false"><span class="tsw-bi">B</span>バナーをいつも出しておく</button></li>')
    js = ('(function(){var w=document.getElementById("tsw");if(!w)return;var b=w.querySelector(".tsw-btn"),l=w.querySelector(".tsw-list"),r=document.documentElement;'
          'var mark=function(){var k=r.getAttribute("data-theme")||"base",bn=r.getAttribute("data-banner")==="open"?"open":"tab";'
          'Array.prototype.forEach.call(l.querySelectorAll("button[data-k]"),function(x){x.setAttribute("aria-pressed",x.getAttribute("data-k")===k?"true":"false")});'
          'Array.prototype.forEach.call(l.querySelectorAll("button[data-b]"),function(x){x.setAttribute("aria-pressed",x.getAttribute("data-b")===bn?"true":"false")})};'
          'b.addEventListener("click",function(){var o=l.hidden;l.hidden=!o;b.setAttribute("aria-expanded",o?"true":"false")});'
          'l.addEventListener("click",function(e){var y=e.target.closest("button[data-b]");if(y){var bn=y.getAttribute("data-b");'
          'if(bn==="open")r.setAttribute("data-banner","open");else r.removeAttribute("data-banner");try{localStorage.setItem("msbanner",bn)}catch(e){}'
          'if(window.msBannerMode)window.msBannerMode();mark();return}'
          'var x=e.target.closest("button[data-k]");if(!x)return;var k=x.getAttribute("data-k");'
          'if(k==="base")r.removeAttribute("data-theme");else r.setAttribute("data-theme",k);try{localStorage.setItem("mstheme",k)}catch(e){}mark()});'
          'document.addEventListener("click",function(e){if(!w.contains(e.target)){l.hidden=true;b.setAttribute("aria-expanded","false")}});mark()})();')
    return (f'<div class="tsw" id="tsw"><ul class="tsw-list" hidden><li><p class="tsw-h">色の案</p></li>{items}{banners}<li><p>選ぶとすぐにサイト全体が切り替わります。採用バナーはトップページを少し下へ進めると出ます</p></li></ul>'
            f'<button class="tsw-btn" type="button" aria-expanded="false"><span class="tsw-dot"></span>色・表示を選ぶ</button></div>\n<script>{js}</script>\n')


def head(fname, title, desc):
    robots = '' if RELEASE else '<meta name="robots" content="noindex,nofollow">\n'
    canonical = ''
    if RELEASE and SITE_URL:
        path = '' if fname == 'index.html' else fname
        canonical = f'<link rel="canonical" href="{SITE_URL}/{path}">\n'
    # LINE などに URL を貼ったときの写真（ogp.py で作る）。場所はアドレスの頭から書く決まり。公開用で URL が未定なら出さない
    img_base = SITE_URL if RELEASE else PREVIEW_URL
    ogv = hashlib.md5((BASE / 'images' / 'ogp.jpg').read_bytes()).hexdigest()[:8]  # 撮り直したら LINE などが新しい写真を取り直すように
    ogimg = (f'<meta property="og:image" content="{img_base}/images/ogp.jpg?v={ogv}">\n'
             '<meta name="twitter:card" content="summary_large_image">\n') if img_base else ''
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
{ogimg}<link rel="stylesheet" href="assets/style.css?v={ASSET_V}">
{EWL_HEAD if fname == 'index.html' else ''}{'' if RELEASE else theme_head()}</head>'''


def header(fname):
    items = []
    for f, name, _en, in_head, _d in PAGES:
        if not in_head:
            continue
        cur = ' aria-current="page"' if f == fname else ''
        items.append(f'<li><a href="{f}"{cur}>{name}</a></li>')
    # 採用情報は今の AirWORK へ（2026-11-17 松本さん。新しいタブで開く）
    items.append(f'<li><a href="{RECRUIT_URL}" target="_blank" rel="noopener">採用情報{ic("ext", "ic gnav-ext")}<span class="vh">（外部サイト）</span></a></li>')
    drawer = []
    for f, name, _en, _h, _d in PAGES:
        cur = ' aria-current="page"' if f == fname else ''
        drawer.append(f'<li><a href="{href(f)}"{cur}>{name}{ic("chev")}</a></li>')
    drawer.append(f'<li><a href="{RECRUIT_URL}" target="_blank" rel="noopener">採用情報<span class="ext-note">（外部サイト）</span>{ic("ext")}</a></li>')
    draft = '' if RELEASE else ('<div class="draft"><span>制作中のページです（確認用）</span>'
                                '<a href="check.html">確認が必要なところの一覧</a></div>\n')
    return f'''<body>
{EWL_BODY if fname == 'index.html' else ''}{SPRITE}
<a class="skip" href="#main">本文へ移動</a>
{draft}<header class="hd{' hd-ovl' if fname == 'index.html' else ''}">
<div class="hd-in">
<a class="logo" href="./" aria-label="{COMPANY} ホーム"><span class="logo-s">株式会社</span><span class="logo-l">丸信</span><span class="logo-en" lang="en" aria-hidden="true">MARUSHIN</span></a>
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
<a class="logo logo-w" href="./" aria-label="{COMPANY} ホーム"><span class="logo-s">株式会社</span><span class="logo-l">丸信</span></a>
<address>〒{POSTAL} {ADDRESS}<br>TEL {TEL}　FAX {FAX}</address>
</div>
<nav class="ft-nav" aria-label="フッターメニュー"><ul>
{''.join(links)}
</ul></nav>
</div>
<p class="copy"><small>&copy; {COMPANY}</small></p>
</footer>
<div class="fixbar">
<a class="btn btn-white-line" href="{TEL_HREF}">{ic("phone")}電話で相談</a>
<a class="btn btn-teal" href="contact.html">{ic("mail")}お問い合わせ</a>
</div>
{'' if RELEASE else theme_body()}{script}
</body>
</html>
'''


def page_head(fname):
    """下層ページの上の帯（題・英字・写真）と、現在位置。"""
    _f, name, en, _h, _d = PAGE[fname]
    pos = PH_POS
    # 全ページ、松本さんのデザイン案の見せ方（左に英字と大きな明朝の題・右に斜めに切った写真。2026-11-17 丸信について・料金案内から。
    # 2026-11-20 よくある質問・お客様の声・お問い合わせ・プライバシーポリシーもそろえた）
    # 長い題は、写真の見え方を変えずにすむよう、スマホでは言葉の切れ目で2行に折る（2026-11-20）
    ttl = name.replace('プライバシーポリシー', '<span class="ib">プライバシー</span><span class="ib">ポリシー</span>')
    return f'''<div class="ph ph-au">
<div class="ph-img"><img src="images/hero.jpg" alt="" width="1600" height="1066" style="object-position:{pos}"></div>
<div class="ph-in"><div class="ph-ttl"><p class="ph-en" lang="en">{en}</p><h1>{ttl}</h1></div></div>
</div>
<nav class="bc" aria-label="現在位置"><ol><li><a href="./">ホーム</a></li><li aria-current="page">{name}</li></ol></nav>'''


def layout(fname, body, with_cta=True):
    _f, name, _en, _h, desc = PAGE[fname]
    if fname == 'index.html':
        title = f'春日井市・名古屋市の解体工事｜{COMPANY}'   # 2026-11-17「解体工事相談室」はあまり押し出さない（丸信さん）
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


def ct_band():
    """紺の「解体工事のご相談はこちら」の帯。全ページで同じもの（2026-11-17）。
    トップにあった「ただいま電話受付中」は、年末年始などの長い休みにも出てしまうので外した（2026-11-20 松本さん）"""
    arw = '<svg class="t-arw" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M4 12h15M13.5 6.5 19 12l-5.5 5.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>'
    return f'''<section class="ct-band has-wm" data-wm="CONTACT" aria-labelledby="h-contact">
<div class="wrap ct-in">
<div class="ct-l"><p class="cm-en" lang="en">CONTACT</p><h2 class="ct-ttl" id="h-contact">解体工事のご相談はこちら</h2>
<a class="ct-tel" href="{TEL_HREF}">{ic("phone")}<span>{TEL}</span></a>
<p class="ct-hours">{HOURS}</p>
</div>
<a class="btn btn-white ct-btn" href="contact.html">お問い合わせ{arw}</a>
</div>
</section>'''


# ---------- 各ページ ----------

def page_index():
    company, works, flow, voice, faq = load('company.json'), load('works.json'), load('flow.json'), load('voice.json'), load('faq.json')
    # 丸信の取り組み（2026-11-17 松本さんのデザイン案のとおり。文は今のサイトの3項目を言い換えたもの）
    cards = [
        ('解体専門の会社に<br>直接相談', '地域に根付いた解体専門の会社です。下請業者への発注による中間マージンが発生しません。'),
        ('着工前から<br>近隣に配慮', '工事前には、近隣の皆様へ丁寧にご挨拶。万が一のトラブルにも、速やかに対応いたします。'),
        ('工事が終わっても<br>丁寧に', '工事完了後も、改めてご近所へご挨拶。ご迷惑がなかったかを確認することまで、大切にしています。'),
    ]
    cards_html = ''.join(f'<li><span class="cm-n" aria-hidden="true">{n:02d}</span><h3>{t}</h3><p>{p}</p></li>'
                         for n, (t, p) in enumerate(cards, 1))
    # 会社の強み（2026-11-18 松本さん「しっかりした会社という印象に」）。数字・許可は company.json から取り、変われば一緒に変わる
    prof = {r['k']: r['v'] for r in company['profile']}
    perm = {r['k']: r['v'] for r in company['permits']}
    m = re.match(r'平成(\d+)年', prof['創業'][0])
    founded = 1988 + int(m.group(1))
    cap = re.match(r'(\d+)万円', prof['資本金'][0])
    sanpai = [x.split()[0] for x in perm['産業廃棄物収集運搬業許可']]
    st = [(f'{founded}', '年', '創業', prof['創業'][0]),
          (f'{int(cap.group(1)):,}', '万円', '資本金', ''),
          # 2026-11-18 国の建設業者検索で確認：令和8年10月に更新（特-8）、解体工事業ととび・土工工事業がともに特定
          ('特定', '', '建設業許可', '、'.join(next(r for r in company['permits'] if r['k'] == '建設業許可').get('kinds', [])) or '愛知県知事許可'),
          (f'{len(sanpai)}', '県', '産業廃棄物収集運搬業許可', '・'.join(p.replace('県', '') for p in sanpai))]
    if '特-' not in perm['建設業許可'][0]:
        st[2] = ('許可', '', '建設業許可', '愛知県知事許可')
    # 説明は「、」の区切りで折り返す（「土工工／事業」のように語の途中で切れないよう、区切りごとにまとめる）
    nw = lambda d: '、'.join(f'<span class="nw">{x}</span>' for x in d.split('、'))
    st_html = ''.join(f'<li><p class="ab-sn"><b>{a}</b>{u}</p><p class="ab-sl">{l}</p><p class="ab-sd">{nw(d)}</p></li>' for a, u, l, d in st)
    # 法令と環境への取り組み（会社の理念・方針の文を言い換えたもの。新しいことは足さない）
    eco = [
        ('法令にもとづく施工', '契約内容と建設リサイクル法にもとづいた施工計画を守り、ご依頼の目的に沿った工事を行います。'),
        ('廃棄物の適正な処分', f'解体で出た廃棄物を正しく分けて処分し、リサイクルで排出を減らします。産業廃棄物収集運搬業の許可（{"・".join(sanpai)}）を持っています。'),
        ('汚染土壌の浄化', '汚染された土壌の浄化に取り組んでいます。'),
        ('車両と重機の省エネ', '解体工事で使う車両・重機の燃費の向上に努めます。'),
    ]
    eco_html = ''.join(f'<li><h4>{t}</h4><p>{d}</p></li>' for t, d in eco)
    # 施工事例（2026-11-17 松本さんのデザイン案）：番号・施工前後の写真・構造の札・場所・題。トップだけの見せ方（施工事例のページは work_card のまま）
    def wk(n, w):
        title = f'{esc(w["place"])} {esc(w["name"])}'
        kind = f'<span class="wk-kind">{esc(w["type"])}</span>' if w['type'] else ''
        note = f'<p class="wk-note">{esc(w["note"])}</p>' if w['note'] else ''
        return (f'<li><div class="wk-ph">'
                f'<figure><img src="images/case/{w["id"]}-before.jpg" alt="施工前の写真：{title}" width="208" height="156" loading="lazy" decoding="async"><figcaption>施工前</figcaption></figure>'
                f'<span class="wk-arw" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v13M6.5 12.5 12 18l5.5-5.5"/></svg></span>'
                f'<figure><img src="images/case/{w["id"]}-after.jpg" alt="施工後の写真：{title}" width="268" height="201" loading="lazy" decoding="async"><figcaption class="after">施工後</figcaption></figure>'
                f'</div>{kind}<p class="wk-place">{esc(w["place"])}</p><h3 class="wk-ttl">{esc(w["name"])} 解体工事</h3>{note}</li>')
    works_html = ''.join(wk(n, w) for n, w in enumerate(works[:3], 1))
    # 施工の流れ（2026-11-17 松本さんのデザイン案）：10段階を4つのまとまりで。中身は施工の流れのページ（data/flow.json）のとおり
    fl = [
        ('chat', 'ご相談・お見積もり', 'ご相談・お見積もり依頼から、お見積もりのご提出まで。'),
        ('doc', 'ご契約・着工準備', 'ご契約、アスベスト事前調査、届出、近隣へのご挨拶。'),
        ('excavator', '解体工事', '着工から、廃材の分別・搬出まで。'),
        ('ground', '整地・工事完了', '整地・完了後、近隣へ改めてご挨拶。'),
    ]
    # 各段の写真はイメージ（2026-11-17 松本さんが用意。images/top/flow-1〜4.jpg）。段のあいだの「→」は写真の高さの真ん中に
    steps = ''.join(f'<li style="--i:{n - 1}"><p class="fl-n"><span lang="en">STEP</span><b>{n:02d}</b></p>'
                    f'<div class="fl-phw"><img class="fl-ph" src="images/top/flow-{n}.jpg" alt="" width="1448" height="1086" loading="lazy" decoding="async">'
                    + ('<span class="fl-arw" aria-hidden="true">→</span>' if n < len(fl) else '') + '</div>'
                    f'<h3>{t}</h3><p class="fl-p">{d}</p></li>' for n, (_i, t, d) in enumerate(fl, 1))
    voices = ''.join(f'<li><span class="vc-q" aria-hidden="true">“</span><p class="vc-t">{esc(v["title"])}</p><p class="vc-w">{esc(v["who"])}</p></li>' for v in voice)
    area_rows = ''.join(f'<div><dt>{esc(a["pref"])}</dt><dd>{esc(a["cities"])}</dd></div>' for a in company['area'])
    top_faq = [(n, it) for n, it in enumerate(faq['items'], 1) if it.get('top')]
    faq_html = ''.join(qa_html(it, n) for n, it in top_faq)
    return f'''<section class="hero">
<div class="hero-ph">
<picture><source media="(max-width:767px)" srcset="images/top/fv-1-sp.jpg"><img class="hero-img" src="images/top/fv-1.jpg" alt="" width="1536" height="1024" fetchpriority="high"></picture>
<i class="hero-sl" style="background-image:url(images/top/fv-2.jpg);animation-delay:5s"></i>
<i class="hero-sl" style="background-image:url(images/top/fv-3.jpg);animation-delay:11s"></i>
</div>
<div class="hero-in">
<p class="hero-label">解体から次の一歩へ</p>
<h1>建物の解体は<br><em>丸信へ</em></h1>
<p class="hero-sub">愛知県（春日井市・小牧市・尾張旭市・瀬戸市・名古屋市等）の解体のご相談は、株式会社丸信にお任せください。</p>
<div class="hero-btns">
<a class="btn btn-teal btn-lg" href="contact.html">{ic("mail")}無料相談</a>
<a class="btn btn-ghost btn-lg" href="case.html">施工事例を見る{ic("chev")}</a>
</div>
</div>
<span class="hero-scroll" aria-hidden="true">scroll</span>
</section>

<section class="ab-band" aria-labelledby="h-about">
<div class="wrap ab-in">
<h2 class="ab-ttl" id="h-about">丸信の解体工事について</h2>
<p class="ab-tx">当社は愛知県春日井市を中心に解体工事を承っています。<br>木造住宅、鉄骨建築、鉄筋コンクリート造や、テナント事務所・店舗など、<br>建築様式を問わず解体工事が可能です。</p>
<ul class="ab-st" aria-label="会社の概要">{st_html}</ul>
</div>
</section>

<section class="sec cm-sec has-wm" data-wm="COMMITMENT" aria-labelledby="h-torikumi">
<div class="wrap">
<div class="cm-head">
<div><p class="cm-en" lang="en">OUR COMMITMENT</p>
<h2 class="cm-ttl" id="h-torikumi">解体の前も後も<br>安心につながる丸信の取り組み</h2></div>
</div>
<ol class="cm">{cards_html}</ol>
<div class="eco"><h3 class="eco-ttl">法令と環境への取り組み</h3><ul class="eco-l">{eco_html}</ul></div>
<p class="center cm-more"><a class="btn btn-navy cm-btn" href="outline.html">丸信の会社案内を見る{ic("chev")}</a></p>
</div>
</section>

<section class="sec wk-sec has-wm" data-wm="WORKS" aria-labelledby="h-works">
<div class="wrap">
<div class="wk-head">
<div><p class="cm-en" lang="en">WORKS</p><h2 class="wk-ttl-h" id="h-works">施工事例</h2></div>
<p class="wk-lead">これまでに手がけた解体工事の一例をご紹介します。<br>木造・鉄骨造・鉄筋コンクリート造など、さまざまな建物に対応しています。</p>
</div>
<ol class="wk">{works_html}</ol>
<p class="center cm-more"><a class="btn btn-navy cm-btn" href="case.html">施工事例をもっと見る{ic("chev")}</a></p>
</div>
</section>

<section class="pr-band has-wm" data-wm="PRICE" aria-labelledby="h-price">
<div class="wrap pr-in">
<div class="pr-h"><p class="cm-en" lang="en">PRICE</p><h2 class="t-ttl" id="h-price">料金案内</h2></div>
<p class="pr-tx">木造・鉄骨造・鉄筋コンクリート造の解体工事と、<br>庭木伐採・ブロック塀などその他の料金表を掲載しています。</p>
<a class="btn btn-navy t-btn" href="price.html">料金案内を見る{ic("chev")}</a>
</div>
</section>

<section class="sec fl-sec has-wm" data-wm="FLOW" aria-labelledby="h-flow">
<div class="wrap">
<div class="fl-head"><p class="cm-en" lang="en">FLOW</p>
<h2 class="cm-ttl" id="h-flow">ご相談から工事完了まで</h2></div>
<ol class="fl">{steps}</ol>
<p class="center cm-more"><a class="btn btn-navy cm-btn" href="flow.html">施工の流れを詳しく見る{ic("chev")}</a></p>
</div>
</section>

<section class="sec vc-sec has-wm" data-wm="VOICE" aria-labelledby="h-voice">
<div class="wrap">
<p class="cm-en" lang="en">VOICE</p><h2 class="t-ttl" id="h-voice">お客様の声</h2>
<ul class="vc">{voices}</ul>
<p class="center t-more"><a class="tlink t-link" href="voice.html">お客様の声を見る<svg class="t-arw" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M4 12h15M13.5 6.5 19 12l-5.5 5.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></a></p>
</div>
</section>

<section class="sec ar-sec has-wm" data-wm="AREA" aria-labelledby="h-area">
<div class="wrap t-two">
<div><p class="cm-en" lang="en">AREA</p><h2 class="t-ttl" id="h-area">対応エリア</h2><p class="t-sub">春日井市を中心に近隣エリアへ</p></div>
<div><dl class="ar">{area_rows}</dl>
<p class="ar-note">{esc(company["area_note"])}。上記の対応エリア以外にも柔軟に対応させていただきます。まずはお気軽にお問い合わせください。</p></div>
</div>
</section>

<section class="sec fq-sec has-wm" data-wm="FAQ" aria-labelledby="h-faq">
<div class="wrap t-two">
<div><p class="cm-en" lang="en">FAQ</p><h2 class="t-ttl" id="h-faq">よくある質問</h2></div>
<div><div class="qas fq">{faq_html}</div>
<p class="center t-more"><a class="tlink t-link" href="faq.html">よくある質問をすべて見る<svg class="t-arw" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M4 12h15M13.5 6.5 19 12l-5.5 5.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></a></p></div>
</div>
</section>

{ct_band()}

<div class="rqs" id="rqs">
<aside class="rq" id="rq" aria-label="従業員募集のお知らせ">
<button class="rq-tab" type="button" aria-expanded="false" aria-controls="rq-pop"><span class="rq-tab-new">募集中</span><span class="rq-tab-en" lang="en">RECRUIT</span><span class="rq-tab-ja">採用情報</span></button>
<div class="rq-pop" id="rq-pop">
<a class="rq-in" href="{RECRUIT_URL}" target="_blank" rel="noopener"><img src="images/top/recruit-banner.jpg" alt="RECRUIT 街の次の一歩をともにつくる 株式会社 丸信 採用情報を見る（外部サイト）" width="1122" height="1402" loading="lazy" decoding="async"><span class="rq-tk" aria-hidden="true"><span>{"<span>RECRUIT</span>" * 8}</span></span></a>
</div>
</aside>
<aside class="rq rq-blog" id="rq-blog" aria-label="ブログのお知らせ">
<button class="rq-tab" type="button" aria-expanded="false" aria-controls="rq-blog-pop"><span class="rq-tab-new">準備中</span><span class="rq-tab-en" lang="en">BLOG</span><span class="rq-tab-ja">ブログ</span></button>
<div class="rq-pop" id="rq-blog-pop">
<div class="rq-in rq-soon"><p class="rq-soon-en" lang="en">BLOG</p><p class="rq-soon-ttl">ブログ</p><p class="rq-soon-st">ただいま準備中です</p><p class="rq-soon-tx"><span>公開まで</span><span>今しばらくお待ちください</span></p></div>
</div>
</aside>
</div>{todo('求人の案内：載せたい言葉（未経験者歓迎など）があれば')}'''


def page_about():
    """丸信について。2026-11-17 松本さんのデザイン案の構成に（トップと同じ見せ方・動き）。
    文は今のサイトの内容を、デザイン案の短い言い回しで。見出しは「。」「、」なし（決まり）。"""
    company = load('company.json')
    chev = ic('chev')
    arw = '<svg class="t-arw" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M4 12h15M13.5 6.5 19 12l-5.5 5.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>'

    def photo(src, label):
        """写真があればイメージ写真、なければ仮枠"""
        if src:
            return f'<figure class="au-ph"><img src="{src}" alt="" width="1448" height="1086" loading="lazy" decoding="async"></figure>'
        return f'<div class="au-ph">{frame(label)}</div>'

    feats = [
        ('解体専門の会社へ直接ご依頼', '地域に根付いた解体専門の会社へ直接ご相談いただけます。<br>下請業者への発注による中間マージンが発生しません。',
         'images/top/flow-2.jpg', '', ''),   # 「解体費用は確実に安くなります」の言い切りは外したまま（2026-11-20 松本さん「今のままでOK」）
        ('着工前から近隣に配慮', '振動や騒音、チリ・ホコリに配慮し、工事前には丁寧にご挨拶。<br>万が一のトラブルにも、速やかに対応します。',
         'images/top/flow-3.jpg', '', ''),
        ('工事が終わっても丁寧に', '工事完了後も改めてご挨拶。ご協力への感謝をお伝えし、<br>ご迷惑がなかったかを確認します。',
         'images/top/flow-4.jpg', '', ''),
    ]
    feat_html = ''.join(
        f'<li><span class="au-n" aria-hidden="true">{n:02d}</span><div class="au-tx"><h3>{t}</h3><p>{d}</p>{todo(td) if td else ""}</div>{photo(src, lb)}</li>'
        for n, (t, d, src, lb, td) in enumerate(feats, 1))

    kinds = [('home', '木造住宅'), ('steel', '鉄骨造'), ('rc', '鉄筋コンクリート造'), ('shop', '店舗・事務所')]
    kind_svg = {
        'home': '<path d="M4 11.5 12 5l8 6.5"/><path d="M6 10v9h12v-9"/><path d="M10 19v-5h4v5"/>',
        'steel': '<path d="M3 10h18M5 10l7-5 7 5"/><path d="M6 10v10M18 10v10M12 10v10M6 15h12"/>',
        'rc': '<rect x="6" y="3.5" width="12" height="17"/><path d="M9 7h2M13 7h2M9 10.5h2M13 10.5h2M9 14h2M13 14h2M11 20.5v-3h2v3"/>',
        'shop': '<path d="M4 9h16l-1.5-4.5h-13z"/><path d="M4 9c0 1.4 1 2.3 2.3 2.3S8.7 10.4 8.7 9c0 1.4 1 2.3 2.3 2.3S13.3 10.4 13.3 9c0 1.4 1 2.3 2.3 2.3S18 10.4 18 9"/><path d="M5.5 11.5V20h13v-8.5M10 20v-5h4v5"/>',
    }
    kinds_html = ''.join(
        f'<li><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{kind_svg[k]}</svg>{t}</li>'
        for k, t in kinds)
    area_rows = ''.join(f'<div><dt>{esc(a["pref"])}</dt><dd>{esc(a["cities"])}</dd></div>' for a in company['area'])

    pol = [
        ('法令順守', '法令・条例を守り、従業員や<br>協力業者への周知を徹底します。'),
        ('顧客満足', '十分な対話と説明を心がけ、<br>ご要望に応える工事を目指します。'),
        ('近隣協定', '事前の説明と誠実な対応で、<br>近隣の皆様への配慮を徹底します。'),
        ('継続的な運用・改善', '社会の変化に対応し、技術・サービスの<br>向上に取り組みます。'),
    ]
    pol_html = ''.join(f'<li><span class="au-pn" aria-hidden="true">{n:02d}</span><div><h3>{t}</h3><p>{d}</p></div></li>' for n, (t, d) in enumerate(pol, 1))

    land = [   # 写真は 2026-11-20 松本さんにいただいたイメージ写真
        ('駐車場運営', '使わなくなった土地の、駐車場としての活用をご提案します。', 'images/about/parking.jpg'),
        ('土木工事・外構整備', 'フェンス・門扉・カーポートなど、土地活用に伴う工事もご相談ください。', 'images/about/gaikou.jpg'),
    ]
    land_html = ''.join(f'<li>{photo(src, t)}<h3>{t}</h3><p>{d}</p></li>' for t, d, src in land)

    return f'''{page_head('about.html')}
<section class="sec au-mind has-wm" data-wm="MIND" aria-labelledby="h-mind">
<div class="wrap au-mind-in">
<figure class="au-ph au-staff"><img src="images/about-staff.jpg" alt="丸信の社員の集合写真" width="2000" height="1003" loading="lazy" decoding="async"></figure>
<div class="au-mind-tx"><p class="cm-en" lang="en">OUR MIND</p><p class="au-sub">解体工事への想い</p>
<h2 class="t-ttl au-big" id="h-mind">一番大切なのは<br>ご近所様への気配り</h2>
<p>工事の後も、ここで暮らすお客様のために。<br>ご近所様へのご挨拶から、日々の作業まで。<br>熟練の技術と一人ひとりの気配りで、安心してお任せいただける解体工事を目指します。</p></div>
</div>
</section>

<section class="sec au-cm-sec has-wm" data-wm="COMMITMENT" aria-labelledby="h-au-cm">
<div class="wrap">
<p class="cm-en" lang="en">OUR COMMITMENT</p><h2 class="t-ttl" id="h-au-cm">丸信の取り組み</h2>
<ol class="au-cm">{feat_html}</ol>
</div>
</section>

<section class="sec au-svc-sec has-wm" data-wm="SERVICE" aria-labelledby="h-svc">
<div class="wrap">
<p class="cm-en" lang="en">SERVICE</p><h2 class="t-ttl" id="h-svc">対応する工事</h2>
<p class="t-sub">木造住宅から店舗・事務所まで、建築様式を問わず対応します。</p>
<ul class="au-kinds">{kinds_html}</ul>
<div class="au-hand">
<div class="au-hand-h"><p class="au-sub">手壊しによる解体</p><h3 class="t-ttl">細かな場所こそ<br>手壊しで丁寧に</h3></div>
<div class="au-hand-b"><p>道幅が狭く重機が入れない場所や、隣接する建物に注意が必要な箇所にも対応。機械ではできない細かな部分を、人の手で丁寧に解体します。</p>
<a class="btn btn-navy cm-btn au-btn" href="price.html">料金案内を見る{arw}</a></div>
</div>
</div>
</section>

<section class="sec ar-sec au-ar has-wm" data-wm="AREA" aria-labelledby="h-area">
<div class="wrap t-two">
<div><p class="cm-en" lang="en">AREA</p><h2 class="t-ttl" id="h-area">対応エリア</h2><p class="t-sub">春日井市を中心に近隣エリアへ</p></div>
<div><dl class="ar">{area_rows}</dl>
<p class="ar-note">{esc(company["area_note"])}。その他の地域もお気軽にご相談ください。</p></div>
</div>
</section>

<section class="sec au-pol-sec has-wm" data-wm="POLICY" aria-labelledby="h-pol">
<div class="wrap">
<p class="cm-en" lang="en">POLICY</p><h2 class="t-ttl" id="h-pol">丸信の方針</h2>
<ul class="au-pol">{pol_html}</ul>
</div>
</section>

<section class="au-note-sec" aria-labelledby="h-note">
<div class="wrap"><div class="au-note">
<h2 id="h-note">解体業者選びで後悔しないために</h2>
<p>見積もりの金額だけでなく、工事内容や廃棄物の処理方法も確認しましょう。不安な点は、事前にご相談ください。</p>
</div></div>
</section>

<section class="sec au-land-sec has-wm" data-wm="LAND USE" aria-labelledby="h-land">
<div class="wrap">
<p class="cm-en" lang="en">LAND USE</p><h2 class="t-ttl" id="h-land">解体のその先土地活用まで</h2>
<ul class="au-land">{land_html}</ul>
</div>
</section>

{ct_band()}'''


def page_price():
    """料金案内。2026-11-17 松本さんのデザイン案の構成に（丸信について・トップと同じ見せ方）。
    金額と単位は data/price.json（今のサイトの料金表）のまま。デザイン案の数字は使わない（庭木・庭石の単位がデザイン案と違う）。"""
    price = load('price.json')
    chev = ic('chev')
    arw = '<svg class="t-arw" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M4 12h15M13.5 6.5 19 12l-5.5 5.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>'
    down = '<svg class="t-arw" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M12 4v15M6.5 13.5 12 19l5.5-5.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>'
    svg = {
        '木造': '<path d="M4 11.5 12 5l8 6.5"/><path d="M6 10v9h12v-9"/><path d="M10 19v-5h4v5"/>',
        '鉄骨造': '<path d="M3 10h18M5 10l7-5 7 5"/><path d="M6 10v10M18 10v10M12 10v10M6 15h12"/>',
        '鉄筋コンクリート造': '<rect x="6" y="3.5" width="12" height="17"/><path d="M9 7h2M13 7h2M9 10.5h2M13 10.5h2M9 14h2M13 14h2M11 20.5v-3h2v3"/>',
    }
    def cost_html(c):
        # 「3.5～4.5万円」の数字を大きく、単位（万円・円）を小さく
        import re as _re
        m = _re.match(r'^(.*?)(万円|円)(.*)$', c)
        return f'<b>{esc(m.group(1))}</b><small>{esc(m.group(2))}{esc(m.group(3))}</small>' if m else f'<b>{esc(c)}</b>'
    cards = ''.join(
        f'<li><h3><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{svg.get(st["name"], "")}</svg>{esc(st["name"])}</h3>'
        f'<table class="pr-t"><caption class="vh">{esc(st["name"])}の解体費用（坪単価）</caption>'
        f'<thead><tr><th scope="col">坪数</th><th scope="col">費用（坪単価）</th></tr></thead><tbody>'
        + ''.join(f'<tr><th scope="row">{esc(a)}</th><td>{cost_html(b)}</td></tr>' for a, b in st['rows'])
        + '</tbody></table></li>' for st in price['structures'])
    incl = ['整地', '処分費用', '養生シート', 'コンクリート基礎']
    incl_html = ''.join(f'<li><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>{t}</li>' for t in incl)
    rows, n = [], 0
    for o in price['others']:
        for what, cost in o['rows']:
            n += 1
            rows.append(f'<tr><td class="pr-no">{n}.</td><th scope="row">{esc(o["name"])}</th><td>{esc(what) or "―"}</td><td class="num">{cost_html(cost)}</td></tr>')
    return f'''{page_head('price.html')}
<section class="sec pr-intro">
<div class="wrap">
<h2 class="t-ttl pr-lead-h">解体工事の費用をわかりやすく</h2>
<p class="pr-lead">{esc(price["lead"]).replace("料金表です。", "料金をご案内します。")}</p>
{todo('料金の金額（今のサイトの料金表は2013年ごろのものです。今もこの金額でよいか）')}
{todo('税込・税別の表記（今のサイトの料金表には、どちらとも書かれていません）')}
<ul class="pr-jump"><li><a href="#demolition">建物の解体工事{down}</a></li><li><a href="#other">その他の工事・処分{down}</a></li></ul>
</div>
</section>

<section class="sec pr-dm has-wm" data-wm="DEMOLITION" id="demolition" aria-labelledby="h-dm">
<div class="wrap">
<div class="pr-dm-h"><div><p class="cm-en" lang="en">DEMOLITION</p><h2 class="t-ttl" id="h-dm">建物の解体工事</h2></div>
<p class="pr-unit">費用は坪単価です（1坪＝3.3m²）</p></div>
<ul class="pr-cards">{cards}</ul>
<div class="pr-incl"><p>上記料金に含まれるもの</p><ul>{incl_html}</ul></div>
</div>
</section>

<section class="sec pr-ot has-wm" data-wm="OTHER WORKS" id="other" aria-labelledby="h-ot">
<div class="wrap">
<p class="cm-en" lang="en">OTHER WORKS</p><h2 class="t-ttl" id="h-ot">その他の工事・処分</h2>
<div class="pr-tw"><table class="pr-ot-t"><caption class="vh">その他の工事・処分の料金</caption>
<thead><tr><th scope="col" colspan="2">項目</th><th scope="col">内容</th><th scope="col" class="num">費用</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div>
<div class="pr-info"><span class="pr-i" aria-hidden="true">i</span>
<div><h3>着工前のご準備・別途費用について</h3><p>解体工事着工までのご準備や、別途費用が発生する場合については、<a href="faq.html#prep">よくある質問</a>もご覧ください。</p></div>
<a class="btn pr-info-btn" href="faq.html#prep">よくある質問を見る{arw}</a></div>
<p class="pr-note">{esc(price["note"]).replace("ございましたら、", "は")}</p>
</div>
</section>

{ct_band()}'''


def page_case():
    """施工事例。2026-11-17 松本さんのデザイン案の構成に（丸信について・料金案内と同じ見せ方）。
    写真は丸信さんの事例写真（01〜03は届いた大きい写真、04は今のサイトの小さい写真）。見出しは句読点なし。"""
    works = load('works.json')
    items = []
    for n, w in enumerate(works, 1):
        title = f'{esc(w["place"])} {esc(w["name"])}'
        lz = '' if n <= 2 else ' loading="lazy" decoding="async"'
        kind = f'<span class="wk-kind cs-kind">{esc(w["type"])}</span>' if w['type'] else ''
        note = f'<span class="cs-note">{esc(w["note"])}</span>' if w['note'] else ''
        items.append(f'''<li><div class="cs-ph">
<figure><img src="images/case/{w["id"]}-before.jpg" alt="施工前の写真：{title}" width="1448" height="976"{lz}><figcaption>施工前</figcaption></figure>
<figure><img src="images/case/{w["id"]}-after.jpg" alt="施工後の写真：{title}" width="1448" height="976"{lz}><figcaption class="after">施工後</figcaption></figure>
</div>
<div class="cs-cap"><span class="cs-n" aria-hidden="true">{n:02d}</span><div class="cs-tx"><p class="cs-tags">{kind}{note}</p><h2 class="cs-ttl">{esc(w["name"])}</h2><p class="cs-place">{esc(w["place"])}</p></div></div></li>''')
    return f'''{page_head('case.html')}
<section class="sec cs-sec has-wm" data-wm="WORKS" aria-labelledby="h-cs">
<div class="wrap">
<div class="cs-head"><div><p class="cm-en" lang="en">OUR WORKS</p><p class="t-ttl cs-catch" id="h-cs">一つひとつの現場に誠実に</p></div>
<p class="cs-lead">株式会社丸信にて施工を行いました事例をご紹介します。<br>工事完了後の隣家外壁補修工事や駐車場整備工事など、<br>お客様のニーズに幅広くお応えしております。</p></div>
<ol class="cs">{''.join(items)}</ol>
<p class="cs-more">※順次、施工事例を追加予定をしております。</p>
</div>
</section>

{ct_band()}'''


def page_flow():
    """施工の流れ。2026-11-17 松本さんのデザイン案の構成に（ほかの下層ページと同じ見せ方）。
    10段階を4つのまとまり（トップの流れと同じ）に分け、左に写真・右に縦の線と STEP。説明は今のサイトの内容を短くしたもの。"""
    flow = load('flow.json')
    arw = '<svg class="t-arw" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M4 12h15M13.5 6.5 19 12l-5.5 5.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>'
    short = {
        1: 'まずはご要望をお聞かせください。お問い合わせフォーム、またはお電話で承ります。',
        2: '現地調査を行い、費用や解体方法を詳しくご説明します。',
        3: 'お見積もりの内容にご納得いただいたうえで、ご契約となります。',
        4: '有資格者が調査・申請を行い、調査内容をお客様にご説明します。',
        5: '工事内容に応じて、必要な届出を行います。',
        6: '近隣の皆様へ、工事の概要や作業工程を丁寧にご説明します。',
        7: '現場の状況に合わせ、騒音・振動・粉塵・安全に配慮して施工します。',
        8: '木材・コンクリート・鉄などを分別し、中間処理施設へ搬出。マニフェスト伝票で処理状況を管理します。',
        9: '地盤面を平らに整え、工事完了後にお客様に現場をご確認いただきます。',
        10: 'ご協力への感謝をお伝えするとともに、ご迷惑がなかったかを確認します。',
    }
    title = {10: '近隣への工事終了のご挨拶', 6: '近隣への工事説明・ご挨拶', 2: 'お見積もりのご提出・ご説明', 1: 'ご相談・お見積もりのご依頼', 8: '廃材の分別・収集・搬出'}
    tags = {7: ['騒音対策', '振動対策', '防塵対策', '安全対策']}
    phases = [('ご相談・お見積もり', [1, 2], 'flow-1'), ('ご契約・着工準備', [3, 4, 5, 6], 'flow-2'),
              ('解体工事', [7, 8], 'flow-3'), ('整地・工事完了', [9, 10], 'flow-4')]
    nav = ''.join(f'<li><b>{n:02d}</b><span>{t}</span></li>' for n, (t, _s, _p) in enumerate(phases, 1))
    blocks = []
    for n, (t, steps, ph) in enumerate(phases, 1):
        st = ''.join(
            f'<li><p class="fw-sn"><span lang="en">STEP</span><b>{k:02d}</b></p><div><h3>{esc(title.get(k, flow[k - 1]["title"]))}</h3><p>{short[k]}</p>'
            + (''.join(f'<span class="fw-tag">{x}</span>' for x in tags[k]) if k in tags else '') + '</div></li>'
            for k in steps)
        blocks.append(f'''<section class="fw-ph" aria-labelledby="h-ph{n}">
<div class="fw-l"><p class="fw-pn"><span lang="en">PHASE</span> {n:02d}</p><h2 class="fw-pt" id="h-ph{n}">{t}</h2>
<figure class="au-ph"><img src="images/top/{ph}.jpg" alt="" width="1448" height="1086" loading="lazy" decoding="async"></figure></div>
<ol class="fw-steps">{st}</ol>
</section>''')
    return f'''{page_head('flow.html')}
<section class="sec fw-sec has-wm" data-wm="PROCESS" aria-labelledby="h-fw">
<div class="wrap">
<p class="cm-en" lang="en">PROCESS</p><p class="t-ttl fw-catch" id="h-fw">ご相談から工事完了まで丁寧に</p>
<p class="fw-lead">ご相談・お見積もりから、近隣へのご挨拶、解体工事、整地まで。丸信が行う施工の主な流れをご紹介します。</p>
<p class="fw-small">※解体内容によっては異なる場合がございます。詳しくは<a href="contact.html">お問い合わせ</a>ください。</p>
<ol class="fw-nav">{nav}</ol>
{''.join(blocks)}
</div>
</section>

<section class="fw-faq" aria-labelledby="h-flowfaq">
<div class="wrap fw-faq-in">
<p class="fw-faq-en" lang="en">FAQ</p><h2 id="h-flowfaq">よくある質問</h2>
<p>工事前の準備や手続きについて、ご質問をまとめています。</p>
<a class="btn pr-info-btn" href="faq.html">よくある質問を見る{arw}</a>
</div>
</section>

{ct_band()}'''


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
    """よくある質問。2026-11-20 松本さんのデザイン案の構成に（左に番号と分類、右に質問の一覧。ほかの下層ページと同じ帯で終える）。
    見出しは「。」「、」なし（決まり）。答えの中身は faq.json のまま"""
    faq = load('faq.json')
    en = {'cost': 'COST', 'work': 'WORK', 'prep': 'PREPARATION', 'area': 'AREA'}
    icon = {'cost': 'calc', 'work': 'excavator', 'prep': 'doc', 'area': 'pin'}
    down = '<svg class="fq-dn" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M6 9l6 6 6-6" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>'
    arw = '<svg class="t-arw" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M4 12h15M13.5 6.5 19 12l-5.5 5.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>'
    jump = ''.join(f'<li><a href="#{c["id"]}">{ic(icon.get(c["id"], "chat"))}<span>{esc(c["name"])}</span>{down}</a></li>' for c in faq['categories'])
    secs = []
    for i, c in enumerate(faq['categories'], 1):
        qs = ''.join(qa_html(it, n) for n, it in enumerate(faq['items'], 1) if it['cat'] == c['id'])
        if i == 1:
            qs = qs.replace('<details class="qa"', '<details class="qa" open', 1)   # 最初の1問は開いておき、押すと開くことが伝わるように
        secs.append(f'''<section class="fq-cat" id="{c["id"]}" aria-labelledby="h-{c["id"]}">
<div class="fq-cat-h"><p class="fq-no" lang="en">{i:02d}</p><p class="fq-en" lang="en">{en.get(c["id"], "")}</p><h2 id="h-{c["id"]}">{esc(c["name"])}</h2></div>
<div class="qas fq">{qs}</div>
</section>''')
    return f'''{page_head('faq.html')}
<section class="sec fq-page">
<div class="wrap">
<div class="fq-intro">
<p class="cm-en fq-intro-en" lang="en">QUESTIONS &amp; ANSWERS</p>
<h2 class="t-ttl">解体工事の疑問にお答えします</h2>
<p class="fq-lead">解体工事について、よくいただくご質問をまとめました。</p>
<p class="fq-hint">質問を押すと回答が開きます。</p>
</div>
<nav class="fq-jump" aria-label="質問の分類"><ul>{jump}</ul></nav>
{''.join(secs)}
<div class="fq-more">
{ic("chat", "ic fq-more-ic")}
<div class="fq-more-tx"><p class="fq-more-h">解決しない疑問はお気軽にご相談ください</p><p>工事の内容やお見積もりについて、個別にご案内いたします。</p></div>
<a class="tlink t-link" href="flow.html">施工の流れを見る{arw}</a>
</div>
</div>
</section>

{ct_band()}'''


def page_outline():
    """会社案内。2026-11-17 松本さんのデザイン案の構成に（丸信について・料金案内と同じ見せ方）。
    社長あいさつは今のサイトの文のまま（2026-11-17 松本さん「原文に戻して」）。企業理念はデザイン案の短い言い回しで。見出しは「。」「、」なし（決まり）。"""
    c = load('company.json')
    arw = '<svg class="t-arw" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M12 4v15M6.5 13.5 12 19l5.5-5.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>'

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

    jump = [('ol-msg', '社長あいさつ'), ('ol-prof', '会社概要'), ('ol-lic', '許可・登録'), ('ol-area', '対応エリア'), ('ol-acc', '所在地')]
    jump_html = ''.join(f'<li><a href="#{i}">{t}{arw}</a></li>' for i, t in jump)

    pics = [('images/top/fv-3.jpg', '50% 60%'), ('images/top/fv-2.jpg', '50% 55%'), ('images/top/staff.jpg', '50% 40%')]
    pics_html = ''.join(f'<li><img src="{src}" alt="" width="1600" height="1066" loading="lazy" decoding="async" style="object-position:{pos}"></li>' for src, pos in pics)

    def lic(r):
        prefs = '・'.join(x.split()[0].split('知事')[0] for x in r['v'])   # 「愛知県　第…」「愛知県知事許可…」の県名
        nums = '<br>'.join(esc(x) for x in r['v'])
        t = todo(r['todo']) if r.get('todo') else ''
        kinds = ''
        if r.get('kinds'):   # 許可の業種（建設業許可だけ）
            kinds = f'<p class="ol-kind">{esc("、".join(r["kinds"]))}' + (f'<small>（{esc(r["kinds_note"])}）</small>' if r.get('kinds_note') else '') + '</p>'
        return f'<li><h3>{esc(r["k"])}</h3><p class="ol-pref">{esc(prefs)}</p><p class="ol-num">{nums}</p>{kinds}{t}</li>'
    lic_html = ''.join(lic(r) for r in c['permits'])

    ph_svg = {
        'hand': '<path d="M3 12.5 7.5 8l3 1.5L14 7l4 1.5 3 4"/><path d="M7.5 8 3 12.5l5 4.5 2-1.5 2 1.5 2-1.5 2 1.5 3.5-4.5"/><path d="M10.5 9.5 8 12c-.7.8.4 2 1.3 1.3L12 11l4 3.5"/>',
        'recycle': '<path d="M8.5 6.5 10.6 3a1.6 1.6 0 0 1 2.8 0l2.3 4"/><path d="m15.7 4.5.1 2.6-2.5.6"/><path d="M19 11.5l2.1 3.6a1.6 1.6 0 0 1-1.4 2.4H15"/><path d="m17 19.5-2-2 1.7-1.9"/><path d="M8.5 17.5H4.3a1.6 1.6 0 0 1-1.4-2.4L5 11.4"/><path d="m3.4 12.2 1.6-.8 1.4 2.2"/>',
        'leaf': '<path d="M5 19c0-8 5-13 15-14-1 10-6 15-14 15"/><path d="M5 19 13 11"/>',
    }
    phil = [
        ('hand', '近隣への配慮', '工程や作業時間を丁寧にお伝えし<br>周辺の生活環境に配慮して施工します。'),
        ('recycle', '適正処分とリサイクル', '廃棄物の分別と適正処分を徹底し<br>循環型社会を目指します。'),
        ('leaf', '省エネルギー', '車両・重機の燃費向上に努め<br>環境負荷の低減に取り組みます。'),
    ]
    phil_html = ''.join(
        f'<li><div class="ol-ph-h"><span class="ol-pn" aria-hidden="true">{n:02d}</span>'
        f'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ph_svg[k]}</svg></div>'
        f'<h3>{t}</h3><p>{d}</p></li>'
        for n, (k, t, d) in enumerate(phil, 1))
    area_rows = ''.join(f'<div><dt>{esc(a["pref"])}</dt><dd>{esc(a["cities"])}</dd></div>' for a in c['area'])
    # 地図（2026-11-18 郵便番号が確かめられたので入れた）。Google マップの埋め込み（鍵は要らない）
    map_fr = (f'<iframe class="ol-map" src="https://maps.google.com/maps?q={quote(ADDRESS)}&amp;z=16&amp;output=embed" '
              f'title="{COMPANY}の地図" loading="lazy" referrerpolicy="no-referrer-when-downgrade"></iframe>')

    return f'''{page_head('outline.html')}
<nav class="ol-jump" aria-label="このページの内容"><div class="wrap"><ul>{jump_html}</ul></div></nav>

<section class="sec ol-msg has-wm" data-wm="MESSAGE" id="ol-msg" aria-labelledby="h-msg">
<div class="wrap">
<div class="ol-msg-in">
<div class="ol-msg-h"><p class="cm-en" lang="en">MESSAGE</p><h2 class="t-ttl" id="h-msg">社長あいさつ</h2>
<p class="t-ttl ol-big">解体のことは<br>解体の専門家へ</p></div>
<div class="ol-msg-b">
{''.join(f'<p>{esc(p)}</p>' for p in c['greeting'])}
<p class="ol-sign">株式会社 丸信　代表取締役　灰崎 信吉</p>
{todo('社長あいさつの文章（2013年ごろの文章です。このまま載せてよいか）')}
</div>
</div>
<ul class="ol-pics">{pics_html}</ul>
</div>
</section>

<section class="sec ol-prof has-wm" data-wm="PROFILE" id="ol-prof" aria-labelledby="h-prof">
<div class="wrap t-two">
<div><p class="cm-en" lang="en">PROFILE</p><h2 class="t-ttl" id="h-prof">会社概要</h2></div>
<dl class="ol-dl">{rows(c['profile'])}</dl>
</div>
</section>

<section class="sec ol-lic-sec has-wm" data-wm="LICENSE" id="ol-lic" aria-labelledby="h-lic">
<div class="wrap t-two">
<div><p class="cm-en" lang="en">LICENSE</p><h2 class="t-ttl" id="h-lic">許可・登録</h2></div>
<ul class="ol-lic">{lic_html}</ul>
</div>
</section>

<section class="sec ol-phil-sec has-wm" data-wm="PHILOSOPHY" aria-labelledby="h-phil">
<div class="wrap">
<div class="ol-phil-h"><div><p class="cm-en" lang="en">PHILOSOPHY</p><h2 class="t-ttl" id="h-phil">企業理念・経営方針</h2></div>
<p class="ol-phil-c">近隣の皆様への配慮と<br>環境に向き合う施工を</p></div>
<ul class="ol-phil">{phil_html}</ul>
</div>
</section>

<section class="sec ar-sec ol-ar has-wm" data-wm="AREA" id="ol-area" aria-labelledby="h-area">
<div class="wrap t-two">
<div><p class="cm-en" lang="en">AREA</p><h2 class="t-ttl" id="h-area">対応エリア</h2></div>
<div><p class="ol-c">春日井市を中心に<br>東海3県へ</p><dl class="ar">{area_rows}</dl>
<p class="ar-note">{esc(c["area_note"])}。その他の地域もお気軽にご相談ください。</p></div>
</div>
</section>

<section class="sec ol-acc has-wm" data-wm="ACCESS" id="ol-acc" aria-labelledby="h-acc">
<div class="wrap t-two">
<div><p class="cm-en" lang="en">ACCESS</p><h2 class="t-ttl" id="h-acc">所在地・アクセス</h2></div>
<div class="ol-acc-in"><div><p class="ol-addr">〒{POSTAL}<br>{ADDRESS}</p></div>
{map_fr}</div>
</div>
</section>

{ct_band()}'''


def page_contact():
    connected = bool(FORM_ENDPOINT)
    notice = '' if connected else ('<div class="unconnected" role="note"><b>このフォームの送信機能は未接続です。</b>'
                                   '「送信」を押しても、入力した内容はどこにも送られません。お急ぎの場合はお電話でご連絡ください。</div>')
    if not connected:
        TODOS.append((CUR, 0, 'お問い合わせフォームの送り先（受け取るメールアドレス）'))

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
    """プライバシーポリシー。2026-11-20 松本さん「案を作って」で、2013年の文章を今の個人情報保護法に合わせて書き直した
    （事業者の住所・代表者、安全管理の取り組み、開示などの請求、窓口を足し、使っていない「新商品のお知らせ」を外した）"""
    pol = load('policy.json')
    secs = ''.join(f'<section class="pol-sec"><h2><span class="pol-n" aria-hidden="true">{i:02d}</span>{esc(s["h"])}</h2>\n{body_html(s["p"])}</section>'
                   for i, s in enumerate(pol, 1))
    return f'''{page_head('policy.html')}
<section class="sec">
<div class="wrap wrap-s">
{secs}
{'' if RELEASE else '<p class="pol-date">改定日：公開する日を入れます</p>'}
{todo('プライバシーポリシーの内容（今の法律に合わせて書き直した案です。窓口のアドレス・委託先・書類の管理のしかたが実際と合っているか）')}
</div>
</section>'''


# 文章の中の印では表せない、全体にかかわる確認事項（check.html と --release の案内に出す）
GENERAL = [
    'トップと各ページ上部の写真は、イメージ写真です（丸信様の現場ではありません）。現場の写真をいただければ差し替えます',
    '採用情報は、今お使いの採用ページ（AirWORK）へつないでいます',
]


# 確認事項の優先度（2026-11-20 松本さん「優先度がわかるように」）。label に含まれる言葉で決める。
# 高＝公開すると実害がある（問い合わせが届かない・法律に触れる・揉めごとになる）、中＝公開前に直したい、低＝公開後でもよい
PRIO = [
    # (label に含まれる言葉, 優先度, 公開した場合に困ること, 丸信さんにお願いしたいこと, EWCだけで片づくか)
    # EWCだけで片づくものは確認一覧（丸信さんに見てもらうページ）に出さない。README の「EWC側でやること」に残す（2026-11-20 松本さん）
    ('お問い合わせフォームの送り先', '高', 'フォームから送られたご相談がどこにも届かず、お問い合わせを逃してしまいます',
     'ホームページからのお問い合わせを受け取るメールアドレスを教えてください（今のサイトのフォームがどのアドレスに届いていたかでも構いません）', False),
    ('料金の金額', '高', '今の料金と違うと「ホームページと違う」とお客様と行き違いになります。表示と実際が違うと景品表示法の問題になるおそれもあります',
     '今もこの金額でよいか、変わっていれば今の金額を教えてください', False),
    ('税込・税別', '高', '一般のお客様向けに料金を載せるときは、税込みの総額で表示する決まり（総額表示の義務）があります',
     '料金表の金額が税込みか税別かを教えてください', False),
    ('産業廃棄物の許可番号', '高', '期限の切れた番号を載せると、誤った許可の表示になります（許可は5年ごとの更新です）',
     '今お持ちの許可証の番号と有効期限を教えてください（写しでも構いません）', False),
    ('プライバシーポリシーの内容', '高', 'お問い合わせフォームで個人情報をお預かりするため、使い道などを公表することが法律で求められています',
     'EWCで今の法律に合わせた案を作りました。窓口のメールアドレス（info）、書類やパソコンの管理のしかたが実際と合っているかをご確認ください', False),
    ('改定日', '中', '', '', True),
    ('銀行名', '中', '古い銀行名のままだと、お振り込みの際に迷わせてしまいます', '今の銀行名と支店名を教えてください', False),
    ('懲役', '中', '', '', True),
    ('社長あいさつ', '低', '', 'このまま載せてよいか、書き直したいところがあれば教えてください', False),
    ('求人の案内', '低', '', '「未経験者歓迎」など、求人の案内に載せたい言葉があれば教えてください', False),
]
PRIO_ORDER = {'高': 0, '中': 1, '低': 2}


def prio_of(label):
    for key, lv, why, ask, ewc in PRIO:
        if key in label:
            return lv, why, ask, ewc
    return '低', '', '', False


def page_check():
    """要確認の一覧（確認用にだけ作る）。優先度の高い順に、どのページのどこかと理由・誰が決めるかを並べる"""
    rows = []
    for f, n, label in TODOS:
        lv, why, ask, ewc = prio_of(label)
        if ewc:
            continue
        rows.append((PRIO_ORDER[lv], f, n, label, lv, why, ask))
    order = lambda label: next((i for i, x in enumerate(PRIO) if x[0] in label), len(PRIO))   # 同じ優先度の中は PRIO に書いた順（実害の大きい順）
    rows.sort(key=lambda r: (r[0], order(r[3])))
    groups = []
    for lv, ttl, lead in (('高', '優先度 高', '公開の前に必ず片づける（公開すると実害がある）'),
                          ('中', '優先度 中', '公開の前に直したい'),
                          ('低', '優先度 低', '公開してから直しても困らない')):
        items = [r for r in rows if r[4] == lv]
        if not items:
            continue
        lis = ''.join(f'''<li class="ck-i"><a class="ck-l" href="{href(f)}{"#todo-%d" % n if n else ""}"><span class="ck-pg">{PAGE[f][1]}</span>{esc(label)}</a>
{f'<p class="ck-why">{esc(why)}</p>' if why else ''}{f'<p class="ck-ask">お願い：{esc(ask)}</p>' if ask else ''}</li>''' for _o, f, n, label, _lv, why, ask in items)
        groups.append(f'<section class="ck-g ck-{PRIO_ORDER[lv]}"><h2 class="ck-h"><span class="ck-badge">{ttl}</span><span>{lead}</span>{'<span class="ck-dl">ご回答：11月25日（水）ごろまで</span>' if lv in ('高', '中') else ''}<span class="ck-n">{len(items)}件</span></h2><ul class="ck-list">{lis}</ul></section>')
    fr = {}
    for f, label in FRAMES:
        fr.setdefault(f, []).append(label)
    fr_html = ''.join(f'<li><a href="{href(f)}">{PAGE[f][1]}</a>：{esc("、".join(v))}</li>' for f, v in fr.items())
    gen = ''.join(f'<li>{esc(g)}</li>' for g in GENERAL)
    body = f'''<div class="ph ph-plain"><div class="ph-in"><div class="ph-ttl"><h1>確認が必要なところの一覧</h1><p class="ph-en">制作中の確認用ページ（公開しません）</p></div></div></div>
<section class="sec"><div class="wrap wrap-m">
<p>新しいホームページの公開の前に、丸信様にご確認いただきたいところです。優先度の高い順に並べています。各ページでは黄色の「要確認」の印が付いています（項目を押すとその場所へ移ります）。</p>
<p class="ck-due"><b>優先度 高・中</b>の項目は、<b>11月25日（水）ごろまで</b>にご回答いただけますと幸いです。新しいホームページの公開（11月30日の週の予定）に間に合わせるためです。分かるところからで構いません。優先度 低の項目は、公開のあとでも大丈夫です。</p>
{''.join(groups)}
{f'<h2 class="h2l mt-xl">写真の仮枠が残っているところ（優先度 低：公開用では枠を出しません）</h2><ul class="dots">{fr_html}</ul>' if fr_html else ''}
<h2 class="h2l mt-xl">お知らせ（ご確認のみ）</h2>
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
        write(fname, layout(fname, builder(), with_cta=(fname not in ('contact.html', 'index.html', 'about.html', 'price.html', 'case.html', 'flow.html', 'outline.html', 'faq.html'))))

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
