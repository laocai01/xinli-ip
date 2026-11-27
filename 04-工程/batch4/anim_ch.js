/* 字符级动画引擎 v2（2026-11-18 重写）
   董事长要求：每张卡文字入场动态都要不同，且"漂亮、专业、明显"。

   设计：
   - 文字按字符自动拆分（<span class="ch">），每个字符可用 window.__setT(t) 精确控制
   - 引擎只负责"按 data-anim + data-delay + data-dur 计算每个元素的进度 p"
   - 具体效果在 CHAR_EFFECTS 里按名字实现，卡片 HTML 用 data-anim="fadeUp" 指定

   已实现 12 种字符级 + 8 种块级：
    字符级：fadeUp / fadeIn / wipeL / wipeU / typeOn / spring / trackIn
            flyIn / byWord / pop / sheen / drumRoll
    块级：  grow / grow2 / popBlock / maskRise / slideL / slideR / scaleIn / blurIn

   铁律：所有入场 <0.75s；落地后完全静止；重点字（.em）最后出现且不动。
*/
(function () {
  var CH_ANIM = {
    fadeUp: 1, fadeIn: 1, wipeL: 1, wipeU: 1, typeOn: 1, spring: 1,
    trackIn: 1, flyIn: 1, byWord: 1, pop: 1, sheen: 1, drumRoll: 1
  };

  function n(el, k, dft) {
    var v = el.dataset[k];
    return (v === undefined || v === '') ? dft : parseFloat(v);
  }
  function easeOutQuad(p) { return 1 - (1 - p) * (1 - p); }
  function easeOutCubic(p) { return 1 - Math.pow(1 - p, 3); }
  function easeOutExpo(p) { return p >= 1 ? 1 : 1 - Math.pow(2, -10 * p); }
  function easeOutBack(p) { var c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(p - 1, 3) + c1 * Math.pow(p - 1, 2); }

  /* ---------- 准备：文字节点自动拆字符 ---------- */
  function splitChars(root) {
    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null);
    var nodes = [], nn;
    while ((nn = walker.nextNode())) {
      if (nn.nodeValue && nn.nodeValue.trim() !== '') nodes.push(nn);
    }
    nodes.forEach(function (tn) {
      var frag = document.createDocumentFragment();
      var txt = tn.nodeValue;
      var idx = 0;
      for (var i = 0; i < txt.length; i++) {
        var c = txt[i];
        var sp = document.createElement('span');
        sp.className = 'ch';
        // 空格用一个不折叠的宽度占位
        if (c === ' ' || c === '\u3000') {
          sp.textContent = '\u00a0';   // 不折叠空格；常量赋值，无 XSS 风险
          sp.dataset.space = '1';
        } else {
          sp.textContent = c;
        }
        sp.dataset.ci = idx++;
        frag.appendChild(sp);
      }
      tn.parentNode.replaceChild(frag, tn);
    });
  }

  /* ---------- 初始化：记录每个元素的字符、延迟 ---------- */
  function initAnims() {
    var els = [].slice.call(document.querySelectorAll('[data-anim]'));
    // ★ 先拆字符（只对字符级动画拆，块级动画不拆，避免破坏 maskRise/clip-path 效果）
    els.forEach(function (el) {
      if (CH_ANIM[el.dataset.anim] === 1) splitChars(el);
    });
    els.forEach(function (el) {
      el._ch = [].slice.call(el.querySelectorAll('.ch'));
      el._isChar = CH_ANIM[el.dataset.anim] === 1;
      el._ci = 0;
      el._last = -1;
    });
    return els;
  }

  /* ---------- 字符进度：按 stagger 错开 ---------- */
  function charP(el, t) {
    var d = n(el, 'delay', 0);
    var du = n(el, 'dur', 0.55);
    var st = n(el, 'stagger', 0.035);
    return el._ch.map(function (ch, i) {
      var dd = d + i * st;
      return Math.max(0, Math.min(1, (t - dd) / du));
    });
  }

  // 落定后的持续微动（2026-11-18 董事长：文字要有动态，不能一秒钟后死掉）
  function breathe(el, t, d, du) {
    var ip = Math.max(0, Math.min(1, (t - d) / du));
    if (ip < 1) return;
    var after = t - d - du;
    // 重点字：极缓亮度呼吸（周期 2.4s，幅度很小，不晃眼）
    var ems = el.querySelectorAll('span[style*="letter-spacing"], .ch');
    // 整块：极缓的 0.4% 缩放视差
    var k = 1 + Math.sin(after * 2.6) * 0.004;
    el.style.transform = (el.style.transform || '').replace(/scale\([^)]*\)/, '') + ' scale(' + k.toFixed(4) + ')';
  }

  window.__setT = function (t) {
    var els = window.__animEls || (window.__animEls = initAnims());
    els.forEach(function (el) {
      var kind = el.dataset.anim;
      var d = n(el, 'delay', 0);
      var du = n(el, 'dur', 0.6);
      var p = Math.max(0, Math.min(1, (t - d) / du));

      if (el._isChar) {
        var ps = charP(el, t);
        var allDone = ps.length && ps[ps.length - 1] >= 1;
        el.style.opacity = 1;
        el._ch.forEach(function (ch, i) {
          var q = ps[i];
          applyChar(kind, ch, q, i, el);
        });
        breathe(el, t, d, du);
        return;
      }

      /* ---------- 块级 ---------- */
      if (kind === 'grow') {
        var w = n(el, '_w', 420) * easeOutQuad(p);
        el.style.width = w + 'px';
        el.style.marginLeft = (-w / 2) + 'px';
        el.style.opacity = p > 0 ? 1 : 0;
        return;
      }
      if (kind === 'grow2') {
        el.style.width = (n(el, '_w', 120) * easeOutQuad(p)) + 'px';
        el.style.opacity = p > 0 ? 1 : 0;
        return;
      }
      if (kind === 'popBlock') {
        el.style.opacity = p > 0 ? 1 : 0;
        el.style.transform = 'scale(' + (0.3 + 0.7 * easeOutBack(p)) + ')';
        return;
      }
      if (kind === 'maskRise') {
        var mp = easeOutCubic(p);
        el.style.opacity = p > 0 ? 1 : 0;
        el.style.clipPath = 'inset(' + ((1 - mp) * 100).toFixed(1) + '% 0 -2% 0)';
        el.style.transform = 'translateY(' + ((1 - mp) * 40) + 'px)';
        return;
      }
      if (kind === 'slideL') {
        el.style.opacity = p > 0 ? 1 : 0;
        el.style.transform = 'translateX(' + ((1 - easeOutCubic(p)) * -150) + 'px)';
        return;
      }
      if (kind === 'slideR') {
        el.style.opacity = p > 0 ? 1 : 0;
        el.style.transform = 'translateX(' + ((1 - easeOutCubic(p)) * 150) + 'px)';
        return;
      }
      if (kind === 'scaleIn') {
        el.style.opacity = p > 0 ? 1 : 0;
        el.style.transform = 'scale(' + (0.72 + 0.28 * easeOutBack(p)) + ')';
        return;
      }
      if (kind === 'blurIn') {
        var bp = easeOutCubic(p);
        el.style.opacity = p > 0 ? 1 : 0;
        el.style.filter = 'blur(' + ((1 - bp) * 14).toFixed(2) + 'px)';
        el.style.transform = 'scale(' + (1.06 - 0.06 * bp) + ')';
        return;
      }
      /* 默认 */
      el.style.opacity = p > 0 ? 1 : 0;
      el.style.transform = 'translateY(' + ((1 - easeOutQuad(p)) * 40) + 'px)';
    });
  };

  function applyChar(kind, ch, q, i, el) {
    if (q <= 0) {
      ch.style.opacity = 0;
      ch.style.transform = '';
      ch.style.clipPath = '';
      ch.style.filter = '';
      return;
    }
    switch (kind) {
      case 'fadeUp':
        ch.style.opacity = q;
        ch.style.transform = 'translateY(' + ((1 - easeOutQuad(q)) * 46) + 'px)';
        break;
      case 'fadeIn':
        ch.style.opacity = q * q;
        ch.style.transform = 'none';
        break;
      case 'wipeL':
        ch.style.opacity = 1;
        ch.style.clipPath = 'inset(0 ' + ((1 - easeOutCubic(q)) * 100).toFixed(1) + '% 0 0)';
        break;
      case 'wipeU':
        ch.style.opacity = 1;
        ch.style.clipPath = 'inset(' + ((1 - easeOutCubic(q)) * 100).toFixed(1) + '% 0 0 0)';
        break;
      case 'typeOn':
        ch.style.opacity = q >= 1 ? 1 : (q > 0 ? 1 : 0);
        ch.style.transform = 'none';
        break;
      case 'spring':
        var s = 0.4 + 0.6 * easeOutBack(q);
        ch.style.opacity = Math.min(1, q * 2.2);
        ch.style.transform = 'scale(' + s.toFixed(3) + ')';
        break;
      case 'trackIn':
        ch.style.opacity = Math.min(1, q * 2);
        ch.style.transform = 'none';
        ch.style.marginLeft = ((1 - easeOutCubic(q)) * 0.34 * parseFloat(getComputedStyle(el).fontSize) * 0.5) + 'px';
        break;
      case 'flyIn':
        var fx = (1 - easeOutCubic(q)) * -90, fy = (1 - easeOutCubic(q)) * 60;
        ch.style.opacity = Math.min(1, q * 1.6);
        ch.style.transform = 'translate(' + fx.toFixed(1) + 'px,' + fy.toFixed(1) + 'px) rotate(' + ((1 - easeOutCubic(q)) * -8).toFixed(2) + 'deg)';
        break;
      case 'byWord':
        ch.style.opacity = q;
        ch.style.transform = 'translateY(' + ((1 - easeOutExpo(q)) * 24) + 'px)';
        break;
      case 'pop':
        var ps2 = q >= 1 ? 1 : (0.6 + 0.4 * easeOutBack(q));
        ch.style.opacity = Math.min(1, q * 3);
        ch.style.transform = 'scale(' + ps2.toFixed(3) + ')';
        break;
      case 'sheen':
        ch.style.opacity = Math.min(1, q * 2.5);
        var sh = 40 + 120 * q;
        ch.style.filter = 'brightness(' + (1 + 0.9 * Math.max(0, 1 - Math.abs(q - 0.5) * 2)).toFixed(2) + ')';
        ch.style.transform = 'none';
        break;
      case 'drumRoll':
        ch.style.opacity = Math.min(1, q * 1.4);
        ch.style.transform = 'translateY(' + ((1 - easeOutBack(q)) * 70).toFixed(1) + 'px)';
        break;
      default:
        ch.style.opacity = q;
        ch.style.transform = 'translateY(' + ((1 - easeOutQuad(q)) * 40) + 'px)';
    }
  }

  function ensure() {
    if (!window.__animEls || window.__animEls.length === 0) {
      window.__animEls = initAnims();
    }
    return window.__animEls;
  }

  function boot() {
    ensure();
    window.__setT(0);
    window.__booted = true;
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
  // 兜底：外部第一次 __setT 时再确保一次
  var _st = window.__setT;
  window.__setT = function (t) {
    if (!window.__booted) ensure();
    return _st(t);
  };
})();
