/* 株式会社丸信 ホームページ：メニューの開け閉め・質問への直接リンク・トップの冒頭の演出・お問い合わせフォームの入力チェック */
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
      L.style.setProperty('--ewd', Math.round(Math.min(m, w * k * 1.25 + 56)) + 'px');
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
      // 輪が満ちたら輪と数字だけ消し、社名はもう少し見せてからヘッダーへ
      setTimeout(function () { if (ended) return; L.classList.add('is-p2'); setTimeout(absorb, 900); }, 250);
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
