import base64, os, subprocess, json, re

BASE = r"E:/心理咨询IP/07-形象设计"
CHROME = r"C:/Program Files/Google/Chrome/Application/chrome.exe"
import sys
_name = sys.argv[1] if len(sys.argv) > 1 else "封面_第02条"
inner = os.path.join(BASE, "_render_" + _name + ".html")
assert os.path.exists(inner), f"先跑 render_cover.py {_name}"

PROBE_JS = """
window.addEventListener('load', function () {
  function r(s){ var e=document.querySelector(s); if(!e) return null;
    var b=e.getBoundingClientRect();
    return {sel:s, top:Math.round(b.top), bottom:Math.round(b.bottom), h:Math.round(b.height)}; }
  var out = [r('.brand'), r('.rule'), r('.kicker'), r('.big'),
             r('.dotline'), r('.punch'), r('.bottom'), r('.hint'), r('.sign')].filter(Boolean);
  var overlaps = [];
  for (var i=0;i<out.length;i++){
    for (var j=i+1;j<out.length;j++){
      var a=out[i], b=out[j];
      // 跳过父子包含关系（那不算视觉重叠）
      var contains = (b.sel.indexOf(a.sel)===0) || (a.sel.indexOf(b.sel)===0);
      var parentChild = (a.sel==='.bottom' && (b.sel==='.hint'||b.sel==='.sign')) ||
                        (b.sel==='.bottom' && (a.sel==='.hint'||a.sel==='.sign'));
      if (parentChild) continue;
      if (a.top < b.bottom && b.top < a.bottom) overlaps.push(a.sel+' x '+b.sel);
    }
  }
  var bad = out.filter(function(d){ return d.top < 44 || d.bottom > 1620; })
               .map(function(d){ return d.sel+'(t'+d.top+'/b'+d.bottom+')'; });
  document.title = 'MEASURE:' + JSON.stringify({boxes:out, overlaps:overlaps, outofzone:bad});
});
"""

html = open(inner, encoding="utf-8").read()
html = html.replace("</body>", "<script>" + PROBE_JS + "</script></body>")
probe = os.path.join(BASE, "_probe.html")
open(probe, "w", encoding="utf-8").write(html)

r = subprocess.run([CHROME, "--headless=new", "--disable-gpu",
                    "--virtual-time-budget=3000", "--dump-dom",
                    "file:///" + probe.replace("\\", "/")],
                   capture_output=True, text=True, errors="ignore", encoding="utf-8")
m = re.search(r"<title>MEASURE:(.*?)</title>", r.stdout, re.S)
if not m:
    print("未取到测量值"); print(r.stdout[:600]); raise SystemExit(1)

data = json.loads(m.group(1).replace("&quot;", '"'))
print(f"{'元素':<12}{'top':>8}{'bottom':>9}{'高':>7}")
for d in data["boxes"]:
    flag = ""
    if d["top"] < 44: flag = "  X 压边框"
    if d["bottom"] > 1620: flag = "  X 侵入安全区"
    print(f"{d['sel']:<12}{d['top']:>8}{d['bottom']:>9}{d['h']:>7}{flag}")
print()
print("重叠:", data["overlaps"] if data["overlaps"] else "无 OK")
print("越界:", data["outofzone"] if data["outofzone"] else "无 OK")
os.remove(probe)
