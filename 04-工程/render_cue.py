"""★ 口播对齐渲染器（2026-10-08 董事长定：卡片文字跟着口播显现）
用法: python render_cue.py <卡名...>

原理：把每张卡的分层文字（大字/重点色块/辅助句）的出字时刻，
      按"董事长说到那句话的秒数"来定，而不是固定的 0.15/0.80/1.60/2.70。
"""
import io, os, re, sys, json, time, socket, shutil, subprocess, base64, urllib.request, asyncio

BASE = r"E:/心理咨询IP/07-形象设计/卡片v2"
CHROME = r"C:/Program Files/Google/Chrome/Application/chrome.exe"
CUE = r"E:/心理咨询IP/04-工程/cue/cards_cue.json"     # 时刻表
LU = "data:image/png;base64," + base64.b64encode(
    open(r"E:/心理咨询IP/07-形象设计/交付_v5/圆形标/老蔡说_圆形标_400.png", "rb").read()).decode()

TMP = r"E:/tmp/anim_cue"

# 注入 ID（与 render_all.py 一致）
IDS_CARD = [('<div class="brand">', '<div class="brand" id="e_brand">'),
            ('<div class="rule"></div>', '<div class="rule" id="e_rule"></div>'),
            ('<div class="big">', '<div class="big" id="e_big">'),
            ('<em>', '<em id="e_em">'),
            ('<div class="punch">', '<div class="punch" id="e_punch">'),
            ('<div class="sign">', '<div class="sign" id="e_sign">'),
            ('<div class="corekey">', '<div class="corekey" id="e_corekey">'),
            ('<div class="numline">', '<div class="numline" id="e_numline">'),
            ('<div class="label">', '<div class="label" id="e_label">')]


def make_js(cue):
    """按时刻表生成 __setT（时刻单位=秒，相对卡片出现）"""
    def c(k, d=0.0):
        return f"{cue.get(k, d):.2f}"
    return """<script>
window.__setT=function(t){
 function cl(x){return x<0?0:x>1?1:x;}
 function out(p){return 1-Math.pow(1-p,2);}
 function back(p){var c=1.6;return 1+(c+1)*Math.pow(p-1,3)+c*Math.pow(p-1,2);}
 var E=function(i){return document.getElementById(i);};
 var BRAND=%s, BIG=%s, EM=%s, PUNCH=%s, CORE=%s, RULE=%s, LABEL=%s;
 // 品牌条
 var p1=out(cl((t-BRAND)/0.45)),b=E('e_brand');
 if(b){b.style.opacity=p1;b.style.transform='translateY('+(-45*(1-p1)).toFixed(1)+'px)';}
 // 分割线
 var p2=out(cl((t-RULE)/0.40)),r=E('e_rule');
 if(r){r.style.transform='scaleX('+p2.toFixed(3)+')';r.style.transformOrigin='center';}
 // 主标题（跟口播第一句）
 var p3=out(cl((t-BIG)/0.55)),g=E('e_big');
 if(g){g.style.opacity=p3;g.style.transform='translateY('+(200*(1-p3)).toFixed(1)+'px)';}
 // 辅助句
 var p4=out(cl((t-PUNCH)/0.55)),pu=E('e_punch');
 if(pu){pu.style.opacity=p4;pu.style.transform='translateY('+(90*(1-p4)).toFixed(1)+'px)';}
 // ★ 重点色块（跟口播说到重点那句）
 var p5=back(cl((t-EM)/0.55)),e=E('e_em');
 if(e){e.style.opacity=cl((t-EM)/0.30);e.style.transform='scale('+(0.3+0.7*p5).toFixed(3)+')';}
 // B线左栏
 var cw=E('e_corekey');
 if(cw){cw.style.opacity=out(cl((t-CORE)/0.60));cw.style.transform='translateY('+(-120*(1-out(cl((t-CORE)/0.60)))).toFixed(1)+'px)';}
 var nl=E('e_numline');
 if(nl){nl.style.transform='scaleY('+out(cl((t-CORE+0.20)/0.50)).toFixed(3)+')';nl.style.transformOrigin='top';}
 var lb=E('e_label');
 if(lb){lb.style.opacity=out(cl((t-LABEL)/0.45));lb.style.transform='translateY('+(40*(1-out(cl((t-LABEL)/0.45)))).toFixed(1)+'px)';}
};
</script>""" % (c("brand", 0.05), c("big", 0.20), c("em", 1.60), c("punch", 1.00),
                c("corekey", 0.10), c("rule", 0.30), c("label", 0.60))


def prep(name, cue):
    p = os.path.join(BASE, name + ".html")
    s = io.open(p, encoding="utf-8").read().replace("__LOGO__", LU)
    for a, b in IDS_CARD:
        s = s.replace(a, b, 1)
    s = re.sub(r'<script>.*?</script>', '', s, flags=re.S)
    s = s.replace("</body>", make_js(cue) + "</body>")
    o = os.path.join(BASE, "_cue_" + name + ".html")
    io.open(o, "w", encoding="utf-8").write(s)
    return o


async def shoot(name, dur, cue):
    import websockets
    hp = prep(name, cue)
    url = "file:///" + hp.replace("\\", "/")
    frames = int(round(dur * 30))
    td = os.path.join(TMP, name)
    os.makedirs(td, exist_ok=True)
    have = lambda: len([f for f in os.listdir(td) if f.endswith(".png")])
    if have() >= frames:
        return True
    # ★ 断线重试：每张卡最多 8 轮，断点续渲
    for attempt in range(8):
        if have() >= frames:
            break
        sk = socket.socket(); sk.bind(("127.0.0.1", 0)); port = sk.getsockname()[1]; sk.close()
        udd = f"E:/tmp/cueprof_{port}"
        proc = subprocess.Popen([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
            "--no-first-run", "--no-default-browser-check", "--disable-extensions",
            "--disable-dev-shm-usage", "--user-data-dir=" + udd,
            "--remote-debugging-port=" + str(port), "--force-device-scale-factor=1",
            "--window-size=1080,1920", "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        wsu = None
        for _ in range(80):
            try:
                d = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json", timeout=3))
                for it in d:
                    if it.get("type") == "page":
                        wsu = it["webSocketDebuggerUrl"]; break
                if wsu: break
            except Exception: pass
            time.sleep(0.25)
        if not wsu:
            proc.kill(); shutil.rmtree(udd, ignore_errors=True); continue
        try:
            ok = await _shoot_once(wsu, url, td, frames)
            if ok:
                proc.kill(); shutil.rmtree(udd, ignore_errors=True)
                return True
        except Exception as e:
            pass
        finally:
            try: proc.kill()
            except Exception: pass
            shutil.rmtree(udd, ignore_errors=True)
    return have() >= frames


async def _shoot_once(wsu, url, td, frames):
    import websockets
    have = lambda: len([f for f in os.listdir(td) if f.endswith(".png")])
    async with websockets.connect(wsu, max_size=300*1024*1024, open_timeout=30) as ws:
        mid = [0]
        async def cmd(m, **p):
            mid[0] += 1
            await ws.send(json.dumps({"id": mid[0], "method": m, "params": p}))
            while True:
                r = json.loads(await ws.recv())
                if r.get("id") == mid[0]: return r.get("result", {})
        await cmd("Page.enable")
        await cmd("Emulation.setDeviceMetricsOverride", width=1080, height=1920,
                  deviceScaleFactor=1, mobile=False)
        await cmd("Page.navigate", url=url)
        await asyncio.sleep(1.2)
        start = have()
        for i in range(start, frames):
            t = i / 30.0
            await cmd("Runtime.evaluate", expression=f"window.__setT({t:.4f})")
            r = await cmd("Page.captureScreenshot", format="png")
            import base64 as b64
            with open(os.path.join(td, f"{i:04d}.png"), "wb") as f:
                f.write(b64.b64decode(r["data"]))
    return have() >= frames


def finish(name, dur):
    """PNG 序列 → mp4"""
    d = os.path.join(TMP, name)
    out = os.path.join(BASE, "动画", name + "_动画.mp4")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    r = subprocess.run([FFMPEG, "-y", "-v", "error", "-framerate", "30",
                        "-i", os.path.join(d, "%04d.png"),
                        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                        "-pix_fmt", "yuv420p", "-r", "30", out],
                       capture_output=True, text=True, errors="ignore")
    return r.returncode == 0


FFMPEG = r"C:/Users/Dell/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.1-full_build/bin/ffmpeg.exe"


async def main(names):
    cue_all = json.load(io.open(CUE, encoding="utf-8"))
    for n in names:
        cue = cue_all.get(n)
        if cue is None:
            print(f"  ⏭ {n}: 无时刻表，跳过"); continue
        dur = cue.get("_dur", 5.0)
        ok = await shoot(n, dur, cue)
        if ok:
            finish(n, dur)
            print(f"  ✅ {n}: {int(dur*30)} 帧 → {n}_动画.mp4")
        else:
            print(f"  ❌ {n}: 渲染失败")


if __name__ == "__main__":
    names = sys.argv[1:]
    if not names:
        cue_all = json.load(io.open(CUE, encoding="utf-8"))
        names = [k for k in cue_all if not k.startswith("_")]
    asyncio.run(main(names))
