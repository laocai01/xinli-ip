/* 卡片动画引擎（2026-11-04 重写：支持每张卡不同入场动效）
   董事长要求：每张卡片的动态画面都必须不相同。

   支持的 data-anim 类型（由 gen_cards.make_anim() 逐张分配）：
     up      — 上浮淡入（位移 90px）
     in      — 轻微上浮淡入（位移 16px）
     left    — 从左侧滑入
     right   — 从右侧滑入
     scale   — 中心放大弹入
     blur    — 模糊聚焦（clear）
     rot     — 轻微旋转落下
     wipe    — 从左向右擦出（clip-path）
     rise    — 由下至上的长距离升起（比 up 更慢更沉）
     grow    — 中线向两侧展开
     grow2   — 自身从 0 展开
     pop     — 焦点色块弹入

   额外支持 data-stagger，让子元素整体依次错开。
   用法：注入 HTML 后调用 window.__setT(t) 再截图 */
(function () {
  var els = [].slice.call(document.querySelectorAll('[data-anim]'));

  function n(el, k, dft) {
    var v = el.dataset[k];
    return v === undefined || v === '' ? dft : parseFloat(v);
  }

  function easeOutQuad(p) { return 1 - (1 - p) * (1 - p); }
  function easeOutCubic(p) { return 1 - Math.pow(1 - p, 3); }
  function easeOutBack(p) { var c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(p - 1, 3) + c1 * Math.pow(p - 1, 2); }
  function easeOutExpo(p) { return p >= 1 ? 1 : 1 - Math.pow(2, -10 * p); }

  els.forEach(function (el) {
    var kind = el.dataset.anim;
    if (kind === 'grow' && !el.dataset._w) el.dataset._w = '420';
    if (kind === 'grow2' && !el.dataset._w) el.dataset._w = '120';
  });

  window.__setT = function (t) {
    els.forEach(function (el) {
      var kind = el.dataset.anim,
          d = n(el, 'delay', 0),
          du = n(el, 'dur', 0.8),
          p = Math.max(0, Math.min(1, (t - d) / du));

      /* ---- 线条类 ---- */
      if (kind === 'grow') {
        var w = parseFloat(el.dataset._w) * easeOutQuad(p);
        el.style.width = w + 'px';
        el.style.marginLeft = (-w / 2) + 'px';
        el.style.opacity = p > 0 ? 1 : 0;
        return;
      }
      if (kind === 'grow2') {
        el.style.width = (parseFloat(el.dataset._w) * easeOutQuad(p)) + 'px';
        el.style.opacity = p > 0 ? 1 : 0;
        return;
      }

      /* ---- 块状类 ---- */
      if (kind === 'pop') {
        el.style.opacity = p > 0 ? 1 : 0;
        el.style.transform = 'scale(' + (0.3 + 0.7 * easeOutBack(p)) + ')';
        return;
      }

      /* ---- 文字类：每类动效不同 ---- */
      el.style.opacity = p > 0 ? 1 : 0;

      if (kind === 'up') {
        el.style.transform = 'translateY(' + ((1 - easeOutQuad(p)) * 90) + 'px)';
        return;
      }
      if (kind === 'in') {
        el.style.transform = 'translateY(' + ((1 - easeOutQuad(p)) * 16) + 'px)';
        return;
      }
      if (kind === 'rise') {
        el.style.transform = 'translateY(' + ((1 - easeOutExpo(p)) * 170) + 'px)';
        return;
      }
      if (kind === 'left') {
        el.style.transform = 'translateX(' + ((1 - easeOutCubic(p)) * -150) + 'px)';
        return;
      }
      if (kind === 'right') {
        el.style.transform = 'translateX(' + ((1 - easeOutCubic(p)) * 150) + 'px)';
        return;
      }
      if (kind === 'scale') {
        var s = 0.72 + 0.28 * easeOutBack(p);
        el.style.transform = 'scale(' + s + ')';
        return;
      }
      if (kind === 'blur') {
        var bp = easeOutCubic(p);
        el.style.filter = 'blur(' + ((1 - bp) * 14).toFixed(2) + 'px)';
        el.style.transform = 'scale(' + (1.06 - 0.06 * bp) + ')';
        return;
      }
      if (kind === 'rot') {
        var rp = easeOutCubic(p);
        el.style.transform = 'rotate(' + ((1 - rp) * -3.5).toFixed(2) + 'deg) translateY(' + ((1 - rp) * 60) + 'px)';
        return;
      }
      if (kind === 'wipe') {
        var wp = easeOutCubic(p);
        el.style.clipPath = 'inset(0 ' + ((1 - wp) * 100).toFixed(1) + '% 0 0)';
        el.style.transform = 'translateY(' + ((1 - wp) * 10) + 'px)';
        return;
      }

      /* 兜底 */
      el.style.transform = 'translateY(' + ((1 - easeOutQuad(p)) * 40) + 'px)';
    });
  };

  window.__setT(0);
})();
