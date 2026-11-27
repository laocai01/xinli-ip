"""★ 最终稳定版动画渲染（单实例、单profile、串行截图）
针对问题：
  - 并发起多个 Chrome → 进程堆积（200+）、profile 缓存爆炸（1.4G）、超时
  - 解法：**一个 Chrome 实例**，用 DevTools Protocol 连续截图（不开多进程）

如果 CDP 仍崩，退路：单 Chrome + JS 自驱动截图（页面内 setInterval + canvas.toDataURL 存盘）
"""
import io, os, sys, json, time, base64, asyncio, subprocess, shutil, re, socket
import urllib.request

BASE = r"E:/心理咨询IP/07-形象设计/卡片v2"
OUT  = os.path.join(BASE, "动画")
CHROME = r"C:/Program Files/Google/Chrome/Application/chrome.exe"
FF = r"C:/Users/Dell/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.1-full_build/bin/ffmpeg.exe"
LOGO = r"E:/心理咨询IP/07-形象设计/交付_v5/圆形标/老蔡说_圆形标_400.png"
lu = "data:image/png;base64," + base64.b64encode(open(LOGO,"rb").read()).decode()
os.makedirs(OUT, exist_ok=True)

ANIM_JS = """
<script>
// ★ 2026-10-08 董事长：动画再慢一点 + 带感觉的显现
// 每层入场 1.6s（原 1.1s），各层间隔拉到 0.9-1.1s，全片 6.5s 播完
var DUR_IN=1.60, RISE=64;
// ★ 签名「正在学心理学的普通人」不做动画（董事长定）→ 不在 TL 里，保持常显
var TL=[{id:"e_brand",t:0.30,fx:"rise"},{id:"e_rule",t:1.00,fx:"grow"},
        {id:"e_big",t:1.70,fx:"rise"},
        {id:"e_em",t:3.00,fx:"pop"},
        {id:"e_punch",t:4.30,fx:"rise"}];
// easeOutQuad：先快后慢，落定稳（比 cubic 更"有质感"）
function ease(x){return 1-(1-x)*(1-x);}
function setT(t){TL.forEach(function(it){var el=document.getElementById(it.id);if(!el)return;
 var p=(t-it.t)/DUR_IN;if(p<0)p=0;if(p>1)p=1;var e=ease(p);
 el.style.opacity=(it.fx==="pop")?Math.min(1,e*1.5):e;
 if(it.fx==="rise")el.style.transform="translateY("+(RISE*(1-e))+"px) scale("+(0.955+0.045*e)+")";
 else if(it.fx==="pop")el.style.transform="scale("+(0.90+0.10*e)+")";
 else if(it.fx==="grow"){el.style.transform="scaleX("+e+")";el.style.transformOrigin="center";}
 else el.style.transform="none";});}
window.__setT = setT;
</script>
"""

def prep(name):
    p = os.path.join(BASE, name + ".html")
    s = io.open(p, encoding="utf-8").read().replace("__LOGO__", lu)
    if name.startswith("封面") or name.startswith("B1封面") or name.startswith("B2封面"):
        s = s.replace('<div class="top">', '<div class="top" id="e_brand">', 1)
        s = s.replace('<div class="ep">', '<div class="ep" id="e_ep">', 1)
        s = s.replace('<div class="rule"></div>', '<div class="rule" id="e_rule"></div>', 1)
        s = s.replace('<div class="stage">', '<div class="stage" id="e_stage">', 1)
        s = s.replace('<div class="sign">', '<div class="sign" id="e_sign">', 1)
        s = s.replace('{id:"e_rule",t:0.55,fx:"grow"}', '{id:"e_ep",t:0.55,fx:"rise"},{id:"e_rule",t:1.15,fx:"grow"}')
        s = s.replace('{id:"e_stage",t:0.85,fx:"rise"}', '{id:"e_stage",t:1.45,fx:"rise"}')
        s = s.replace('{id:"e_punch",t:2.25,fx:"rise"},', '')
        s = s.replace('{id:"e_sign",t:2.85,fx:"fade"}', '{id:"e_sign",t:2.90,fx:"fade"}')
        s = s.replace("var DUR_IN=0.75", "var DUR_IN=0.90")
    else:
        # ★ 内文卡：class 是 brand / rule / stage / big / punch / sign
        s = s.replace('<div class="brand">', '<div class="brand" id="e_brand">', 1)
        s = s.replace('<div class="rule"></div>', '<div class="rule" id="e_rule"></div>', 1)
        s = s.replace('<div class="stage">', '<div class="stage" id="e_stage">', 1)
        s = s.replace('<div class="big">', '<div class="big" id="e_big">', 1)     # 主标题
        s = s.replace('<div class="punch">', '<div class="punch" id="e_punch">', 1)
        s = s.replace('<div class="sign">', '<div class="sign" id="e_sign">', 1)
        # 焦点色块 em：给 <em> 打 id
        s = s.replace('<em>', '<em id="e_em">', 1)
    s = re.sub(r'<script>.*?</script>', '', s, flags=re.S)
    s = s.replace("</body>", ANIM_JS + "</body>")
    out = os.path.join(BASE, "_anim_" + name + ".html")
    io.open(out, "w", encoding="utf-8").write(s)
    return out

async def render(name, dur, is_cover=False):
    """★ 带断点续渲：中途 CDP 掉线就重开 Chrome，从已完成的帧继续"""
    import websockets
    ah = prep(name)
    url = "file:///" + ah.replace("\\","/")
    frames = int(dur*30)
    td = f"E:/tmp/anim_one/{name}"
    os.makedirs(td, exist_ok=True)

    def done_frames():
        return len([f for f in os.listdir(td) if f.endswith(".png")])

    n = done_frames()
    if n >= frames:
        pass  # 已渲完，直接编码
    else:
        for round_ in range(6):          # 最多重开 6 次
            n = done_frames()
            if n >= frames:
                break
            sk = socket.socket(); sk.bind(("127.0.0.1",0)); port = sk.getsockname()[1]; sk.close()
            udd = f"E:/tmp/cdpprof_{port}"
            proc = subprocess.Popen([CHROME,"--headless=new","--disable-gpu","--hide-scrollbars",
                "--no-first-run","--no-default-browser-check","--disable-extensions",
                "--disable-dev-shm-usage","--user-data-dir="+udd,
                "--remote-debugging-port="+str(port),
                "--force-device-scale-factor=1","--window-size=1080,1920","about:blank"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            ws_url=None
            for _ in range(80):
                try:
                    d=json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json", timeout=3))
                    for it in d:
                        if it.get("type")=="page": ws_url=it["webSocketDebuggerUrl"]; break
                    if ws_url: break
                except Exception: pass
                time.sleep(0.25)
            if not ws_url:
                proc.kill(); shutil.rmtree(udd, ignore_errors=True); continue
            try:
                async with websockets.connect(ws_url, max_size=300*1024*1024, open_timeout=30) as ws:
                    mid=[0]
                    async def cmd(m,**p):
                        mid[0]+=1
                        await ws.send(json.dumps({"id":mid[0],"method":m,"params":p}))
                        while True:
                            r=json.loads(await ws.recv())
                            if r.get("id")==mid[0]: return r.get("result",{})
                    await cmd("Page.enable")
                    await cmd("Emulation.setDeviceMetricsOverride",width=1080,height=1920,deviceScaleFactor=1,mobile=False)
                    await cmd("Page.navigate",url=url)
                    await asyncio.sleep(1.5)
                    i = done_frames()
                    while i < frames:
                        await cmd("Runtime.evaluate",expression=f"window.__setT({i/30})")
                        r=await cmd("Page.captureScreenshot",format="png")
                        open(os.path.join(td,f"f{i:04d}.png"),"wb").write(base64.b64decode(r["data"]))
                        i+=1
                        if i%30==0: print(f"    {name} {i}/{frames}", flush=True)
            except Exception as e:
                print(f"    断线 {done_frames()}/{frames} ({type(e).__name__})，重连中…", flush=True)
            finally:
                try: proc.kill()
                except Exception: pass
                try: shutil.rmtree(udd, ignore_errors=True)
                except Exception: pass

    n = done_frames()
    if n < frames*0.9:
        print(f"    {name}: 只完成 {n}/{frames}", flush=True)
        return n, frames, False
    out_mp4 = os.path.join(OUT, name+"_动画.mp4")
    subprocess.run([FF,"-y","-v","error","-framerate","30","-i",os.path.join(td,"f%04d.png"),
        "-c:v","libx264","-pix_fmt","yuv420p","-crf","16",out_mp4],capture_output=True,timeout=300)
    return n, frames, os.path.exists(out_mp4)

if __name__ == "__main__":
    name = sys.argv[1]; dur = float(sys.argv[2])
    is_cover = len(sys.argv) > 3 and sys.argv[3] == "cover"
    n, want, ok = asyncio.run(render(name, dur, is_cover))
    print(f"{name}: {n}/{want} {'OK' if ok else 'FAIL'}")
