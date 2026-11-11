/* 株式会社丸信 ホームページ：メニューの開け閉め・お問い合わせフォームの入力チェック・質問への直接リンク */
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
