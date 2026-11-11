# 株式会社丸信 ホームページ 作り直し（制作中）

今のホームページ（http://www.marushin-kaitai.com ）を作り直すための置き場所です。

- 確認用のURL（GitHub Pages）：https://easywebcraft.github.io/marushin-design/
- 確認が必要なところの一覧：https://easywebcraft.github.io/marushin-design/check.html
- 営業用の見本（トップ1枚）は別のURL：https://easywebcraft.github.io/ewc-proposals/marushin-kaitai/ （こちらは触らない）
- 本番公開・今のサイトの上書き・DNS の変更は、松本さんの指示があるまで行わない。

## ページ

| ファイル | ページ | 元にした情報 |
| --- | --- | --- |
| `index.html` | トップ | 今のサイト全体 |
| `about.html` | 丸信について | 今の about.html |
| `price.html` | 料金案内 | 今の price.html |
| `case.html` | 施工事例 | 今の case.html（写真4組） |
| `flow.html` | 施工の流れ | 今の flow.html（10段階） |
| `voice.html` | お客様の声 | 今の voice.html（匿名・星の評価なし） |
| `faq.html` | よくある質問 | 今の faq 以下の質問13件を1ページに |
| `outline.html` | 会社案内 | 今の outline.html |
| `contact.html` | お問い合わせ | 今の contact.html（送信は未接続） |
| `policy.html` | プライバシーポリシー | 今の policy.html |
| `check.html` | 確認が必要なところの一覧 | 確認用だけ。公開用には出ない |

用語集・サイトマップのページ・採用ページは作っていない（採用は今の外部サイトへのリンクだけ）。

## 作り方

文章は `data/*.json`、見た目は `src/style.css`、動きは `src/main.js`、組み立ては `build.py`（Python の標準機能だけ）。
ページの HTML を直接書き換えず、元のファイルを直してから作り直す。

```sh
python3 build.py                 # 確認用を、この場所（リポジトリ直下）に書き出す
python3 build.py --release       # 公開用を dist/ に書き出す。確認が残っていれば一覧を出して止まる
python3 build.py --release --force --site-url https://www.marushin-kaitai.com
```

確認用と公開用の違い

| | 確認用 | 公開用（`dist/`） |
| --- | --- | --- |
| 「制作中のページです」の帯 | 出る | 出ない |
| 検索に載せない設定（noindex） | 入る | 入らない |
| 黄色の「要確認」の印 | 出る | 出ない |
| 写真の仮枠 | 出る | 出ない |
| `check.html` | 作る | 作らない |

`raw/`（今のサイトを保存したもの）と `dist/` は、この置き場所には上げない。

## 公開までに決めること

一覧は `check.html` にある（`build.py --release` でも同じ一覧が出る）。大きなものだけ：

- お問い合わせフォームの送り先と送信の仕組み（今は未接続。`build.py` の `FORM_ENDPOINT` が空のあいだは、送信完了の文は出ない）
- 料金表の金額と、税込・税別の表記（今のサイトの表は2013年ごろのもの）
- 郵便番号（今のサイトに 486-0932 と 480-0306 の2通り）と、そのあとの地図
- 建設業許可・産業廃棄物の許可番号、取引銀行の名前、社長あいさつの文章
- 写真（丸信さんの現場・スタッフの写真、施工事例の元の大きさの写真）。トップの大きな写真はイメージ
- 採用情報のリンク先（今は AirWORK。残すかは丸信さんに確認）

## 古いURLからの転送（本番でだけ設定する）

次のページは、今と同じ名前で作ってあるので転送は要らない：
`/`、`about.html`、`price.html`、`case.html`、`flow.html`、`voice.html`、`outline.html`、`contact.html`、`policy.html`

転送が要るもの：

| 古いURL（`http://www.marushin-kaitai.com` の下） | 転送先 |
| --- | --- |
| `/faq`、`/category/faq` | `/faq.html` |
| `/faq/見積もり依頼は無料ですか？.html` | `/faq.html#q1` |
| `/faq/対応エリアを教えてください。.html` | `/faq.html#q2` |
| `/faq/植木や庭石・石垣等も処分してもらえるのですか.html` | `/faq.html#q3` |
| `/faq/樹木のみの撤去や駐車場のアスファルトのみの撤.html` | `/faq.html#q4` |
| `/faq/店舗やビル・マンションなどの解体もお願いでき.html` | `/faq.html#q5` |
| `/faq/店舗や事務所の原状回復（内装解体・スケルトン.html` | `/faq.html#q6` |
| `/faq/屋内に不用品が残っていた場合はどうしたらいい.html` | `/faq.html#q7` |
| `/faq/解体工事の期間はどのくらいですか？.html` | `/faq.html#q8` |
| `/faq/解体工事着工までに準備することはありますか？.html` | `/faq.html#q9` |
| `/faq/近隣へのご挨拶はした方が良いでしょうか？.html` | `/faq.html#q10` |
| `/faq/解体工事前の近所への挨拶は同行してもらえます.html` | `/faq.html#q11` |
| `/faq/解体後に手続きなどが必要なんですか？.html` | `/faq.html#q12` |
| `/faq/安すぎる業者は違法業者の可能性が高いですか？.html` | `/faq.html#q13` |
| `/faq/解体用語集【あ行】.html` 〜 `【ら行】.html`（9ページ）、`/category/words` | `/faq.html`（用語集は作らないため） |
| `/sitemap.html` | `/`（サイトマップのページは作らないため） |
| `/?p=7` などの番号つきURL、`/〜.html/trackback`、`/feed`、`/feed/atom`、`/wp-atom.php`、`/xmlrpc.php` | `/`（今の仕組みが自動で作っていたもの） |

あわせて、`http://` → `https://`、`www` あり・なしのどちらかへの統一も、本番を置くときに決める。
