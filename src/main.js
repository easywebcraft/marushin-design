/* 株式会社丸信 ホームページ：メニューの開け閉め・トップのヘッダーの切り替え・質問への直接リンク・トップの冒頭の演出・お問い合わせフォームの入力チェック */
(function () {
  'use strict';

  // ---- スマホ・タブレットのメニュー ----
  var burger = document.querySelector('.burger');
  var drawer = document.getElementById('drawer');
  if (burger && drawer) {
    var setOpen = function (open) {
      drawer.hidden = !open;
      document.documentElement.classList.toggle('menu-open', open);
      burger.setAttribute('aria-expanded', open ? 'true' : 'false');
      burger.setAttribute('aria-label', open ? 'メニューを閉じる' : 'メニューを開く');
    };
    burger.addEventListener('click', function () {
      setOpen(burger.getAttribute('aria-expanded') !== 'true');
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && burger.getAttribute('aria-expanded') === 'true') {
        setOpen(false);
        burger.focus();
      }
    });
    drawer.addEventListener('click', function (e) {
      if (e.target.closest('a')) setOpen(false);
    });
    // 画面が広くなったら閉じる（メニューが横並びに切り替わるため）
    window.matchMedia('(min-width:1024px)').addEventListener('change', function (e) {
      if (e.matches) setOpen(false);
    });
  }

  // ---- トップ：写真の上に重ねたヘッダーを、少し下へ進んだら白地に戻す ----
  var ovl = document.querySelector('.hd-ovl');
  if (ovl) {
    var draftBar = document.querySelector('.draft');
    var setSolid = function () {
      ovl.classList.toggle('is-solid', (window.scrollY || window.pageYOffset) > (draftBar ? draftBar.offsetHeight : 0) + 24);
    };
    window.addEventListener('scroll', setSolid, { passive: true });
    window.addEventListener('resize', setSolid);
    setSolid();
  }

  // ---- 全ページ：下へ進むと、各部分がふわっと現れる（動きを減らす設定・JS なしでは最初から見える） ----
  if ('IntersectionObserver' in window && !window.matchMedia('(prefers-reduced-motion:reduce)').matches) {
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) {
        if (!e.isIntersecting) return;
        var el = e.target;
        io.unobserve(el);
        el.classList.add('in');
        setTimeout(function () { el.classList.remove('rv', 'in', 'rv-w'); el.style.removeProperty('--d'); }, 1300);
      });
    }, { threshold: 0.12 });
    document.querySelectorAll('.ol-msg-in>*,.ol-pics,.ol-dl,.ol-lic>li,.ol-phil-h,.ol-phil>li,.ol-acc-in,.fw-nav,.fw-l,.fw-steps>li,.fw-faq-in,.cs-head,.cs>li,.pr-cards>li,.pr-incl,.pr-tw,.pr-info,.au-mind-in>*,.au-cm>li,.au-kinds,.au-hand,.au-pol li,.au-note,.au-land>li,.ab-in,.sec .h2c,.cm-head,.cm>li,.wk>li,.works .work,.band-raise .band-in,.fl-head,.pr-in,.vc>li,.t-two>*,.ct-in,.area,.qas .qa,.cta-box,' +
      '.feat,.intro,.pol>li,.two>.panel,.tbl-wrap,.flow>li,.voice,.dl,.telbox,.formcard').forEach(function (el, i, all) {
      var sib = el.parentNode.children, n = Array.prototype.indexOf.call(sib, el);
      if (el.parentNode.matches('.ol-lic,.ol-phil,.fw-steps,.cs,.pr-cards,.au-cm,.au-pol,.au-land,.cm,.wk,.vc,.works,.fl,.pol,.two')) el.style.setProperty('--d', ((n % 5) * 0.09).toFixed(2) + 's');
      el.classList.add('rv');
      io.observe(el);
    });
  }

  // ---- よくある質問：#q3 のようなリンクで来たら、その質問を開く ----
  var openFromHash = function () {
    var id = decodeURIComponent(location.hash.slice(1));
    if (!id) return;
    var el = document.getElementById(id);
    if (el && el.tagName === 'DETAILS') el.open = true;
  };
  window.addEventListener('hashchange', openFromHash);
  openFromHash();

  // ---- 冒頭の演出（トップだけ）：輪が満ちたら、中央の社名がヘッダーの社名の位置へ移る ----
  (function () {
    var r = document.documentElement, L = document.getElementById('ewl');
    if (!L) return;
    if (!r.classList.contains('ewl-on')) { L.remove(); return; }
    try { sessionStorage.setItem('ms-ewl', '1'); } catch (e) {}
    window.__ewl = 1;   // 動き出した合図（head の保険が、途中で幕を外さないように）
    window.scrollTo(0, 0);
    var real = document.querySelector('.hd .logo'), copy = L.querySelector('.logo'), ended = false;
    var end = function () {
      if (ended) return;
      ended = true;
      if (real) real.style.opacity = '1';
      r.classList.add('ewl-go', 'ewl-txt');
      L.classList.add('is-out');
      setTimeout(function () { r.classList.remove('ewl-on', 'ewl-go', 'ewl-txt'); L.remove(); }, 500);
    };
    // タップ・クリック・Esc で飛ばせる
    L.addEventListener('click', end);
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') end(); });
    var absorb = function () {
      if (ended) return;
      if (real && copy) {
        // 中央に拡大して置いた社名を、ヘッダーの社名にぴったり重なる位置・大きさ（1倍）へ動かす
        var a = copy.getBoundingClientRect(), u = real.getBoundingClientRect();
        var dx = u.left - (a.left + a.width / 2 - copy.offsetWidth / 2);
        var dy = u.top - (a.top + a.height / 2 - copy.offsetHeight / 2);
        copy.style.transform = 'translate(' + dx + 'px,' + dy + 'px) scale(1)';
      }
      r.classList.add('ewl-go');          // 幕の下で止めていた写真の動きを、ここから流す
      L.classList.add('is-absorb');
      setTimeout(function () { if (real) real.style.opacity = '1'; }, 950);
      setTimeout(function () { r.classList.add('ewl-txt'); }, 850);   // 幕がほぼ透けたところで文字を出し始める
      setTimeout(end, 1200);
    };
    // 輪は社名が収まる大きさにし、画面の短い辺の8割に収める
    var m = Math.min(innerWidth, innerHeight) * 0.82, k = 1.9;
    if (copy) {
      var w = copy.offsetWidth || 1;
      k = Math.max(0.8, Math.min(2.2, (m - 56) / (w * 1.25)));
      // 大きさを決める瞬間は動かさない
      copy.style.transition = 'none';
      copy.style.setProperty('--ewk', k.toFixed(3));
      void copy.offsetWidth;
      copy.style.transition = '';
      var d = Math.round(Math.min(m, w * k * 1.25 + 56));
      L.style.setProperty('--ewd', d + 'px');
      L.style.setProperty('--ews', (240 / d).toFixed(3));   // 輪の線を画面上で2pxに（輪の図は120の枠で描いている）
    }
    requestAnimationFrame(function () { L.classList.add('is-in'); });
    var fill = L.querySelector('.ewl-ring .f'), pct = L.querySelector('.ewl-pct');
    var C = 2 * Math.PI * 54, D = 1600, t0 = null;
    fill.style.strokeDasharray = C;
    fill.style.strokeDashoffset = C;
    var tick = function (ts) {
      if (ended) return;
      if (t0 === null) t0 = ts;
      var p = Math.min((ts - t0) / D, 1), q = 1 - Math.pow(1 - p, 3);
      pct.textContent = Math.round(q * 100) + '%';
      fill.style.strokeDashoffset = C * (1 - q);
      if (p < 1) { requestAnimationFrame(tick); return; }
      // 輪が満ちたら「きらっ」と光らせ、そのあと輪と数字だけ消し、社名はもう少し見せてからヘッダーへ
      L.classList.add('is-full');
      setTimeout(function () { if (ended) return; L.classList.add('is-p2'); setTimeout(absorb, 900); }, 950);
    };
    requestAnimationFrame(tick);
  })();

  // ---- お問い合わせフォーム ----
  var form = document.getElementById('contact-form');
  if (!form) return;
  var sum = document.getElementById('form-sum');
  var result = document.getElementById('form-result');
  var val = function (name) { return (form.elements[name].value || '').trim(); };
  var isMail = function (s) { return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(s); };

  var rules = [
    ['name', function () { return val('name') ? '' : 'お名前を入力してください。'; }],
    ['email', function () {
      if (!val('email')) return 'メールアドレスを入力してください。';
      return isMail(val('email')) ? '' : 'メールアドレスの形を確認してください（例：name@example.com）。';
    }],
    ['email2', function () {
      if (!val('email2')) return '確認用のメールアドレスを入力してください。';
      return val('email') === val('email2') ? '' : 'メールアドレスが一致していません。もう一度ご確認ください。';
    }],
    ['message', function () { return val('message') ? '' : 'お問合せ内容を入力してください。'; }]
  ];

  var show = function (name, msg) {
    var input = form.elements[name];
    var err = document.getElementById(name + '-err');
    if (msg) {
      input.setAttribute('aria-invalid', 'true');
      err.textContent = msg;
      err.hidden = false;
    } else {
      input.removeAttribute('aria-invalid');
      err.textContent = '';
      err.hidden = true;
    }
  };

  // 一度エラーが出た欄は、直した時点で消す
  rules.forEach(function (r) {
    form.elements[r[0]].addEventListener('input', function () {
      if (this.getAttribute('aria-invalid') === 'true') show(r[0], r[1]());
      if (r[0] === 'email' && form.elements.email2.getAttribute('aria-invalid') === 'true') show('email2', rules[2][1]());
    });
  });

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    result.hidden = true;
    var bad = [];
    rules.forEach(function (r) {
      var msg = r[1]();
      show(r[0], msg);
      if (msg) bad.push(r[0]);
    });
    if (bad.length) {
      sum.textContent = '入力内容をご確認ください（' + bad.length + 'か所）。';
      sum.hidden = false;
      form.elements[bad[0]].focus();
      return;
    }
    sum.hidden = true;
    // 送り先が決まるまでは送らない。「送信しました」とは出さない
    if (!form.dataset.endpoint) {
      result.className = 'form-result';
      result.textContent = '入力内容に問題はありませんでした。ただし、このフォームの送信機能は未接続のため、内容は送信されていません。';
      result.hidden = false;
      result.focus();
      return;
    }
    // 送り先が決まったら、ここに送信の処理を入れる（成功を確かめてから完了の文を出す）
  });
})();

// ---- トップの動き（2026-11-17 松本さん「動きがない、信頼感のあるしっかりとした会社」：案2〜4。案1の施工前後の見比べは外した） ----
(function () {
  var reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  var once = function (els, cls, fn) {
    if (!els.length) return;
    if (reduce || !('IntersectionObserver' in window)) { if (fn) els.forEach(fn); return; }
    els.forEach(function (el) { el.classList.add(cls); });
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) {
        if (!e.isIntersecting) return;
        io.unobserve(e.target);
        e.target.classList.remove(cls);
        if (fn) fn(e.target);
      });
    }, { rootMargin: '0px 0px -12% 0px' });
    els.forEach(function (el) { io.observe(el); });
  };
  var all = function (sel) { return [].slice.call(document.querySelectorAll(sel)); };

  // 2. 施工の流れ：画面に入ったら、段を順番に出す
  once(all('.fl'), 'fl-wait');
  // 3. 線が引かれる
  once(all('.cm-en,.cm,.wk,.ab-in,.pr-in,.ct-in'), 'ln-wait');

  // 4. ただいま受付中：日本時間で、平日（土日・祝日を除く）の 9:00〜17:00 を受付中とする
  var now = document.getElementById('ct-now');
  if (!now) return;
  var hol = {};
  var holidays = function (y) {   // EWC-CRM の jp_holidays.py と同じ決まり（2020年以降）
    if (hol[y]) return hol[y];
    var d = function (m, day) { return Date.UTC(y, m - 1, day); };
    var nthMon = function (m, n) { var t = new Date(d(m, 1)); return d(m, 1 + ((8 - t.getUTCDay()) % 7) + (n - 1) * 7); };
    var eq = function (base) { return Math.floor(base + 0.242194 * (y - 1980) - Math.floor((y - 1980) / 4)); };
    var h = [d(1, 1), nthMon(1, 2), d(2, 11), d(2, 23), d(3, eq(20.8431)), d(4, 29), d(5, 3), d(5, 4), d(5, 5),
      nthMon(7, 3), d(8, 11), nthMon(9, 3), d(9, eq(23.2488)), nthMon(10, 2), d(11, 3), d(11, 23)];
    var set = {}, DAY = 864e5;
    h.forEach(function (t) { set[t] = 1; });
    h.slice().sort().forEach(function (t) {   // 国民の休日：祝日にはさまれた日
      if (!set[t + DAY] && set[t + 2 * DAY] && new Date(t + DAY).getUTCDay() !== 0) set[t + DAY] = 1;
    });
    Object.keys(set).map(Number).sort().forEach(function (t) {   // 振替休日
      if (new Date(t).getUTCDay() !== 0) return;
      var s = t + DAY; while (set[s]) s += DAY; set[s] = 1;
    });
    return (hol[y] = set);
  };
  var biz = function (t) { var w = new Date(t).getUTCDay(); return w > 0 && w < 6 && !holidays(new Date(t).getUTCFullYear())[t]; };
  var WD = '日月火水木金土';
  var label = function (t) { var x = new Date(t); return (x.getUTCMonth() + 1) + '月' + x.getUTCDate() + '日（' + WD[x.getUTCDay()] + '）'; };
  var update = function () {
    var p = {};
    new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Tokyo', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' })
      .formatToParts(new Date()).forEach(function (x) { p[x.type] = +x.value; });
    var today = Date.UTC(p.year, p.month - 1, p.day), min = p.hour * 60 + p.minute, open = biz(today);
    var txt, on = false;
    if (open && min >= 540 && min < 1020) { txt = 'ただいま電話受付中（本日17:00まで）'; on = true; }
    else if (open && min < 540) txt = '本日は9:00から受付します';
    else {
      var n = today + 864e5; while (!biz(n)) n += 864e5;
      txt = (open ? '本日の受付は終了しました。' : '本日はお休みです。') + '次の受付は' + label(n) + ' 9:00からです';
    }
    now.textContent = txt;
    now.classList.toggle('is-open', on);
    now.hidden = false;
  };
  update();
  setInterval(update, 60000);
})();

// ---- トップの奥行き：大きな薄い英字を、下へ進むと本文よりゆっくり動かす（2026-11-17） ----
(function () {
  var secs = [].slice.call(document.querySelectorAll('.has-wm'));
  if (!secs.length || (window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches)) return;
  var ticking = false;
  var update = function () {
    ticking = false;
    var vh = window.innerHeight;
    secs.forEach(function (s) {
      var r = s.getBoundingClientRect();
      if (r.bottom < -200 || r.top > vh + 200) return;
      // 部分の上端が画面の下端にあるとき +40px、画面の上端に来たとき 0 → さらに進むと上へ
      var y = Math.max(-60, Math.min(60, r.top / vh * 40));
      s.style.setProperty('--wmy', y.toFixed(1) + 'px');
    });
  };
  var req = function () { if (!ticking) { ticking = true; requestAnimationFrame(update); } };
  window.addEventListener('scroll', req, { passive: true });
  window.addEventListener('resize', req);
  update();
})();

// ---- 求人の案内：少し下へ動かしたら出す。× で閉じたら、そのページを見ているあいだは出さない（読み込み直すとまた出る。2026-11-17 松本さん） ----
(function () {
  var rq = document.getElementById('rq');
  if (!rq) return;
  var closed = false;
  rq.hidden = false;
  var ft = document.querySelector('.ft');
  var check = function () {
    if (closed) return;
    // フッターの上端が画面の下端から 120px 手前まで来たら消す（フッターの文字に重ねない）
    var nearFt = ft && ft.getBoundingClientRect().top < window.innerHeight + 120;
    rq.classList.toggle('is-on', (window.scrollY || pageYOffset) > 240 && !nearFt);
  };
  rq.querySelector('.rq-x').addEventListener('click', function () {
    closed = true;
    rq.classList.remove('is-on');
    setTimeout(function () { rq.hidden = true; }, 500);
  });
  window.addEventListener('scroll', check, { passive: true });
  window.addEventListener('resize', check);
  check();
})();
