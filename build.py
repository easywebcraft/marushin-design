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
RECRUIT_URL = 'https://arwrk.net/recruit/yr19dq6rh1okksq'  # 今の採用サイト（AirWORK）。2026-11-26 から採用情報はサイトの中のページ（recruit.html）にし、求人の「詳細を見る」と応募だけ AirWORK へ
# 求人（2026-11-26 AirWORK に載っている5件。給料などは各求人ページのとおり）
JOBS = [
    ('解体作業員', 'images/recruit/kaitai.jpg', 400, 300,
     'ビル・工場・一般住宅などの解体作業をお任せします。年齢・学歴は問いません。',
     [('日給 1万3000円〜1万5000円', '月給30万円も選べます', '1528501')],
     ['残業ほぼなし', '寮あり', '前職の給与保証']),
    ('重機オペレーター', 'images/recruit/juki.jpg', 400, 250,
     '解体工事の現場で、重機を動かして建物を解体します。車両系建設機械の技能講習の修了が必要です。',
     [('日給 1万7000円〜2万2000円', '月給36万円以上も選べます', '4627236')],
     ['残業ほぼなし', '遠方での勤務なし', '前職の給与保証']),
    ('ダンプドライバー（4t・10t）', 'images/recruit/dump.jpg', 400, 250,
     'ダンプの運転と、廃材の選別・運搬、解体作業を行います。4tは中型免許、10tは大型免許が必要です。',
     [('4t 日給 1万5000円〜2万円', '', '4627177'), ('10t 日給 1万6000円〜2万円', '月給35万円以上も選べます', '4627203')],
     ['残業ほぼなし', '遠方での勤務なし', '前職の給与保証']),
    ('監理技術者', 'images/recruit/kanri.jpg', 400, 250,
     'お客様との打ち合わせ、施工計画書や官公庁への書類の作成、協力業者さんへの発注、工程の管理を担当します。',
     [('月給 30万円〜45万円', '1級施工管理技士は45万円以上', '1528560')],
     ['週休2日制', '営業車貸与（通勤にも可）', '前職の給与保証']),
]
# 求人ごとの詳しい条件（2026-11-26 AirWORK の各求人ページのとおり）。ページの中で開いて見せ、応募だけ AirWORK へ（松本さん「3で」）
HOLI_DAY = '日給の方：希望の曜日に休めます'
JOB_COND = {
    '解体作業員': [
        ('仕事内容', ['ビル・工場・一般住宅などの解体作業']),
        ('給与', ['日給 13,000円〜15,000円、または月給 30万円（どちらか選べます）', '前職の給与保証あり', '交通費 規定支給（月1万円まで）']),
        ('勤務時間', ['8:00〜17:00（休憩90分）', '残業ほぼなし']),
        ('休日', [HOLI_DAY, '月給の方：週休2日制（日・祝日＋ほか1日・当社カレンダー）', '夏季休暇・年末年始休暇', '土曜の休みも相談できます']),
        ('応募の条件', ['年齢・学歴は問いません', '解体工事の経験がある方は優遇します']),
        ('福利厚生', ['社会保険完備', '昇給・賞与 年2回', '寮あり（単身用・世帯用）']),
    ],
    '重機オペレーター': [
        ('仕事内容', ['解体工事の現場で、重機を使った解体作業（ビル・工場・一般住宅など）']),
        ('給与', ['日給 17,000円〜22,000円、または月給 36万円以上（どちらか選べます）', '前職の給与保証あり', '交通費 規定支給（月1万円まで）']),
        ('勤務時間', ['8:00〜17:00（休憩90分）', '残業ほぼなし']),
        ('休日', [HOLI_DAY, '月給の方：週休2日制（日・祝日＋ほか1日・当社カレンダー）', '夏季休暇・年末年始休暇']),
        ('応募の条件', ['車両系建設機械（解体用）運転技能講習の修了', '車両系建設機械（整地・運搬・積込み用及び掘削用）運転技能講習の修了']),
        ('福利厚生', ['社会保険完備', '賞与（8月・12月。入社半年後からそれぞれ10万円以上）', '能力次第で随時昇給', '退職金制度（中退共）・資格取得の支援・制服貸与']),
    ],
    'ダンプドライバー（4t・10t）': [
        ('仕事内容', ['ダンプの運転と、解体作業・廃材の選別・運搬', '現場は春日井市から車で1時間ほどのエリア内']),
        ('給与', ['4t：日給 15,000円〜20,000円', '10t：日給 16,000円〜20,000円', 'どちらも月給 35万円以上も選べます', '交通費 規定支給']),
        ('勤務時間', ['8:00〜17:00（休憩90分・現場によります）', '残業ほぼなし']),
        ('休日', [HOLI_DAY, '月給の方：週休2日制（当社カレンダー）', '夏季休暇・年末年始休暇']),
        ('応募の条件', ['4t：中型自動車免許（AT限定不可）以上', '10t：大型自動車免許', '未経験の方も歓迎します']),
        ('福利厚生', ['社会保険完備', '賞与（8月・12月。入社半年後からそれぞれ10万円以上）', '能力次第で随時昇給', '退職金制度（中退共）・資格取得の支援・制服貸与']),
    ],
    '監理技術者': [
        ('仕事内容', ['お客様との打ち合わせ、施工計画書や官公庁への書類の作成', '協力業者さんとの折衝・発注、工程の管理、現場での技術の指導']),
        ('給与', ['月給 30万円〜45万円', '1級施工管理技士（土木・建築）：45万円以上／2級：35万円以上／資格なし：30万円以上', '前職の給与保証あり', '交通費 規定支給（月1万円まで）']),
        ('勤務時間', ['8:00〜17:00（休憩90分）', '残業ほぼなし']),
        ('休日', ['週休2日制', '夏季休暇・年末年始休暇']),
        ('応募の条件', ['普通自動車免許（AT限定可）', '1級・2級の土木／建築施工管理技士があれば尚可']),
        ('福利厚生', ['社会保険完備', '昇給・賞与 年2回', '寮あり（単身用・世帯用）', '営業車の貸与（通勤にも使えます）']),
    ],
}
# お問い合わせフォームの送り先。決まるまでは空（＝未接続。画面に「未接続」と出し、「送信しました」とは出さない）
FORM_ENDPOINT = ''

# ページの一覧：(ファイル名, 名前, 英字, ヘッダーに出すか, 説明文)
PAGES = [
    ('index.html', 'ホーム', '', False,
     '解体のご相談なら、愛知県（春日井市・小牧市・尾張旭市・瀬戸市・名古屋市等）の株式会社丸信へ。事業内容・施工事例・料金表・施工の流れを掲載しています。'),
    ('about.html', '丸信について', 'ABOUT', True,
     '株式会社丸信の解体工事への考え方、近隣への配慮、対応する工事、対応エリアをご紹介します。'),
    ('jigyo.html', '事業内容', 'SERVICE', True,
     '株式会社丸信の事業内容です。木造から鉄骨造・RC造までの建物解体工事、アスベスト（石綿）の調査・除去工事、産業廃棄物の収集運搬・適正処理を行います。'),
    ('price.html', '料金表', 'PRICE', True,
     '木造・鉄骨造・鉄筋コンクリート造の解体工事の料金表と、庭木伐採・ブロック塀などその他の料金を掲載しています。'),
    ('case.html', '施工事例', 'WORKS', True,
     '株式会社丸信が施工した解体工事の事例を、施工前・施工後の写真でご紹介します。'),
    ('flow.html', '施工の流れ', 'FLOW', True,
     'ご相談・お見積もりから、届出、近隣へのご挨拶、解体工事、整地、工事終了のご挨拶までの流れをご説明します。'),
    ('outline.html', '会社案内', 'COMPANY', True,
     '株式会社丸信の会社概要、社長あいさつ、経営方針、許可・保有資格、所在地をご案内します。'),
    ('voice.html', 'お客様の声', 'VOICE', False,
     '解体工事を施工させていただいたお客様からいただいたお言葉をご紹介します。'),
    ('faq.html', 'よくある質問', 'FAQ', True,
     'お見積もり、対応エリア、工事の内容、工事前後の準備や手続きなど、解体工事についてよくいただくご質問にお答えします。'),
    ('contact.html', 'お問い合わせ', 'CONTACT', False,
     '解体工事のご相談・お見積もりは、お電話またはお問い合わせフォームからご連絡ください。'),
    ('recruit.html', '採用情報', 'RECRUIT', False,
     '株式会社丸信の採用情報です。解体作業員・重機オペレーター・ダンプドライバー・監理技術者の求人、福利厚生、社員インタビューをご紹介します。'),
    ('policy.html', 'プライバシーポリシー', 'PRIVACY POLICY', False,
     '株式会社丸信のプライバシーポリシー（個人情報の取り扱い）です。'),
]
PAGE = {p[0]: p for p in PAGES}
# 上のメニュー（2026-11-25 丸信さんのエクセル「メニュー」）。子の項目はプルダウンで出す
NAV = [
    ('about.html', '丸信について', []),
    ('jigyo.html', '事業内容', [('case.html', '施工事例'), ('flow.html', '施工の流れ')]),
    ('price.html', '料金表', [('price.html#demolition', '解体工事料金'), ('price.html#other', 'その他料金')]),
    ('outline.html', '会社案内', [('outline.html#ol-prof', '会社概要'), ('outline.html#ol-msg', '社長あいさつ'), ('outline.html#ol-phil', '経営方針')]),
    ('faq.html', 'よくある質問', []),
]
# お問い合わせフォームの送り先（2026-11-25 丸信さん回答）。フォームをつなぐときに使う
FORM_TO = 'info@marushin-kaitai.com'
# 下層ページの上の写真の見せる位置（同じ写真でも、ページごとに少し変える）
PH_POS = '75% 58%'   # 下層ページ上の写真の切り取り位置。2026-11-20 松本さん「見え方を統一して」で全ページ同じに（重機の全体が入る位置）
# ページごとの上の写真（2026-11-21 松本さんにいただいた4枚。1536×1024）。ここに無いページは重機の写真（images/hero.jpg・PH_POS）
PH_IMG = {
    'about.html': ('images/ph/about.jpg', '74% 60%'),    # ヘルメット・手袋・安全靴
    'price.html': ('images/ph/price.jpg', '62% 50%'),    # 電卓と図面とヘルメット
    'case.html': ('images/ph/case.jpg', '80% 62%'),      # 更地と小さい重機
    'flow.html': ('images/ph/flow.jpg', '62% 55%'),      # 工程表とヘルメット
    'outline.html': ('images/ph/outline.jpg', '72% 60%'),  # 打ち合わせの部屋
    'faq.html': ('images/ph/faq.jpg', '58% 55%'),        # はてなマーク
    'jigyo.html': ('images/top/fv-1.jpg', '62% 50%'),    # 重機（トップの最初の写真）
    'voice.html': ('images/ph/voice.jpg', '68% 58%'),    # 吹き出し
    'policy.html': ('images/ph/policy.jpg', '62% 60%'),  # 鍵を掛けたファイル
    'contact.html': ('images/ph/contact.jpg', '70% 42%'),  # 封筒とメモ
}

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
    # 2026-11-20 松本さん「ページ内の要確認は削除して」：黄色の印は出さず、一覧から飛べるよう見えない目印だけ置く
    return f'<span class="todo-at" id="todo-{n}"></span>'


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
    # 先頭が既定の色（style.css の :root と同じ値・上書きなし）。2026-11-20 松本さん「濃紺×金茶をデフォルトに」で入れ替え
    ('gold', '濃紺×金茶（今の色）', '#142640', '#8E7034', {}),
    ('base', '紺×青緑', '#17354B', '#147F8D', {'navy': '#17354B', 'navy-d': '#102838', 'teal': '#38A8B8', 'teal-d': '#147F8D', 'teal-dd': '#0E6773',
                                          'pale': '#E6F1F6', 'pale2': '#F3F8FB', 'line': '#D3E0E8', 'tint': '#D5ECEE', 'bg1': '#eef5f9', 'bg2': '#dde9f0'}),
    ('brick', '紺×赤茶', '#1E2B3C', '#A9502A', {'navy': '#1E2B3C', 'navy-d': '#141E2B', 'teal': '#D0784F', 'teal-d': '#A9502A', 'teal-dd': '#8A3E1F',
                                           'pale': '#F4ECE6', 'pale2': '#FAF6F2', 'line': '#E5D8CE', 'tint': '#F2DCCF', 'bg1': '#F8F2EE', 'bg2': '#EBDFD6'}),
    ('orange', '黒×オレンジ', '#24282D', '#C66A0A', {'navy': '#24282D', 'navy-d': '#17191C', 'teal': '#F29A2E', 'teal-d': '#C66A0A', 'teal-dd': '#A3560A',
                                                  'pale': '#F5F1EA', 'pale2': '#FAF8F4', 'line': '#E4DDD2', 'tint': '#FBE3C4', 'bg1': '#F9F6F1', 'bg2': '#ECE5DA'}),
    ('green', '深緑×緑', '#1E3A2F', '#2F7A4A', {'navy': '#1E3A2F', 'navy-d': '#142820', 'teal': '#5E9C6E', 'teal-d': '#2F7A4A', 'teal-dd': '#22603A',
                                          'pale': '#E9F2EC', 'pale2': '#F4F9F5', 'line': '#D3E3D8', 'tint': '#D4EBDC', 'bg1': '#F0F6F2', 'bg2': '#DCE9E0'}),
    # 2026-11-20 営業との打ち合わせで7種類に。派手さを抑えた落ち着いた色を足した
    ('brown', '焦げ茶×黄土', '#3A2A1E', '#8C6A33', {'navy': '#3A2A1E', 'navy-d': '#271C13', 'teal': '#B08A4E', 'teal-d': '#8C6A33', 'teal-dd': '#6E5226',
                                         'pale': '#F3EEE6', 'pale2': '#FAF7F2', 'line': '#E3D9CB', 'tint': '#EADFC9', 'bg1': '#F7F3EC', 'bg2': '#E9E0D2'}),
    ('gray', '墨×グレー', '#2B2F33', '#56616B', {'navy': '#2B2F33', 'navy-d': '#1C1F22', 'teal': '#7A8590', 'teal-d': '#56616B', 'teal-dd': '#434C54',
                                      'pale': '#EEF0F2', 'pale2': '#F7F8F9', 'line': '#DADEE2', 'tint': '#DDE2E7', 'bg1': '#F3F5F6', 'bg2': '#E3E7EA'}),
]


def theme_head():
    """色の切り替えの見た目と、ページを開いた直後に選んだ色を当てる短い処理（ちらつかないよう head に置く）"""
    css = ''.join(f':root[data-theme="{k}"]{{' + ''.join(f'--{n}:{v};' for n, v in vs.items()) + '}' for k, _n, _a, _b, vs in THEMES if vs)
    css += ('.tsw{position:fixed;right:60px;bottom:14px;z-index:57;font-size:13px}'
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
            '@media (max-width:767px){.tsw{right:36px;bottom:84px}}'
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
          'var mark=function(){var k=r.getAttribute("data-theme")||"' + THEMES[0][0] + '",bn=r.getAttribute("data-banner")==="open"?"open":"tab";'
          'Array.prototype.forEach.call(l.querySelectorAll("button[data-k]"),function(x){x.setAttribute("aria-pressed",x.getAttribute("data-k")===k?"true":"false")});'
          'Array.prototype.forEach.call(l.querySelectorAll("button[data-b]"),function(x){x.setAttribute("aria-pressed",x.getAttribute("data-b")===bn?"true":"false")})};'
          'b.addEventListener("click",function(){var o=l.hidden;l.hidden=!o;b.setAttribute("aria-expanded",o?"true":"false")});'
          'l.addEventListener("click",function(e){var y=e.target.closest("button[data-b]");if(y){var bn=y.getAttribute("data-b");'
          'if(bn==="open")r.setAttribute("data-banner","open");else r.removeAttribute("data-banner");try{localStorage.setItem("msbanner",bn)}catch(e){}'
          'if(window.msBannerMode)window.msBannerMode();mark();return}'
          'var x=e.target.closest("button[data-k]");if(!x)return;var k=x.getAttribute("data-k");'
          'if(k==="' + THEMES[0][0] + '")r.removeAttribute("data-theme");else r.setAttribute("data-theme",k);try{localStorage.setItem("mstheme",k)}catch(e){}mark()});'
          'document.addEventListener("click",function(e){if(!w.contains(e.target)){l.hidden=true;b.setAttribute("aria-expanded","false")}});mark()})();')
    return (f'<div class="tsw" id="tsw"><ul class="tsw-list" hidden><li><p class="tsw-h">色の案</p></li>{items}{banners}<li><p>選ぶとすぐにサイト全体が切り替わります。採用バナーはトップページを少し下へ進めると出ます</p></li></ul>'
            f'<button class="tsw-btn" type="button" aria-expanded="false"><span class="tsw-dot"></span>色・表示を選ぶ</button></div>\n<script>{js}</script>\n')


def head(fname, title, desc):
    robots = '' if RELEASE else '<meta name="robots" content="noindex,nofollow">\n'
    canonical = ''
    if RELEASE and SITE_URL:
        path = '' if fname == 'index.html' else fname
        canonical = (f'<link rel="canonical" href="{SITE_URL}/{path}">\n'
                     f'<meta property="og:url" content="{SITE_URL}/{path}">\n')
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
{ogimg}<link rel="icon" href="favicon.ico" sizes="32x32">
<link rel="icon" href="images/icon/icon-192.png" type="image/png" sizes="192x192">
<link rel="apple-touch-icon" href="images/icon/apple-touch-icon.png">
<link rel="stylesheet" href="assets/style.css?v={ASSET_V}">
{EWL_HEAD if fname == 'index.html' else ''}{'' if RELEASE else theme_head()}</head>'''


def header(fname):
    items = []
    for f, name, subs in NAV:
        mine = fname == f or any(s.split('#')[0] == fname for s, _t in subs)
        cur = ' aria-current="page"' if mine else ''
        if not subs:
            items.append(f'<li><a href="{f}"{cur}>{name}</a></li>')
            continue
        sub = ''.join(f'<li><a href="{s}">{t}</a></li>' for s, t in subs)
        items.append(f'<li class="has-sub"><a href="{f}"{cur} aria-haspopup="true">{name}{ic("chev", "ic gnav-dn")}</a><ul class="gnav-sub">{sub}</ul></li>')
    # 採用情報はサイトの中のページへ（2026-11-26 丸信さんの作り変え案。それまでは AirWORK へ直接）
    items.append(f'<li><a href="recruit.html"{" aria-current=\"page\"" if fname == "recruit.html" else ""}>採用情報</a></li>')
    # スマホのメニューは2列のボタンで1画面に収める（2026-11-25 松本さん「案2」）。ページの中の見出しへの飛び先は載せない
    drawer = []
    for f in ('about.html', 'jigyo.html', 'case.html', 'flow.html', 'price.html', 'outline.html', 'faq.html', 'contact.html'):
        cur = ' aria-current="page"' if f == fname else ''
        drawer.append(f'<li><a href="{f}"{cur}>{PAGE[f][1]}{ic("chev")}</a></li>')
    drawer.append(f'<li><a href="recruit.html"{" aria-current=\"page\"" if fname == "recruit.html" else ""}>採用情報{ic("chev")}</a></li>')
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
<p class="drawer-foot"><a href="./"{' aria-current="page"' if fname == 'index.html' else ''}>ホーム</a><a href="policy.html"{' aria-current="page"' if fname == 'policy.html' else ''}>プライバシーポリシー</a></p>
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
    src, pos = PH_IMG.get(fname, ('images/hero.jpg', PH_POS))
    w, h = (1536, 1024) if fname in PH_IMG else (1600, 1066)
    # 全ページ、松本さんのデザイン案の見せ方（左に英字と大きな明朝の題・右に斜めに切った写真。2026-11-17 丸信について・料金案内から。
    # 2026-11-20 よくある質問・お客様の声・お問い合わせ・プライバシーポリシーもそろえた）
    # 長い題は、写真の見え方を変えずにすむよう、スマホでは言葉の切れ目で2行に折る（2026-11-20）
    ttl = name.replace('プライバシーポリシー', '<span class="ib">プライバシー</span><span class="ib">ポリシー</span>')
    return f'''<div class="ph ph-au">
<div class="ph-img"><img src="{src}" alt="" width="{w}" height="{h}" style="object-position:{pos}"></div>
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


def qa_html(item, n, num=False):
    """num=True で「Q01」のように通し番号を出す（よくある質問のページ。番号は丸信さんのエクセルの順）"""
    t = todo(item['todo']) if item.get('todo') else ''
    q = f'Q<small>{n:02d}</small>' if num else 'Q'
    return f'''<details class="qa" id="q{n}">
<summary><span class="qa-q" aria-hidden="true">{q}</span><span class="qa-t">{esc(item["q"])}</span><span class="qa-ic" aria-hidden="true"></span></summary>
<div class="qa-a"><span class="qa-m" aria-hidden="true">A</span><div class="qa-b">
{body_html(item["a"])}{t}
<p class="qa-ct"><span class="nw">{COMPANY}</span>　<span class="nw">TEL：<a href="{TEL_HREF}">{TEL}</a></span>　<span class="nw">E-Mail：<a href="mailto:{FORM_TO}">{FORM_TO}</a></span></p>
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


def sanpai_prefs(company):
    """産業廃棄物収集運搬業の許可がある県（company.json の許可から）"""
    perm = {r['k']: r['v'] for r in company['permits']}
    return [x.split()[0] for x in perm['産業廃棄物収集運搬業許可']]


def eco_block(company):
    """法令と環境への取り組み（会社の理念・方針の文を言い換えたもの。新しいことは足さない）。
    2026-11-20 トップから「丸信について」の方針の下へ移した"""
    eco = [
        ('法令にもとづく施工', '契約内容と建設リサイクル法にもとづいた施工計画を守り、ご依頼の目的に沿った工事を行います。'),
        ('廃棄物の適正な処分', f'解体で出た廃棄物を正しく分けて処分し、リサイクルで排出を減らします。産業廃棄物収集運搬業の許可（{"・".join(sanpai_prefs(company))}）を持っています。'),
        ('汚染土壌の浄化', '汚染された土壌の浄化に取り組んでいます。'),
        ('車両と重機の省エネ', '解体工事で使う車両・重機の燃費の向上に努めます。'),
    ]
    items = ''.join(f'<li><h4>{t}</h4><p>{d}</p></li>' for t, d in eco)
    return f'<div class="eco"><h3 class="eco-ttl">法令と環境への取り組み</h3><ul class="eco-l">{items}</ul></div>'


# 対応する工事の種類と絵（「丸信について」とトップで同じものを使う）
KINDS = [('home', '木造住宅'), ('steel', '鉄骨造'), ('rc', '鉄筋コンクリート造'), ('shop', '店舗・事務所')]
KIND_SVG = {
    'home': '<path d="M4 11.5 12 5l8 6.5"/><path d="M6 10v9h12v-9"/><path d="M10 19v-5h4v5"/>',
    'steel': '<path d="M3 10h18M5 10l7-5 7 5"/><path d="M6 10v10M18 10v10M12 10v10M6 15h12"/>',
    'rc': '<rect x="6" y="3.5" width="12" height="17"/><path d="M9 7h2M13 7h2M9 10.5h2M13 10.5h2M9 14h2M13 14h2M11 20.5v-3h2v3"/>',
    'shop': '<path d="M4 9h16l-1.5-4.5h-13z"/><path d="M4 9c0 1.4 1 2.3 2.3 2.3S8.7 10.4 8.7 9c0 1.4 1 2.3 2.3 2.3S13.3 10.4 13.3 9c0 1.4 1 2.3 2.3 2.3S18 10.4 18 9"/><path d="M5.5 11.5V20h13v-8.5M10 20v-5h4v5"/>',
}


def kinds_list():
    return ''.join(
        f'<li><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{KIND_SVG[k]}</svg>{t}</li>'
        for k, t in KINDS)


def work_card(w, h='h3', lazy=True, cmp=False):
    """施工事例の1件（トップと施工事例のページで共通）。
    cmp=True（施工事例のページ）：施工前と施工後を同じ大きさで重ね、つまみを左右に動かして見比べる（.wk-rng・.wk-hdl。2026-11-21 松本さん
    「施工事例を見比べやすくする」→ 同日「TOPは前の案に戻して、施工事例のページは今のままでOK」）。トップは下の経緯のとおり：2026-11-17 松本さんのデザイン案 → 2026-11-20 松本さん「施工前を大きく、施工後を小さく添える」、
    同日「施工事例ページの見せ方もTOPに合わせて」：施工前を大きく、施工後を右下に小さく重ねる。下に「構造｜場所」の1行と題"""
    title = f'{esc(w["place"])} {esc(w["name"])}'
    meta = '｜'.join(f'<span class="nw">{esc(x)}</span>' for x in (w['type'], w['place']) if x)   # スマホで場所の途中で折り返さないように
    note = f'<p class="wk-note">{esc(w["note"])}</p>' if w['note'] else ''
    lz = ' loading="lazy" decoding="async"' if lazy else ''
    name = esc(w['name']) if w['name'].endswith('工事') else f'{esc(w["name"])} 解体工事'   # 「店舗内装撤去工事」に「解体工事」を重ねない
    if w['name'].endswith('工事') and len(w['name']) > 6:   # 長いひとつながりの名前は「店舗内装／撤去工事」で折り返す（最後の1文字だけ落ちないように。2026-11-21）
        name = f'{esc(w["name"][:-4])}<wbr>{esc(w["name"][-4:])}'
    return (f'<li><div class="wk-ph">'
            f'<figure class="wk-bf"><img src="images/case/{w["id"]}-before.jpg" alt="施工前の写真：{title}" width="1448" height="976"{lz}><figcaption>施工前</figcaption></figure>'
            f'<figure class="wk-af"><img src="images/case/{w["id"]}-after.jpg" alt="施工後の写真：{title}" width="1448" height="976"{lz}><figcaption class="after">施工後</figcaption></figure>'
            + (f'<input class="wk-rng" type="range" min="0" max="100" value="50" aria-label="施工前と施工後を見比べる：{title}">'
               f'<span class="wk-hdl" aria-hidden="true"></span>' if cmp else '') +
            f'</div><div class="wk-info"><p class="wk-meta">{meta}</p><{h} class="wk-ttl">{name}</{h}>{note}</div></li>')


# 古いURL（今のサイト）から新しいページへの転送。公開用の .htaccess に書く（README の「古いURLからの転送」と同じ。2026-11-21）
OLD_FAQ = [
    ('見積もり依頼は無料ですか？', 'q1'), ('対応エリアを教えてください。', 'q2'),
    ('植木や庭石・石垣等も処分してもらえるのですか', 'q4'), ('樹木のみの撤去や駐車場のアスファルトのみの撤', 'q5'),
    ('店舗やビル・マンションなどの解体もお願いでき', 'q6'), ('店舗や事務所の原状回復（内装解体・スケルトン', 'q7'),
    ('屋内に不用品が残っていた場合はどうしたらいい', 'q8'), ('解体工事の期間はどのくらいですか？', 'q11'),
    ('解体工事着工までに準備することはありますか？', 'q9'), ('近隣へのご挨拶はした方が良いでしょうか？', 'q10'),
    ('解体工事前の近所への挨拶は同行してもらえます', 'q10'), ('解体後に手続きなどが必要なんですか？', 'q12'),
    ('安すぎる業者は違法業者の可能性が高いですか？', 'q13'),
]


def htaccess():
    """公開用の .htaccess。https と www の統一は、SSL が使えるようになってから「#」を外す"""
    faq = '\n'.join(f'RewriteRule ^faq/{re.escape(t)}\\.html$ /faq.html#{q} [R=301,L,NE]' for t, q in OLD_FAQ)
    return f'''# 株式会社 丸信（build.py --release が作る。直接書き換えない）
AddDefaultCharset UTF-8
RewriteEngine On

# --- https と www の統一（無料SSLが使えるようになってから「#」を外す。www を付けない形に決めたら 2行目を書き換える） ---
# RewriteCond %{{HTTPS}} off [OR]
# RewriteCond %{{HTTP_HOST}} !^www\\. [NC]
# RewriteRule ^(.*)$ https://www.marushin-kaitai.com/$1 [R=301,L]

# --- 古いURLからの転送 ---
{faq}
RewriteRule ^faq/解体用語集.*\\.html$ /faq.html [R=301,L]
RewriteRule ^(faq|category/faq|category/words)/?$ /faq.html [R=301,L]
RewriteRule ^sitemap\\.html$ / [R=301,L]
RewriteRule ^.+\\.html/trackback/?$ / [R=301,L]
RewriteRule ^(feed|feed/atom)/?$ / [R=301,L]
RewriteRule ^(wp-atom|xmlrpc)\\.php$ / [R=301,L]
RewriteCond %{{QUERY_STRING}} (^|&)p=[0-9]+
RewriteRule ^(index\\.php)?$ /? [R=301,L]
'''


# ---------- 各ページ ----------

def page_index():
    company, works, flow, voice, faq = load('company.json'), load('works.json'), load('flow.json'), load('voice.json'), load('faq.json')
    # 丸信の取り組み（2026-11-17 松本さんのデザイン案のとおり。文は今のサイトの3項目を言い換えたもの）
    cards = [
        ('解体専門の会社に<br>直接相談', '地域に根付いた解体専門の会社です。下請業者への発注による中間マージンが発生しません。'),
        # 2026-11-20 松本さん：前の②（着工前の挨拶）と③（完了後の挨拶）を1つにまとめ、3つ目を廃棄物の処理に
        ('着工前から完了後まで<br>近隣に配慮', '着工前のご挨拶から完了後の確認まで、近隣の皆様に配慮します。万が一のトラブルにも速やかに対応いたします。'),
        ('廃棄物の処理まで<br>責任を持って', '廃棄物は分別して適正に処分し、リサイクルを進めます。産業廃棄物収集運搬業の許可を{}で持っています。'),
    ]
    sanpai = sanpai_prefs(company)
    # 番号の右に絵（2026-11-20 松本さんにいただいた絵を images/top/cm-ic-1〜3.png に切り出し、白地を透明にしたもの）。
    # 色は絵の形で切り抜いてサイトの色を流し込むので、色の切り替えにも合う
    # 2026-11-20 松本さん：白いカード3枚。左上に小さい番号、上から絵・見出し・説明
    # 2026-11-21 松本さん：絵の代わりに、絵を立体にしたような写真（images/top/cm-ph-1〜3.jpg・いただいた画像）をカードの上に
    # （2026-11-21 夜に実際の写真の切り抜き images/top/cm-real-1〜3.jpg に替えたが、松本さん「前の案に戻して」で元に戻した）
    cards_html = ''.join(f'<li><span class="cm-ph"><img src="images/top/cm-ph-{n}.jpg" alt="" width="1000" height="667" loading="lazy" decoding="async"></span>'
                         f'<div class="cm-bd"><span class="cm-n" aria-hidden="true">{n:02d}</span>'
                         f'<h3>{t}</h3><p>{p.format("・".join(x.replace("県", "") for x in sanpai))}</p></div></li>'
                         for n, (t, p) in enumerate(cards, 1))
    works_html = ''.join(work_card(w) for w in works[:3])
    # 施工の流れ（2026-11-17 松本さんのデザイン案）：10段階を4つのまとまりで。中身は施工の流れのページ（data/flow.json）のとおり
    fl = [
        ('chat', 'ご相談・お見積もり', 'お問い合わせから、現地調査・お見積りのご説明まで。'),
        ('doc', 'ご契約・着工準備', 'ご契約、アスベスト調査、届出、近隣へのご挨拶。'),
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
<i class="hero-sl" style="background-image:url(images/top/fv-house.jpg);background-position:52% 50%;animation-delay:5s"></i>
<i class="hero-sl" style="background-image:url(images/top/fv-2.jpg);animation-delay:11s"></i>
<i class="hero-sl" style="background-image:url(images/top/fv-3.jpg);animation-delay:17s"></i>
</div>
<div class="hero-in">
<p class="hero-label">解体から次の一歩へ</p>
<h1>建物の解体は<br><em>丸信へ</em></h1>
<p class="hero-sub">春日井市を中心に、<span class="nw">愛知・岐阜・三重の解体工事を承ります。</span></p>
<div class="hero-btns">
<a class="btn btn-teal btn-lg" href="contact.html">{ic("mail")}無料相談</a>
<a class="btn btn-ghost btn-lg" href="case.html">施工事例を見る{ic("chev")}</a>
</div>
</div>
<span class="hero-scroll" aria-hidden="true">scroll</span>
</section>

<section class="ab-band" aria-labelledby="h-about">
<div class="wrap"><div class="ab-in">
<h2 class="ab-ttl" id="h-about">対応する解体工事</h2>
<ul class="au-kinds" aria-label="対応する工事">{kinds_list()}</ul>
<p class="ab-more"><a class="tlink t-link" href="jigyo.html" aria-label="事業内容を詳しく見る">詳しく見る<svg class="t-arw" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M4 12h15M13.5 6.5 19 12l-5.5 5.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></a></p>
</div></div>
</section>

<section class="sec cm-sec has-wm" data-wm="COMMITMENT" aria-labelledby="h-torikumi">
<div class="wrap cm-cards">
<div class="cm-head">
<div><p class="cm-en" lang="en">OUR COMMITMENT</p>
<h2 class="cm-ttl" id="h-torikumi">丸信のこだわり</h2></div>
</div>
<ol class="cm">{cards_html}</ol>
<p class="center cm-more"><a class="btn btn-navy cm-btn" href="about.html">丸信について詳しく見る{ic("chev")}</a></p>
</div>
</section>

<section class="sec wk-sec has-wm" data-wm="WORKS" aria-labelledby="h-works">
<div class="wrap">
<div class="wk-head">
<div><p class="cm-en" lang="en">WORKS</p><h2 class="wk-ttl-h" id="h-works">施工事例</h2></div>
<p class="wk-lead">これまでに手がけた解体工事の一例です。</p>
</div>
<ol class="wk">{works_html}</ol>
<p class="center cm-more"><a class="btn btn-navy cm-btn" href="case.html">施工事例をもっと見る{ic("chev")}</a></p>
</div>
</section>

<section class="sec vc-sec has-wm" data-wm="VOICE" aria-labelledby="h-voice">
<div class="wrap">
<p class="cm-en" lang="en">VOICE</p><h2 class="t-ttl" id="h-voice">お客様の声</h2>
<ul class="vc">{voices}</ul>
<p class="center t-more"><a class="tlink t-link" href="voice.html">お客様の声を見る<svg class="t-arw" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M4 12h15M13.5 6.5 19 12l-5.5 5.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></a></p>
</div>
</section>

<section class="pr-band has-wm" data-wm="PRICE" aria-labelledby="h-price">
<div class="wrap pr-in">
<div class="pr-h"><p class="cm-en" lang="en">PRICE</p><h2 class="t-ttl" id="h-price">料金表</h2></div>
<p class="pr-tx">建物の種類別の料金と、<br>庭木伐採・ブロック塀などの料金をご覧いただけます。</p>
<a class="btn btn-navy t-btn" href="price.html">料金表を見る{ic("chev")}</a>
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

<section class="sec ar-sec t-ar has-wm" data-wm="AREA" aria-labelledby="h-area">
<div class="wrap t-two">
<div><p class="cm-en" lang="en">AREA</p><h2 class="t-ttl" id="h-area">対応エリア</h2><p class="t-sub">春日井市を中心に近隣エリアへ</p>
<p class="ar-note t-l">{esc(company["area_note"])}。その他の地域もお気軽にご相談ください。</p></div>
<div><dl class="ar">{area_rows}</dl>
<p class="ar-note t-r">{esc(company["area_note"])}。その他の地域もお気軽にご相談ください。</p></div>
</div>
</section>

<section class="sec fq-sec has-wm" data-wm="FAQ" aria-labelledby="h-faq">
<div class="wrap t-two">
<div><p class="cm-en" lang="en">FAQ</p><h2 class="t-ttl" id="h-faq">よくある質問</h2>
<p class="t-sub">解体工事のご依頼前に、よくいただくご質問です。</p>
<p class="t-more t-l"><a class="tlink t-link" href="faq.html">よくある質問をすべて見る<svg class="t-arw" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M4 12h15M13.5 6.5 19 12l-5.5 5.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></a></p></div>
<div><div class="qas fq">{faq_html}</div>
<p class="center t-more t-r"><a class="tlink t-link" href="faq.html">よくある質問をすべて見る<svg class="t-arw" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M4 12h15M13.5 6.5 19 12l-5.5 5.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></a></p></div>
</div>
</section>

{ct_band()}

<div class="rqs" id="rqs">
<aside class="rq" id="rq" aria-label="従業員募集のお知らせ">
<button class="rq-tab" type="button" aria-expanded="false" aria-controls="rq-pop"><span class="rq-tab-new">募集中</span><span class="rq-tab-en" lang="en">RECRUIT</span><span class="rq-tab-ja">採用情報</span></button>
<div class="rq-pop" id="rq-pop">
<a class="rq-in rq-card" href="recruit.html" aria-label="RECRUIT 従業員募集中 株式会社 丸信 採用情報を見る"><span class="rq-top" aria-hidden="true"><span class="rq-tk"><span>{"<span>RECRUIT</span>" * 8}</span></span><span class="rq-ttl">従業員募集中</span><span class="rq-co">株式会社 丸信</span></span><span class="rq-ph" aria-hidden="true"><img src="images/top/recruit-banner.jpg" alt="" width="1122" height="1402" loading="lazy" decoding="async"></span><span class="rq-go" aria-hidden="true">採用情報を見る<span class="rq-go-ar">→</span></span></a>
</div>
</aside>
<aside class="rq rq-blog" id="rq-blog" aria-label="ブログのお知らせ">
<button class="rq-tab" type="button" aria-expanded="false" aria-controls="rq-blog-pop"><span class="rq-tab-new">準備中</span><span class="rq-tab-en" lang="en">BLOG</span><span class="rq-tab-ja">ブログ</span></button>
<div class="rq-pop" id="rq-blog-pop">
<div class="rq-in rq-soon"><p class="rq-soon-en" lang="en">BLOG</p><p class="rq-soon-ttl">ブログ</p><p class="rq-soon-st">ただいま準備中です</p><p class="rq-soon-tx"><span>公開まで</span><span>今しばらくお待ちください</span></p></div>
</div>
</aside>
</div>'''


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
        f'<li><div class="au-card"><span class="au-n" aria-hidden="true">{n:02d}</span><div class="au-tx"><h3>{t}</h3><p>{d}</p>{todo(td) if td else ""}</div></div>{photo(src, lb)}</li>'
        for n, (t, d, src, lb, td) in enumerate(feats, 1))

    kinds_html = kinds_list()
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
<a class="btn btn-navy cm-btn au-btn" href="price.html">料金表を見る{arw}</a></div>
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
{eco_block(company)}
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


def page_jigyo():
    """事業内容（2026-11-25 丸信さんのエクセルで新しく作ったページ）。導入と3つの事業。文はいただいたまま。見出しは句読点なし（決まり）"""
    biz = [
        ('01', 'DEMOLITION', '建物解体工事', '', [
            ('home', '木造解体工事', ['一般住宅やアパート、倉庫などの木造建築物の解体を行います。',
                                    '住宅密集地や狭小地においても、防音・防じんシートの養生や散水を徹底し、近隣の皆様の生活環境に配慮した丁寧な作業を心がけています。']),
            ('steel', '鉄骨造（S造）・RC造解体工事', ['店舗、事務所、工場、マンションなどの中・大型建築物の解体に対応しております。',
                                                 '周辺環境や建物の構造に応じた適切な重機・工法を選定し、徹底した安全管理のもとで確実な施工を行います。']),
            ('shop', '内装解体・スケルトン工事', ['店舗の退去やオフィスの移転、リフォームに伴う内装解体や原状回復工事を承ります。',
                                              '建物の躯体を傷つけない精密な作業と、搬出時の養生・清掃まで細やかに対応いたします。']),
            ('fence', '外構・部分解体工事', ['ブロック塀、カーポート、庭石・樹木の撤去など、敷地内の一部のみの部分解体にも柔軟に対応しております。']),
        ]),
        ('02', 'ASBESTOS', 'アスベスト（石綿）調査・除去工事', [
            '解体・改修工事前に義務付けられているアスベスト（石綿）の事前調査から、行政への届出、飛散防止措置を徹底した除去作業、特別管理産業廃棄物としての適正処分まで一貫して対応いたします。',
            '有資格者による正確な調査と、大気汚染防止法・石綿障害予防規則等の関係法令に基づいた厳格な施工管理により、作業員および近隣の皆様の健康と安全を確実に守ります。'], []),
        ('03', 'WASTE', '産業廃棄物収集運搬・適正処理', [
            '解体工事等に伴い発生する産業廃棄物を、建設リサイクル法および廃棄物処理法に基づき適切に分別・収集運搬いたします。',
            '電子マニフェストにも対応し、最終処分まで透明性の高い適正処理を徹底することで、不法投棄の防止とリサイクル率の向上に努めております。'], []),
    ]
    svg = dict(KIND_SVG)
    svg['fence'] = '<path d="M4 20V8l2-2 2 2v12M10 20V8l2-2 2 2v12M16 20V8l2-2 2 2v12"/><path d="M3 11h18M3 16h18"/>'
    secs = []
    for no, en, ttl, lead, subs in biz:
        lead_html = ''.join(f'<p>{esc(x)}</p>' for x in lead) if lead else ''
        sub_html = ''.join(
            f'<li><h4><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{svg[k]}</svg>{esc(t)}</h4>'
            + ''.join(f'<p>{esc(x)}</p>' for x in ps) + '</li>' for k, t, ps in subs)
        secs.append(f'''<section class="jg-biz" aria-labelledby="h-jg{no}">
<div class="jg-biz-h"><p class="jg-no" lang="en">{no}</p><p class="cm-en" lang="en">{en}</p><h3 class="jg-ttl" id="h-jg{no}">{esc(ttl)}</h3></div>
<div class="jg-biz-b">{lead_html}{f'<ul class="jg-sub">{sub_html}</ul>' if sub_html else ''}</div>
</section>''')
    arw = '<svg class="t-arw" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M4 12h15M13.5 6.5 19 12l-5.5 5.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>'
    return f'''{page_head('jigyo.html')}
<section class="sec jg-intro has-wm" data-wm="SERVICE" aria-labelledby="h-jg">
<div class="wrap">
<p class="cm-en" lang="en">OUR SERVICE</p>
<h2 class="t-ttl jg-catch" id="h-jg">安全・丁寧な施工と適正処理で<br>あらゆる建物の解体から<br>アスベスト除去・環境対策まで一貫対応</h2>
<div class="jg-lead"><p>当社は木造住宅から鉄骨・RC造の大型建築物まで、構造や立地条件に合わせた最適な施工計画を立案し、近隣環境への配慮と法令遵守を徹底した解体工事を行っております。</p>
<p>また、義務化されているアスベスト（石綿）の事前調査・除去工事をはじめ、産業廃棄物の収集運搬や土壌汚染対策など、解体に伴う環境業務にもワンストップで対応しております。</p></div>
{''.join(secs)}
<div class="jg-more"><a class="btn btn-navy cm-btn" href="case.html">施工事例を見る{arw}</a><a class="btn btn-navy cm-btn" href="flow.html">施工の流れを見る{arw}</a><a class="btn btn-navy cm-btn" href="price.html">料金表を見る{arw}</a></div>
</div>
</section>

{ct_band()}'''


def page_price():
    """料金案内。2026-11-17 松本さんのデザイン案の構成に（丸信について・トップと同じ見せ方）。
    2026-11-26 丸信さんの正式版：金額はそのまま。注意書き3行を表の上に・「税別」の表記はなし・生活ゴミの無料に但し書き。
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
        if not m:
            return f'<b>{esc(c)}</b>'
        # 税込みの総額を下に添える（総額表示の義務。2026-11-25 松本さん「決まりの通りでOK」）。税率10%・1円未満は切り捨て
        def inc(x):
            v = float(x.replace(',', '')) * 1.1
            if m.group(2) == '万円':
                return f'{round(v, 3):g}'
            return f'{int(v + 1e-9):,}'
        taxin = _re.sub(r'[0-9][0-9,]*(?:\.[0-9]+)?', lambda n: inc(n.group(0)), m.group(1))
        return (f'<b>{esc(m.group(1))}</b><small>{esc(m.group(2))}{esc(m.group(3))}</small>'
                f'<span class="pr-taxin">（税込{esc(taxin)}{esc(m.group(2))}{esc(m.group(3))}）</span>')
    cards = ''.join(
        f'<li><h3><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{svg.get(st["name"], "")}</svg>{esc(st["name"])}</h3>'
        f'<table class="pr-t"><caption class="vh">{esc(st["name"])}の解体費用（坪単価）</caption>'
        f'<thead><tr><th scope="col">坪数</th><th scope="col">費用（坪単価）</th></tr></thead><tbody>'
        + ''.join(f'<tr><th scope="row">{esc(a)}</th><td>{cost_html(b)}</td></tr>' for a, b in st['rows'])
        + '</tbody></table></li>' for st in price['structures'])
    rows, n = [], 0
    for o in price['others']:
        for what, cost in o['rows']:
            n += 1
            # 生活ゴミの無料は解体工事に伴う処分だけ（2026-11-26 丸信さんの正式版）
            only = '<span class="pr-only">（但し、解体工事に伴う処分に限る）</span>' if cost == '無料' else ''
            rows.append(f'<tr><td class="pr-no">{n}.</td><th scope="row">{esc(o["name"])}</th><td>{esc(what) or "―"}</td><td class="num">{cost_html(cost)}{only}</td></tr>')
    return f'''{page_head('price.html')}
<section class="sec pr-intro">
<div class="wrap">
<h2 class="t-ttl pr-lead-h">解体工事の費用をわかりやすく</h2>
<p class="pr-lead">{esc(price["lead"]).replace("料金表です。", "料金をご案内します。")}</p>
<ul class="pr-jump"><li><a href="#demolition">建物の解体工事{down}</a></li><li><a href="#other">その他の工事・処分{down}</a></li></ul>
</div>
</section>

<section class="sec pr-dm has-wm" data-wm="DEMOLITION" id="demolition" aria-labelledby="h-dm">
<div class="wrap">
<div class="pr-dm-h"><div><p class="cm-en" lang="en">DEMOLITION</p><h2 class="t-ttl" id="h-dm">建物の解体工事</h2></div>
</div>
<ul class="pr-notes"><li>下記金額には、廃材処分費、養生シート張り、コンクリート基礎撤去、整地費用が含まれます。</li><li>金額は坪単価です。（1坪＝3.3m²）</li><li>形状や作業環境等によって変わることがあります。詳しくはご相談ください。</li></ul>
<ul class="pr-cards">{cards}</ul>
</div>
</section>

<section class="sec pr-ot has-wm" data-wm="OTHER WORKS" id="other" aria-labelledby="h-ot">
<div class="wrap">
<p class="cm-en" lang="en">OTHER WORKS</p><h2 class="t-ttl" id="h-ot">その他の工事・処分</h2>
<div class="pr-tw"><table class="pr-ot-t"><caption class="vh">その他の工事・処分の料金</caption>
<thead><tr><th scope="col" colspan="2">項目</th><th scope="col">内容</th><th scope="col" class="num">費用</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div>
{todo('土間コンクリートのはつり・ブロック塀の単位（いただいた表では m³、今のサイトでは m² です。面積の m² で載せています）')}
<div class="pr-info"><span class="pr-i" aria-hidden="true">i</span>
<div><h3>着工前のご準備・別途費用について</h3><p>解体工事着工までのご準備や、別途費用が発生する場合については、<a href="faq.html#q9">よくある質問</a>もご覧ください。</p></div>
<a class="btn pr-info-btn" href="faq.html#q9">よくある質問を見る{arw}</a></div>
<p class="pr-note">{esc(price["note"]).replace("点がございましたら、", "点は")}</p>
</div>
</section>

{ct_band()}'''


def page_case():
    """施工事例。2026-11-17 松本さんのデザイン案の構成に（丸信について・料金案内と同じ見せ方）。
    写真は丸信さんの事例写真（01〜03は届いた大きい写真、04は今のサイトの小さい写真）。見出しは句読点なし。"""
    works = load('works.json')
    items = [work_card(w, 'h2', lazy=n > 2, cmp=True) for n, w in enumerate(works, 1)]
    return f'''{page_head('case.html')}
<section class="sec cs-sec has-wm" data-wm="WORKS" aria-labelledby="h-cs">
<div class="wrap">
<div class="cs-head"><div><p class="cm-en" lang="en">OUR WORKS</p><p class="t-ttl cs-catch" id="h-cs">一つひとつの現場に誠実に</p></div>
<p class="cs-lead">株式会社丸信にて施工を行いました事例をご紹介します。<br>工事完了後の隣家外壁補修工事や駐車場整備工事など、<br>お客様のニーズに幅広くお応えしております。</p></div>
<ol class="wk cs-wk">{''.join(items)}</ol>
<p class="cs-more">※順次、施工事例を追加予定をしております。</p>
</div>
</section>

{ct_band()}'''


def page_flow():
    """施工の流れ。2026-11-17 松本さんのデザイン案の構成に（ほかの下層ページと同じ見せ方）。
    9段階を4つのまとまり（トップの流れと同じ）に分け、左に写真・右に縦の線と STEP。説明は今のサイトの内容を短くしたもの。"""
    flow = load('flow.json')
    arw = '<svg class="t-arw" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M4 12h15M13.5 6.5 19 12l-5.5 5.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>'
    # 2026-11-25 丸信さんのエクセル「施工の流れ」で10段階→9段階に（ご相談と見積りの提出を「現地調査・お見積り」に）
    short = {
        1: 'お電話またはメールフォームでお問い合わせください。現地調査のうえでお見積りし、お見積書は原則手渡しで内容をご説明します。建物・敷地の図面があると正確に見積もれます。',
        2: 'お見積りにご納得いただけましたらご契約です。契約書をお持ちしますので、押印をお願いします。',
        3: '有資格者（建築物石綿含有建材調査者）が調査します。アスベストが見つかった場合は、除去工事を追加でお見積りします。',
        4: '延べ床面積80㎡以上の建物は、着工の7日前までに行政への届出が必要です。書類の作成・提出は当社で代行し、一部のご記入・ご捺印をお願いします。',
        5: '近隣の皆様へご挨拶し、工事の概要や作業工程を丁寧にご説明します。',
        6: '現場の作業環境や状況に合わせて、万全の対策で施工します。',
        7: '廃材を分別して中間処理施設へ搬出します。マニフェスト伝票で処理を記録し、不法投棄を防ぎます。',
        8: '地盤面を平らに整地します。ご要望により砕石を敷いて転圧します。完了後に現場をご確認いただきます。',
        9: 'ご協力への感謝をお伝えするとともに、ご迷惑がなかったかを確認します。',
    }
    title = {}
    tags = {6: ['騒音対策', '振動対策', '粉塵対策', '安全対策', '環境美化対策']}
    phases = [('ご相談・お見積もり', [1], 'flow-1'), ('ご契約・着工準備', [2, 3, 4, 5], 'flow-2'),
              ('解体工事', [6, 7], 'flow-3'), ('整地・工事完了', [8, 9], 'flow-4')]
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
<p class="fw-lead">ご相談頂いてから工事完了までの流れを簡単にご紹介します。</p>
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
{todo('お客様の声のページ（新しいメニューに入っていません。ページごと無くしてよいか）')}
</div>
</section>'''


def page_faq():
    """よくある質問。丸信さんのエクセルの通し番号（Q01〜）の順に1列で並べる（2026-11-25 松本さん。13問なら分類は要らない）。
    見出しは「。」「、」なし（決まり）。答えの中身は faq.json のまま。faq.json の cat は今は使っていない"""
    faq = load('faq.json')
    arw = '<svg class="t-arw" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M4 12h15M13.5 6.5 19 12l-5.5 5.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>'
    qs = ''.join(qa_html(it, n, num=True) for n, it in enumerate(faq['items'], 1))
    qs = qs.replace('<details class="qa"', '<details class="qa" open', 1)   # 最初の1問は開いておき、押すと開くことが伝わるように
    return f'''{page_head('faq.html')}
<section class="sec fq-page">
<div class="wrap">
<div class="fq-intro">
<p class="cm-en fq-intro-en" lang="en">QUESTIONS &amp; ANSWERS</p>
<h2 class="t-ttl">解体工事の疑問にお答えします</h2>
<p class="fq-lead">解体工事について、よくいただくご質問をまとめました。</p>
<p class="fq-hint">質問を押すと回答が開きます。</p>
</div>
<div class="qas fq fq-all">{qs}</div>
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

    jump = [('ol-prof', '会社概要'), ('ol-msg', '社長あいさつ'), ('ol-phil', '経営方針'), ('ol-lic', '許可・保有資格'), ('ol-area', '対応エリア'), ('ol-acc', '所在地')]
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
    ph_svg['law'] = '<path d="M12 4v16M6 20h12M5 8h14"/><path d="M7 8l-3 6h6zM17 8l-3 6h6z"/>'
    ph_svg['up'] = '<path d="M4 18l5-5 4 4 7-8"/><path d="M15 9h5v5"/>'
    # 経営方針の5項目（2026-11-25 丸信さんのエクセル。文はいただいたまま）
    icons = ['law', 'recycle', 'hand', 'leaf', 'up']
    phil_html = ''.join(
        f'<li><div class="ol-ph-h"><span class="ol-pn" aria-hidden="true">{n:02d}</span>'
        f'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ph_svg[k]}</svg></div>'
        f'<h3>{esc(x["h"])}</h3><p>{esc(x["p"])}</p></li>'
        for n, (k, x) in enumerate(zip(icons, c['policy']), 1))
    qual_html = ''.join(f'<li>{esc(q)}</li>' for q in c['qualifications'])
    area_rows = ''.join(f'<div><dt>{esc(a["pref"])}</dt><dd>{esc(a["cities"])}</dd></div>' for a in c['area'])
    # 地図（2026-11-18 郵便番号が確かめられたので入れた）。Google マップの埋め込み（鍵は要らない）
    map_fr = (f'<iframe class="ol-map" src="https://maps.google.com/maps?q={quote(ADDRESS)}&amp;z=16&amp;output=embed" '
              f'title="{COMPANY}の地図" loading="lazy" referrerpolicy="no-referrer-when-downgrade"></iframe>')

    return f'''{page_head('outline.html')}
<nav class="ol-jump" aria-label="このページの内容"><div class="wrap"><ul>{jump_html}</ul></div></nav>

<section class="sec ol-prof has-wm" data-wm="PROFILE" id="ol-prof" aria-labelledby="h-prof">
<div class="wrap t-two">
<div><p class="cm-en" lang="en">PROFILE</p><h2 class="t-ttl" id="h-prof">会社概要</h2></div>
<dl class="ol-dl">{rows(c['profile'])}</dl>
</div>
</section>

<section class="sec ol-msg has-wm" data-wm="MESSAGE" id="ol-msg" aria-labelledby="h-msg">
<div class="wrap">
<div class="ol-msg-in">
<div class="ol-msg-h"><p class="cm-en" lang="en">MESSAGE</p><h2 class="t-ttl" id="h-msg">社長あいさつ</h2>
<p class="t-ttl ol-big">近隣の皆様の暮らしと<br>健康を第一に</p></div>
<div class="ol-msg-b">
{''.join(f'<p>{esc(p)}</p>' for p in c['greeting'])}
<p class="ol-sign">株式会社 丸信　代表取締役　灰﨑 信吉</p>
</div>
</div>
<ul class="ol-pics">{pics_html}</ul>
</div>
</section>

<section class="sec ol-phil-sec has-wm" data-wm="POLICY" id="ol-phil" aria-labelledby="h-phil">
<div class="wrap">
<div class="ol-phil-h"><div><p class="cm-en" lang="en">POLICY</p><h2 class="t-ttl" id="h-phil">経営方針</h2></div>
<p class="ol-phil-c">法令遵守と安全施工を<br>徹底します</p></div>
<ul class="ol-phil">{phil_html}</ul>
</div>
</section>

<section class="sec ol-lic-sec has-wm" data-wm="LICENSE" id="ol-lic" aria-labelledby="h-lic">
<div class="wrap t-two">
<div><p class="cm-en" lang="en">LICENSE</p><h2 class="t-ttl" id="h-lic">許可・保有資格</h2></div>
<div><ul class="ol-lic">{lic_html}</ul>
<div class="ol-qual"><h3>保有資格</h3><ul>{qual_html}</ul><p>{esc(c["qualifications_note"])}</p></div></div>
</div>
</section>

<section class="sec ar-sec ol-ar has-wm" data-wm="AREA" id="ol-area" aria-labelledby="h-area">
<div class="wrap t-two">
<div><p class="cm-en" lang="en">AREA</p><h2 class="t-ttl" id="h-area">対応エリア</h2></div>
<div><p class="ol-c">春日井市を中心に<br>東海3県へ</p><p class="ol-area-l">{esc(c["area_lead"])}</p><dl class="ar">{area_rows}</dl>
<p class="ar-note">※{esc(c["area_more"])}</p></div>
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
        TODOS.append((CUR, 0, f'お問い合わせフォームの接続（送り先は {FORM_TO} に決定。2026-11-25 丸信さん回答）'))

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
</div>
</section>'''


# 文章の中の印では表せない、全体にかかわる確認事項（check.html と --release の案内に出す）
GENERAL = [
    '使用している画像は旧サイトで掲載されていたものを高画質加工したものやイメージ画像となっております。気になる箇所は写真をいただければ差し替え可能です。',
    '採用情報は、今お使いの採用ページ（AirWORK）へつないでいます',
]


# 確認事項の優先度（2026-11-20 松本さん「優先度がわかるように」）。label に含まれる言葉で決める。
# 高＝公開すると実害がある（問い合わせが届かない・法律に触れる・揉めごとになる）、中＝公開前に直したい、低＝公開後でもよい
PRIO = [
    # (label に含まれる言葉, 優先度, 公開した場合に困ること, 丸信さんにお願いしたいこと, EWCだけで片づくか)
    # EWCだけで片づくものは確認一覧（丸信さんに見てもらうページ）に出さない。README の「EWC側でやること」に残す（2026-11-20 松本さん）
    ('お問い合わせフォームの接続', '高', '', '', True),
    ('料金の金額', '高', '今の料金と違うと「ホームページと違う」とお客様と行き違いになります。表示と実際が違うと景品表示法の問題になるおそれもあります',
     '新しい金額が決まりましたらお送りください（今は今のサイトの金額のまま載せています）', False),
    ('料金の税込みの表示', '高', '一般のお客様向けに料金を載せるときは、税込みの総額で表示する決まり（総額表示の義務）があります。税別の金額だけでは決まりに合いません',
     '税別の金額に、税込みの金額を並べて出す形でよいかを教えてください', False),
    ('はつり・ブロック塀の単位', '中', '単位が違うと、お見積りの金額と大きく食い違います',
     'm³（体積）と m²（面積）のどちらが正しいかを教えてください', False),
    ('E-MAIL と主要取引銀行の行', '中', '残す場合、銀行名は今の名前（あいち銀行・三菱ＵＦＪ銀行）に直す必要があります',
     '消してよいか、残すかを教えてください', False),
    ('改定日', '中', '', '', True),
    ('お客様の声のページ', '低', '', '無くすか、残すかを教えてください（残す場合は、メニューの下の段やフッターからつなぎます）', False),
    ('求人の案内', '低', '', '「未経験者歓迎」など、求人の案内に載せたい言葉があれば教えてください', False),
]
PRIO_ORDER = {'高': 0, '中': 1, '低': 2}


def page_recruit():
    """採用情報。2026-11-26 丸信さんの作り変え案（PDF）の順：会社の紹介 → 福利厚生 → 求人（仕事紹介と1つに） → インタビュー。
    見に来る人はまず募集の中身を見たいので、大きな写真・「25年」の事業紹介は載せない（丸信さん「ナシ」）。
    文は今の採用サイト（AirWORK）とPDFのまま。「詳細を見る」と応募は AirWORK の各求人ページへ。
    会社の紹介は、最初の一文と写真だけ出し、3つの話は押すと開く（2026-11-27 松本さん「ABOUT が長い」）"""
    ext = ic('ext')
    jobs = []
    for name, src, w, h, desc, pays, tags in JOBS:
        nw = lambda t: '〜'.join(f'<span class="nw">{esc(x)}</span>' for x in t.split('〜'))   # 金額の途中で折り返さない
        pay = ''.join(f'<p class="rc-pay"><b>{nw(a)}</b>{f"<small>{esc(b)}</small>" if b else ""}</p>' for a, b, _j in pays)
        # 詳しい条件はページの中で開き、応募だけ AirWORK の求人ページへ（2026-11-26 松本さん「3で」）。
        # パソコンでは左に職種の一覧・右に詳しい条件。カーソルを合わせた職種の条件に切り替わる（2026-11-27 松本さん。main.js の rc-job）
        rows = ''.join(f'<div><dt>{esc(k)}</dt><dd>{"<br>".join(esc(x) for x in v)}</dd></div>' for k, v in JOB_COND[name])
        btn = ''.join(
            f'<a class="btn rc-btn" href="{RECRUIT_URL}/{j}/" target="_blank" rel="noopener">'
            f'{"応募する" if len(pays) == 1 else esc(a.split(" ")[0]) + "で応募する"}{ext}<span class="vh">（採用サイト・Airワーク）</span></a>'
            for a, _b, j in pays)
        jobs.append(f'''<li class="rc-job"><img src="{src}" alt="" width="{w}" height="{h}" loading="lazy" decoding="async">
<div class="rc-job-tx"><h3>{esc(name)}</h3><p class="rc-desc">{esc(desc)}</p>{pay}
<ul class="rc-tags">{"".join(f"<li>{esc(t)}</li>" for t in tags)}</ul></div>
<details class="rc-more"><summary>詳しい条件を見る</summary><div class="rc-pop">
<div class="rc-pop-h" aria-hidden="true"><p class="rc-pop-n">{esc(name)}</p>{pay}</div><dl class="rc-cond">{rows}</dl>
<div class="rc-btns">{btn}</div><p class="rc-via">応募は採用サイト（Airワーク）の画面で受け付けています</p></div></details></li>''')
    # 営業は「現在募集しておりません」（丸信さん）。押せる所は置かない
    # 営業も左の一覧に並べる（2026-11-27 松本さん）。右の枠には「現在募集しておりません」を出す。スマホでは開く欄なし
    jobs.append('''<li class="rc-job rc-off"><img src="images/recruit/eigyo.jpg" alt="" width="400" height="250" loading="lazy" decoding="async">
<div class="rc-job-tx"><h3>営業</h3><p class="rc-desc">ゼネコンや住宅メーカー、工務店などからのご依頼で、解体工事の見積もりから施工管理までを行います。</p>
<p class="rc-closed">現在募集しておりません</p></div>
<details class="rc-more"><summary>詳しい条件を見る</summary><div class="rc-pop">
<div class="rc-pop-h" aria-hidden="true"><p class="rc-pop-n">営業</p></div>
<p class="rc-off-msg">現在募集しておりません</p>
<p class="rc-off-tx">ゼネコンや住宅メーカー、工務店などからのご依頼で、解体工事の見積もりから施工管理までを行います。</p></div></details></li>''')
    bens = [('昇給・賞与あり', '昇給 年1回・賞与 年2回'), ('社会保険完備', '厚生年金・健康保険・雇用保険・労災保険'),
            ('退職金制度あり', '勤続2年以上が対象'), ('資格取得の支援', '業務に必要な資格の取得を支援')]
    ben_html = ''.join(f'<li><b>{t}</b><span>{d}</span></li>' for t, d in bens)
    qa = [   # 2026-11-26 丸信さんのPDFの文のまま（今の採用サイトの文を短くしたもの）
        ('未経験でも大丈夫ですか？', [
            '私は未経験で入社しました。以前は水道工事の会社に勤めていました。8年ぐらい働いて資格を取りましたが、何か違うと感じ、転職を決意。丸信に入社して、やっと自分に合った仕事を見つけることができたと実感しています。',
            'まずは、解体工事の現場で水を撒いたり、細かい木切れや樹脂などを拾い集めて分別するなど、手元の作業から始めました。',
            '作業中、現場の状況を見て「建物って、こうやって壊していくんだ！」「こういうことは危険だから気を付けよう」と少しずつ覚えてきました。',
            'わからないことは先輩社員に教えてもらえるので、安心して働けます。']),
        ('お仕事の中で大変なことはありますか？', [
            '現場でいちばん重要なのは安全性への配慮です。',
            '解体工事は、思いのままに建物を壊せばいいわけではありません。周囲の状況を見ながら、壊したものが飛ばないようにしたり、車の通行を止めるなどの気配りや頭を使う必要があります。',
            'また、建物の工法や建材はどんどん進化しているので、この仕事は常に勉強をしなければなりません。']),
        ('お仕事のやりがいはありますか？', [
            'モノを壊してお金を貰えて喜ばれる仕事なんて、めったにありません。マジメな話、現在の建築は、まず古い建物を壊さないと始まらない。',
            '社会に貢献できる仕事だと思います。']),
        ('キャリアプランについて教えてください', [
            '私の場合は入社2年目ぐらいから少しずつ1日や2日で終わる簡単な現場にアタマで入って、協力業者の職人さんに指示をする仕事も任せてもらえるようになりました。',
            '解体工事は奥の深いプロの仕事、私は入社して3年になりますが、手元の仕事をしながら、最近は重機(パワーショベル)を動かせるよう練習しているところです。',
            '業務に必要な免許取得はもちろん会社が支援してくれます。']),
        ('丸信に入って良かった、と思うことは？', [
            '解体工事はサイクルが早いので、色んな現場を経験できて飽きません。',
            'そして、解体業はなくなることのない仕事なので、安定性も魅力です。']),
    ]
    qa_html = ''.join(f'<div class="rc-qa"><h3><span aria-hidden="true">Q.</span>{esc(q)}</h3>{"".join(f"<p>{esc(a)}</p>" for a in ans)}</div>' for q, ans in qa)
    return f'''{page_head('recruit.html')}
<section class="sec rc-about" aria-labelledby="h-rc-about">
<div class="wrap rc-about-in">
<div class="rc-about-tx">
<p class="cm-en" lang="en">ABOUT</p>
<h2 class="t-ttl" id="h-rc-about">現代の建設工事は<br>「解体工事」から始まります</h2>
<p>株式会社丸信は、「壊す」ことのプロ集団として本拠地・春日井を中心に東海3県エリアに密着し、建物の「解体工事」を行う会社です。</p>
<div class="rc-accs">
<details class="rc-acc"><summary>解体について</summary><div class="rc-acc-b">
<p>現在の建築は、まっさらな土地に新しく建てるのではなく、既存の建物を壊してから建てるのが主流です。これまで人々の暮らしを支えてきた建物が、再開発により新しく建造され、よりもっと人々の暮らしを豊かにする。その前提には必ず解体工事があるのです。まさに、これは「創造的破壊」であり、再開発の過程に私たちの技術は必要不可欠です。</p>
</div></details>
<details class="rc-acc"><summary>代表からのメッセージ</summary><div class="rc-acc-b">
<p>現在の建設工事のスタートは「解体工事」から始まります。その重要度の割に、建設現場の裏方的存在で脚光を浴びることはありませんでしたが、2016年6月に建設業許可の改定に伴い、解体工事業が新たに追加されました。これは解体工事が専門職として、行政から認められたと言う事です。</p>
<p>公衆災害の防止、産業廃棄物の適正処理、密集地内での解体技術の向上等、やるべきことは多岐にわたります。着実に安定成長し続ける「解体業界」、そして「株式会社丸信」で、共により魅力的な創造的破壊に取り組んでいきましょう！</p>
</div></details>
<details class="rc-acc"><summary>ご家族の方へ</summary><div class="rc-acc-b">
<p>平成15年に法人化して以来、丁寧な建物解体技術が評価され、お客様が着実に増えています。また、官公庁からの仕事も増え、地域社会にも貢献して参りました。</p>
{todo('「平成15年に法人化して17年」は今の年と合わないため「法人化して以来」にしています')}
<p>作業スタッフは能力次第で随時昇給し、資格取得も会社がバックアップするなど、長く勤められる環境の整備をしています。</p>
<p>建築業界経験者も、全くの未経験者も大歓迎。ご入社される全ての方々を将来の幹部候補としてお迎えしております。</p>
</div></details>
</div>
</div>
<figure class="rc-staff"><img src="images/about-staff.jpg" alt="丸信の社員の集合写真" width="2000" height="1003" loading="lazy" decoding="async"></figure>
</div>
</section>

<section class="sec rc-ben" aria-labelledby="h-rc-ben">
<div class="wrap">
<h2 class="rc-h" id="h-rc-ben">福利厚生</h2>
<ul class="rc-ben-l">{ben_html}</ul>
</div>
</section>

<section class="sec rc-jobs has-wm" data-wm="RECRUIT" id="jobs" aria-labelledby="h-rc-jobs">
<div class="wrap">
<p class="cm-en" lang="en">RECRUIT</p>
<h2 class="t-ttl" id="h-rc-jobs">募集している仕事</h2>
<p class="rc-common"><span class="ib">勤務地：春日井市松河戸町（JR勝川駅より車で5分・車通勤OK）</span><span class="ib">勤務時間：8:00〜17:00</span></p>
<ul class="rc-job-l">{"".join(jobs)}</ul>
<p class="rc-note">応募は「応募する」から採用サイト（Airワーク）の画面で受け付けています。お電話（<a href="{TEL_HREF}">{TEL}</a>）でもお問い合わせいただけます。</p>
</div>
</section>

<section class="sec rc-iv" aria-labelledby="h-rc-iv">
<div class="wrap rc-iv-in">
<p class="cm-en" lang="en">INTERVIEW</p>
<h2 class="t-ttl" id="h-rc-iv">社員インタビュー</h2>
<p class="rc-who">解体作業員　29歳／入社3年目</p>
{qa_html}
</div>
</section>
'''

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
        groups.append(f'<section class="ck-g ck-{PRIO_ORDER[lv]}"><h2 class="ck-h"><span class="ck-badge">{ttl}</span><span>{lead}</span>{'<span class="ck-dl">ご回答：11月26日（木）ごろまで</span>' if lv in ('高', '中') else ''}<span class="ck-n">{len(items)}件</span></h2><ul class="ck-list">{lis}</ul></section>')
    fr = {}
    for f, label in FRAMES:
        fr.setdefault(f, []).append(label)
    fr_html = ''.join(f'<li><a href="{href(f)}">{PAGE[f][1]}</a>：{esc("、".join(v))}</li>' for f, v in fr.items())
    gen = ''.join(f'<li>{esc(g)}</li>' for g in GENERAL)
    body = f'''<div class="ph ph-plain"><div class="ph-in"><div class="ph-ttl"><h1>確認が必要なところの一覧</h1><p class="ph-en">制作中の確認用ページ（公開しません）</p></div></div></div>
<section class="sec"><div class="wrap wrap-m">
<p>新しいホームページの公開の前に、丸信様にご確認いただきたいところです。優先度の高い順に並べています。項目を押すと、そのページの該当する場所へ移ります。</p>
<p class="ck-due"><b>優先度 高・中</b>の項目は、<b>11月26日（木）ごろまで</b>にご回答いただけますと幸いです。新しいホームページの公開（11月30日の週の予定）に間に合わせるためです。分かるところからで構いません。優先度 低の項目は、公開のあとでも大丈夫です。</p>
{''.join(groups)}
{f'<h2 class="h2l mt-xl">写真の仮枠が残っているところ（優先度 低：公開用では枠を出しません）</h2><ul class="dots">{fr_html}</ul>' if fr_html else ''}
<h2 class="h2l mt-xl">お知らせ（ご確認のみ）</h2>
<ul class="dots">{gen}</ul>
</div></section>'''
    return '\n'.join([head('check.html', '確認が必要なところの一覧｜' + COMPANY, '制作中の確認用ページです。'),
                      header('check.html'), body, footer('check.html')])


BUILDERS = {
    'index.html': page_index, 'about.html': page_about, 'jigyo.html': page_jigyo, 'price.html': page_price, 'case.html': page_case,
    'flow.html': page_flow, 'outline.html': page_outline, 'voice.html': page_voice, 'faq.html': page_faq,
    'contact.html': page_contact, 'policy.html': page_policy, 'recruit.html': page_recruit,
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
        write(fname, layout(fname, builder(), with_cta=(fname not in ('contact.html', 'index.html', 'about.html', 'jigyo.html', 'price.html', 'case.html', 'flow.html', 'outline.html', 'faq.html', 'recruit.html'))))

    if RELEASE:
        if (SITE / 'images').exists():
            shutil.rmtree(SITE / 'images')
        shutil.copytree(BASE / 'images', SITE / 'images')
        shutil.copy2(BASE / 'favicon.ico', SITE / 'favicon.ico')
        (SITE / '.htaccess').write_text(htaccess(), encoding='utf-8')   # ブラウザはサイトの一番上の favicon.ico も見に行く（2026-11-21 公開前の点検で追加）
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
