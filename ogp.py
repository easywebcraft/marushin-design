#!/usr/bin/env python3
"""LINE などに URL を貼ったときに出る写真（OGP画像）を作る。images/ogp.jpg（1200×630）。

    python3 ogp.py

トップの最初の画面を 1200×630 で撮り、メニュー・ボタン・制作中の帯など、写真の中で読めない細かい部品は隠す。
トップの写真や見出しを変えたら撮り直す。
"""
import base64, json, os, random, shutil, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path

sys.path.insert(0, os.path.expanduser('~/.claude/skills/hp-sample/scripts'))
import shoot as sh  # noqa: E402 ― Chrome の場所と開発者用の接続（WS）を借りる

BASE = Path(__file__).parent
W, H = 1200, 630
HIDE = '.ewl,.draft,.gnav,.hd-cta,.burger,.hero-sl,.hero-sub,.hero-btns,.hero-scroll,.img-note,.rqs{display:none!important}.hero{height:630px!important;min-height:630px!important}'


def main():
    port = random.randint(20000, 40000)
    prof, tmp = tempfile.mkdtemp(prefix='chrome-'), tempfile.mkdtemp(prefix='ogp-')
    p = subprocess.Popen([sh.CHROME, '--headless=new', '--hide-scrollbars', f'--remote-debugging-port={port}',
                          f'--user-data-dir={prof}', 'about:blank'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            try:
                page = next(t for t in json.load(urllib.request.urlopen(f'http://127.0.0.1:{port}/json'))
                            if t.get('type') == 'page')
                break
            except Exception:  # noqa: BLE001
                time.sleep(0.1)
        else:
            sys.exit('Chrome に接続できない')
        ws = sh.WS(page['webSocketDebuggerUrl'])
        ws.call('Page.enable')
        ws.call('Emulation.setDeviceMetricsOverride', width=W, height=H, deviceScaleFactor=1, mobile=False)
        ws.call('Page.navigate', url=(BASE / 'index.html').resolve().as_uri())
        ws.wait_event('Page.loadEventFired', 30)
        time.sleep(4)  # 冒頭の演出が終わるまで待つ
        ws.call('Runtime.evaluate', expression=f'document.head.insertAdjacentHTML("beforeend","<style>{HIDE}</style>")')
        time.sleep(0.5)
        png = os.path.join(tmp, 'ogp.png')
        with open(png, 'wb') as fh:
            fh.write(base64.b64decode(ws.call('Page.captureScreenshot', format='png')['data']))
        subprocess.run(['sips', '-s', 'format', 'jpeg', '-s', 'formatOptions', '82', png,
                        '--out', str(BASE / 'images' / 'ogp.jpg')], check=True, capture_output=True)
    finally:
        p.kill()
        shutil.rmtree(prof, ignore_errors=True)
        shutil.rmtree(tmp, ignore_errors=True)
    print('images/ogp.jpg を作った')


if __name__ == '__main__':
    main()
