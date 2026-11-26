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
    var show = function (obs, wait) {
      return function (es) {
        es.forEach(function (e) {
          if (!e.isIntersecting) return;
          var el = e.target;
          obs().unobserve(el);
          el.classList.add('in');
          setTimeout(function () { el.classList.remove('rv', 'in', 'rv-w'); el.style.removeProperty('--d'); }, wait);
        });
      };
    };
    // 動き出す位置は、トップの線・施工の流れと同じ「画面の下から 12% 入ったところ」にそろえる（2026-11-21 動きの統一）
    var io = new IntersectionObserver(show(function () { return io; }, 1500), { rootMargin: '0px 0px -12% 0px' });
    // 施工事例の1件は、写真の下（施工後が重なるところ）まで画面に入ってから動かす（2026-11-20 松本さん「スクロールする前に動きが終わる」）。
    // 施工後・札の動きが終わるまで .rv/.in を外さない
    var ioWk = new IntersectionObserver(show(function () { return ioWk; }, 2200), { rootMargin: '0px 0px -12% 0px' }   /* 2026-11-21 松本さん「統一感を」：ほかの段と同じ動き出す位置に */);
    document.querySelectorAll('.ol-msg-in>*,.ol-pics,.ol-dl,.ol-lic>li,.ol-phil-h,.ol-phil>li,.ol-acc-in,.fw-nav,.fw-l,.fw-steps>li,.fw-faq-in,.cs-head,.cs>li,.pr-cards>li,.pr-incl,.pr-tw,.pr-info,.au-mind-in>*,.au-cm>li,.au-kinds,.au-hand,.au-pol li,.au-note,.au-land>li,.ab-in,.sec .h2c,.cm-head,.cm>li,.wk>li,.works .work,.band-raise .band-in,.fl-head,.pr-in,.vc>li,.t-two>*,.ct-in,.area,.qas .qa,.cta-box,' +
      '.feat,.intro,.pol>li,.two>.panel,.tbl-wrap,.flow>li,.voice,.dl,.telbox,.formcard').forEach(function (el, i, all) {
      var sib = el.parentNode.children, n = Array.prototype.indexOf.call(sib, el);
      if (el.parentNode.matches('.ol-lic,.ol-phil,.fw-steps,.cs,.pr-cards,.au-cm,.au-pol,.au-land,.cm,.wk,.vc,.works,.fl,.pol,.two')) el.style.setProperty('--d', ((n % 5) * 0.12).toFixed(2) + 's');   // 並びの間隔はサイト全体で 0.12秒（2026-11-21 動きの統一）
      el.classList.add('rv');
      (el.matches('.wk>li') ? ioWk : io).observe(el);
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
      // 2026-11-21 松本さん「左上にいく動きを削除」：社名は中央のまま、幕と一緒に消す
      r.classList.add('ewl-go');          // 幕の下で止めていた写真の動きを、ここから流す
      L.classList.add('is-absorb');
      // 2026-11-21 松本さん「冒頭演出とFVの切り替わりに違和感」：写真だけで文字がない間ができていたので、
      // 幕が透け始めたらすぐ文字とヘッダーの社名を出す（850→300ms・950→350ms）。幕を外すのも早める（1200→1000ms）
      setTimeout(function () { if (real) real.style.opacity = '1'; }, 350);
      setTimeout(function () { r.classList.add('ewl-txt'); }, 300);
      setTimeout(end, 1000);
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
    var C = 2 * Math.PI * 54, D = 1100, t0 = null;   // 輪が満ちるまで（2026-11-18 松本さん「もう少し短く」で 1.6秒→1.1秒）
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
      // 2026-11-21「切り替わりに違和感」：満ちてから写真が出るまで社名だけの白い画面が長かったので詰める（950+500 → 700+250ms）
      setTimeout(function () { if (ended) return; L.classList.add('is-p2'); setTimeout(absorb, 250); }, 700);   // 2026-11-20「きらっをもっと強調」で 700→950（光が見える間をのばす）
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

  // （4. 「ただいま電話受付中」の表示は 2026-11-20 松本さんの指示で外した。年末年始などの長い休みにも出てしまうため）
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

// ---- 求人の案内とブログの札：下へ進むと左端に札を出し、押すとバナーを開く（PC は触れても開く）。札をもう一度押す・Esc・外を押すと閉じる（×は 2026-11-18 松本さんの希望で外した）。
// ブログの札（準備中）は 2026-11-19 に足した。開くのは押した札の分だけ ----
(function () {
  var box = document.getElementById('rqs');
  if (!box) return;
  var shown = null;
  var all = Array.prototype.slice.call(box.querySelectorAll('.rq'));
  var set = function (rq, open) {
    rq.classList.toggle('is-open', open);
    var tab = rq.querySelector('.rq-tab');
    tab.setAttribute('aria-expanded', open ? 'true' : 'false');
    if (!open && document.activeElement === tab) tab.blur();   // iPhone で押した状態が残らないように（2026-11-20）
  };
  // 2026-11-20 お客様に見比べてもらう用：<html data-banner="open"> のときは、札が出ている間は求人のバナーを開いたままにする
  // （ブログの札を押している間だけブログを出す）。data-banner は確認用だけにある「色を選ぶ」の部品が付け外しする（?banner=open でも付く）
  var always = function () { return document.documentElement.getAttribute('data-banner') === 'open'; };
  var main = document.getElementById('rq');
  var closeAll = function (except) {
    all.forEach(function (rq) { if (rq !== except) set(rq, false); });
    if (always() && shown && !except && main) set(main, true);
  };
  window.msBannerMode = function () { closeAll(); };
  all.forEach(function (rq) {
    rq.querySelector('.rq-tab').addEventListener('click', function () {
      var open = !rq.classList.contains('is-open');
      closeAll(rq);
      set(rq, open);
      if (!open) closeAll();
    });
  });
  document.addEventListener('click', function (ev) { if (!box.contains(ev.target)) closeAll(); });
  document.addEventListener('keydown', function (ev) { if (ev.key === 'Escape') closeAll(); });
  // 最初の画面では隠し、画面の高さの半分ほど下へ進んだら出す。上へ戻ると隠す（2026-11-18 松本さん）
  var check = function () {
    var on = (window.scrollY || window.pageYOffset) > window.innerHeight * 0.5;
    if (on === shown) return;
    shown = on;
    box.classList.toggle('is-wait', !on);
    if (!on) { all.forEach(function (rq) { set(rq, false); }); } else closeAll();
  };
  window.addEventListener('scroll', check, { passive: true });
  window.addEventListener('resize', check);
  check();
})();

// ---- 施工事例のページ：つまみを左右に動かして、施工前と施工後を見比べる（2026-11-21 松本さん「施工事例を見比べやすくする」）。
// 写真のどこを押しても、その位置へ境目が動く。縦に指を動かしたときはページがふつうに進む（CSS の touch-action:pan-y）。
// 画面に出てきたとき、一度だけ境目を少し左右に動かして「動かせる」ことを知らせる（動きを減らす設定では動かさない） ----
(function () {
  var boxes = document.querySelectorAll('.wk-ph');   // つまみ（.wk-rng）があるのは施工事例のページだけ
  if (!boxes.length) return;
  var still = window.matchMedia('(prefers-reduced-motion:reduce)');
  Array.prototype.forEach.call(boxes, function (box) {
    var rng = box.querySelector('.wk-rng');
    if (!rng) return;
    var set = function (v) {
      v = Math.max(0, Math.min(100, v));
      box.style.setProperty('--pos', v + '%');
      rng.value = Math.round(v);
    };
    var at = function (e) {
      var r = box.getBoundingClientRect();
      set((e.clientX - r.left) / r.width * 100);
    };
    var dragging = false;
    box.addEventListener('pointerdown', function (e) {
      if (e.pointerType === 'mouse' && e.button !== 0) return;
      dragging = true;
      box.hint = false;
      at(e);
      if (box.setPointerCapture) box.setPointerCapture(e.pointerId);
    });
    box.addEventListener('pointermove', function (e) { if (dragging) at(e); });
    ['pointerup', 'pointercancel', 'lostpointercapture'].forEach(function (t) {
      box.addEventListener(t, function () { dragging = false; });
    });
    rng.addEventListener('input', function () { box.hint = false; set(+rng.value); });
  });

  if (!('IntersectionObserver' in window)) return;
  var hint = function (box) {
    if (still.matches) return;
    // 50% → 30% → 70% → 50%（約1.6秒）。途中で触られたらやめる
    var keys = [[0, 50], [450, 30], [1150, 70], [1600, 50]], t0 = null;
    box.hint = true;
    var step = function (t) {
      if (!box.hint) return;
      if (t0 === null) t0 = t;
      var e = t - t0, i = 1;
      while (i < keys.length - 1 && e > keys[i][0]) i++;
      var a = keys[i - 1], b = keys[i], k = Math.min(1, (e - a[0]) / (b[0] - a[0]));
      k = k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
      box.style.setProperty('--pos', (a[1] + (b[1] - a[1]) * k) + '%');
      if (e < keys[keys.length - 1][0]) requestAnimationFrame(step); else box.hint = false;
    };
    requestAnimationFrame(step);
  };
  var io = new IntersectionObserver(function (es) {
    es.forEach(function (e) {
      if (!e.isIntersecting) return;
      io.unobserve(e.target);
      setTimeout(function () { hint(e.target); }, 500 + (parseFloat(e.target.closest('li').style.getPropertyValue('--d')) || 0) * 1000);
    });
  }, { rootMargin: '0px 0px -25% 0px' });
  Array.prototype.forEach.call(boxes, function (box) { if (box.querySelector('.wk-rng')) io.observe(box); });
})();

/* 採用情報の求人の札：マウスのある画面では、カーソルを合わせると詳しい条件が札の上に開く（2026-11-27 松本さん）。
   スマホは「詳しい条件を見る」を押して開く（details のまま） */
(function () {
  if (!window.matchMedia || !matchMedia('(hover: hover) and (pointer: fine)').matches) return;
  document.documentElement.classList.add('rc-hover');
  // 開け閉めは CSS の動き（:hover）に任せる。中身はいつも開いておき、見え方だけを滑らかに切り替える（2026-11-27「もっと滑らかに」）
  Array.prototype.forEach.call(document.querySelectorAll('.rc-job'), function (job) {
    var d = job.querySelector('.rc-more');
    if (!d) return;
    d.open = true;
    job.tabIndex = 0;   // キーボードでも札に合わせると開く
  });
})();
