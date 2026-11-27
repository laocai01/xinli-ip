"""★★ 全量卡片/封面/闭环页动画渲染器 —— 看得见版 + 断点续渲（2026-10-08 定稿）
用法:
  python render_all.py              # 跑全部
  python render_all.py A2n_01钩子    # 跑单张

规格（董事长"按看得见版来"）:
  · 主标题从下 200px 滑入 / 焦点色块 0.3→1.0 弹入（带回弹）
  · 签名「正在学心理学的普通人」不做动画
  · 断线自动重连，从已完成帧继续
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

# ============ ① 内文卡动画（看得见版 + 分层）============
# 分层顺序：品牌条 → 分割线 → 主标题普通字 → 辅助句 → ★重点字(<em>)最后出
JS_CARD = """
<script>
window.__setT=function(t){
 function cl(x){return x<0?0:x>1?1:x;}
 function out(p){return 1-Math.pow(1-p,2);}
 function back(p){var c=1.6;return 1+(c+1)*Math.pow(p-1,3)+c*Math.pow(p-1,2);}
 var E=function(i){return document.getElementById(i);};
 // 1) 品牌条 0.15-0.75
 var p1=out(cl((t-0.15)/0.60)),b=E('e_brand');
 if(b){b.style.opacity=p1;b.style.transform='translateY('+(-45*(1-p1)).toFixed(1)+'px)';}
 // 2) 分割线 0.60-1.10
 var p2=out(cl((t-0.60)/0.50)),r=E('e_rule');
 if(r){r.style.transform='scaleX('+p2.toFixed(3)+')';r.style.transformOrigin='center';}
 // 3) 主标题普通字 0.80-1.40（从下 200px 滑入）
 var p3=out(cl((t-0.80)/0.60)),g=E('e_big');
 if(g){g.style.opacity=p3;g.style.transform='translateY('+(200*(1-p3)).toFixed(1)+'px)';}
 // 4) 辅助句 1.60-2.20（先给辅助句，把重点字压到最后）
 var p4=out(cl((t-1.60)/0.60)),pu=E('e_punch');
 if(pu){pu.style.opacity=p4;pu.style.transform='translateY('+(90*(1-p4)).toFixed(1)+'px)';}
 // 5) ★★★ 焦点色块（重点字）最后出：2.70-3.45，缩放弹入
 var p5=back(cl((t-2.70)/0.75)),e=E('e_em');
 if(e){e.style.opacity=cl((t-2.70)/0.35);e.style.transform='scale('+(0.3+0.7*p5).toFixed(3)+')';}
 // 6) ★ B线专用：左栏大字从上滑入（0.40-1.10）+ 板块标签淡入（1.60-2.10）
 var cw=E('e_corekey');
 if(cw){cw.style.opacity=out(cl((t-0.40)/0.70));cw.style.transform='translateY('+(-120*(1-out(cl((t-0.40)/0.70)))).toFixed(1)+'px)';}
 var nl=E('e_numline');
 if(nl){nl.style.transform='scaleY('+out(cl((t-0.80)/0.60)).toFixed(3)+')';nl.style.transformOrigin='top';}
 var lb=E('e_label');
 if(lb){lb.style.opacity=out(cl((t-1.60)/0.50));lb.style.transform='translateY('+(40*(1-out(cl((t-1.60)/0.50)))).toFixed(1)+'px)';}
 // 签名不动画
};
</script>
"""

# ============ ② 封面动画（看得见版 + 重点字最后出）============
JS_COVER = """
<script>
window.__setT=function(t){
 function cl(x){return x<0?0:x>1?1:x;}
 function out(p){return 1-Math.pow(1-p,2);}
 function back(p){var c=1.6;return 1+(c+1)*Math.pow(p-1,3)+c*Math.pow(p-1,2);}
 var E=function(i){return document.getElementById(i);};
 // 1) 品牌条 0.15-0.75
 var p1=out(cl((t-0.15)/0.60)),b=E('e_brand');
 if(b){b.style.opacity=p1;b.style.transform='translateY('+(-45*(1-p1)).toFixed(1)+'px)';}
 // 2) 第X讲标签 0.70-1.30
 var p2=out(cl((t-0.70)/0.60)),ep=E('e_ep');
 if(ep){ep.style.opacity=p2;ep.style.transform='translateY('+(60*(1-p2)).toFixed(1)+'px)';}
 // 3) 分割线 1.20-1.70
 var p3=out(cl((t-1.20)/0.50)),r=E('e_rule');
 if(r){r.style.transform='scaleX('+p3.toFixed(3)+')';r.style.transformOrigin='center';}
 // 4) 主标题普通字 1.60-2.30（从下 220px）
 var p4=out(cl((t-1.60)/0.70)),g=E('e_big');
 if(g){g.style.opacity=p4;g.style.transform='translateY('+(220*(1-p4)).toFixed(1)+'px)';}
 // 5) ★★★ 重点字(<em>)最后出：2.60-3.40 缩放弹入
 var p5=back(cl((t-2.60)/0.80)),e=E('e_em');
 if(e){e.style.opacity=cl((t-2.60)/0.40);e.style.transform='scale('+(0.3+0.7*p5).toFixed(3)+')';}
};
</script>
"""

# ============ ③ 闭环页动画（看得见版 + 分层）============
# 顺序：品牌条 → 分割线 → 小标题 → 三个要点依次 → ★结论色块最后出 → 预告 → 涨粉
JS_END = """
<script>
window.__setT=function(t){
 function cl(x){return x<0?0:x>1?1:x;}
 function out(p){return 1-Math.pow(1-p,2);}
 function back(p){var c=1.6;return 1+(c+1)*Math.pow(p-1,3)+c*Math.pow(p-1,2);}
 var E=function(i){return document.getElementById(i);};
 // 1) 品牌条 0.15-0.75
 var p1=out(cl((t-0.15)/0.60)),b=E('e_brand');
 if(b){b.style.opacity=p1;b.style.transform='translateY('+(-45*(1-p1)).toFixed(1)+'px)';}
 // 2) 分割线 0.60-1.10
 var p2=out(cl((t-0.60)/0.50)),r=E('e_rule');
 if(r){r.style.transform='scaleX('+p2.toFixed(3)+')';r.style.transformOrigin='center';}
 // 3) 小标题 0.90-1.40
 var p3=out(cl((t-0.90)/0.50)),tg=E('e_tag');
 if(tg){tg.style.opacity=p3;}
 // 4) 三个要点依次滑入 1.60 / 2.05 / 2.50
 for(var k=1;k<=3;k++){
   var pp=out(cl((t-(1.60+0.45*(k-1)))/0.55)),el=E('e_i'+k);
   if(el){el.style.opacity=pp;el.style.transform='translateY('+(110*(1-pp)).toFixed(1)+'px)';}
 }
 // 5) ★★★ 结论色块（这一讲的答案）最后出：3.30-4.15 缩放弹入
 var p5=back(cl((t-3.30)/0.85)),c=E('e_concl');
 if(c){c.style.opacity=cl((t-3.30)/0.40);c.style.transform='scale('+(0.35+0.65*p5).toFixed(3)+')';}
 // 6) 下一讲预告 4.60-5.20
 var p6=out(cl((t-4.60)/0.60)),nx=E('e_next');
 if(nx){nx.style.opacity=p6;nx.style.transform='translateY('+(100*(1-p6)).toFixed(1)+'px)';}
 // 7) 涨粉引导 5.40-5.90
 var p7=out(cl((t-5.40)/0.50)),fl=E('e_follow');
 if(fl){fl.style.opacity=p7;}
 // 签名不动画
};
</script>
"""

# ============ HTML 元素注入 ============
IDS_CARD = [('<div class="brand">','<div class="brand" id="e_brand">'),
 ('<div class="rule"></div>','<div class="rule" id="e_rule"></div>'),
 ('<div class="big">','<div class="big" id="e_big">'),
 ('<em>','<em id="e_em">'),
 ('<div class="punch">','<div class="punch" id="e_punch">'),
 ('<div class="sign">','<div class="sign" id="e_sign">'),
 # ★ B线专用（A线没有这些元素，replace 不命中即无害）
 ('<div class="col-left">','<div class="col-left" id="e_colleft">'),
 ('<div class="corekey">','<div class="corekey" id="e_corekey">'),
 ('<div class="numline">','<div class="numline" id="e_numline">'),
 ('<div class="label">','<div class="label" id="e_label">')]

IDS_COVER = [('<div class="top">','<div class="top" id="e_brand">'),
 ('<div class="ep">','<div class="ep" id="e_ep">'),
 ('<div class="rule"></div>','<div class="rule" id="e_rule"></div>'),
 ('<div class="big">','<div class="big" id="e_big">'),
 ('<em>','<em id="e_em">'),
 ('<div class="stage">','<div class="stage" id="e_stage">'),
 ('<div class="sign">','<div class="sign" id="e_sign">')]

IDS_END = [('<div class="brand">','<div class="brand" id="e_brand">'),
 ('<div class="rule"></div>','<div class="rule" id="e_rule"></div>'),
 ('<div class="tag">','<div class="tag" id="e_tag">'),
 ('<div class="concl">','<div class="concl" id="e_concl">'),
 ('<div class="sub">','<div class="sub" id="e_sub">'),
 ('<div class="next">','<div class="next" id="e_next">'),
 ('<div class="follow">','<div class="follow" id="e_follow">'),
 ('<div class="sign">','<div class="sign" id="e_sign">')]

def kind_of(name):
    if name.startswith("封面") or name.startswith("B1封面") or name.startswith("B2封面"):
        return "cover"
    if name.startswith("闭环"):
        return "end"
    return "card"

def prep(name):
    k = kind_of(name)
    p = os.path.join(BASE, name + ".html")
    s = io.open(p, encoding="utf-8").read().replace("__LOGO__", lu)
    if k == "cover":
        for a,b in IDS_COVER: s = s.replace(a,b,1)
        js = JS_COVER
    elif k == "end":
        for a,b in IDS_END: s = s.replace(a,b,1)
        parts = s.split('<div class="item"')
        for i in (1,2,3):
            if len(parts) > i:
                parts[i] = parts[i].replace('>', f' id="e_i{i}">', 1)
        s = '<div class="item"'.join(parts)
        js = JS_END
    else:
        for a,b in IDS_CARD: s = s.replace(a,b,1)
        js = JS_CARD
    s = re.sub(r'<script>.*?</script>','',s,flags=re.S).replace("</body>", js+"</body>")
    o = os.path.join(BASE, "_anim_"+name+".html")
    io.open(o,"w",encoding="utf-8").write(s); return o

# ============ 渲染（断点续渲）============
async def render(name, dur):
    import websockets
    hp = prep(name); url = "file:///"+hp.replace("\\","/")
    frames = int(dur*30); td = f"E:/tmp/anim_all/{name}"
    os.makedirs(td, exist_ok=True)
    def done(): return len([f for f in os.listdir(td) if f.endswith(".png")])
    if done() < frames:
        for _ in range(8):
            if done() >= frames: break
            sk=socket.socket(); sk.bind(("127.0.0.1",0)); port=sk.getsockname()[1]; sk.close()
            udd=f"E:/tmp/allprof_{port}"
            proc=subprocess.Popen([CHROME,"--headless=new","--disable-gpu","--hide-scrollbars",
              "--no-first-run","--no-default-browser-check","--disable-extensions","--disable-dev-shm-usage",
              "--user-data-dir="+udd,"--remote-debugging-port="+str(port),
              "--force-device-scale-factor=1","--window-size=1080,1920","about:blank"],
              stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            wsu=None
            for _ in range(80):
                try:
                    d=json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json",timeout=3))
                    for it in d:
                        if it.get("type")=="page": wsu=it["webSocketDebuggerUrl"]; break
                    if wsu: break
                except Exception: pass
                time.sleep(0.25)
            if not wsu:
                proc.kill(); shutil.rmtree(udd,ignore_errors=True); continue
            try:
                async with websockets.connect(wsu,max_size=300*1024*1024,open_timeout=30) as ws:
                    mid=[0]
                    async def cmd(m,**p):
                        mid[0]+=1; await ws.send(json.dumps({"id":mid[0],"method":m,"params":p}))
                        while True:
                            r=json.loads(await ws.recv())
                            if r.get("id")==mid[0]: return r.get("result",{})
                    await cmd("Page.enable")
                    await cmd("Emulation.setDeviceMetricsOverride",width=1080,height=1920,deviceScaleFactor=1,mobile=False)
                    await cmd("Page.navigate",url=url); await asyncio.sleep(1.5)
                    i=done()
                    while i < frames:
                        await cmd("Runtime.evaluate",expression=f"window.__setT({i/30})")
                        r=await cmd("Page.captureScreenshot",format="png")
                        open(os.path.join(td,f"f{i:04d}.png"),"wb").write(base64.b64decode(r["data"]))
                        i+=1
                        if i%30==0: print(f"    {name} {i}/{frames}", flush=True)
            except Exception as ex:
                print(f"    断线 {done()}/{frames}，重连…", flush=True)
            finally:
                try: proc.kill()
                except Exception: pass
                shutil.rmtree(udd,ignore_errors=True)
    n = done()
    if n < frames*0.9:
        print(f"  ❌ {name}: 只完成 {n}/{frames}", flush=True); return False
    o = os.path.join(OUT, name+"_动画.mp4")
    subprocess.run([FF,"-y","-v","error","-framerate","30","-i",os.path.join(td,"f%04d.png"),
      "-c:v","libx264","-pix_fmt","yuv420p","-crf","16",o],capture_output=True,timeout=300)
    print(f"  ✅ {name}: {n}/{frames} → {os.path.basename(o)}", flush=True)
    return True

# 全部任务：(名称, 时长秒)  ★ 2026-10-08 按脚本重定：A2=6/A3=7/B1=7/B2=6
TASKS = [
    # 封面（停留8秒口径，动画4.0s）
    ("封面_新_第1讲", 4.0), ("封面_新_第2讲", 4.0),
    ("B1封面_第1讲", 4.0),  ("B2封面_第2讲", 4.0),
    # A2 六卡
    ("A2n_01钩子",4.0),("A2n_02痛点",4.0),("A2n_03机制",4.0),
    ("A2n_04转折",4.0),("A2n_05方法",4.0),("A2n_06收束",4.0),
    # A3 七卡
    ("A3n_01钩子",4.0),("A3n_02总览",4.0),("A3n_03停",4.0),("A3n_04退",4.0),
    ("A3n_05看",4.0),("A3n_06做",4.0),("A3n_07收束",4.0),
    # B1 七卡
    ("B1n_01钩子",4.0),("B1n_02场景",4.0),("B1n_03机制",4.0),("B1n_04点破",4.0),
    ("B1n_05转折",4.0),("B1n_06方法",4.0),("B1n_07收束",4.0),
    # B2 六卡
    ("B2n_01钩子",4.0),("B2n_02痛点",4.0),("B2n_03机制",4.0),
    ("B2n_04对比",4.0),("B2n_05方法",4.0),("B2n_06收束",4.0),
    # 四条闭环页（动画6.6秒，停留8秒）
    ("闭环_第1讲",6.6),("闭环_第2讲",6.6),("闭环_第3讲",6.6),("闭环_第4讲",6.6),
    # ★ 2026-10-08 新四条（A4/A5/B3/B4）
    # ★★ 时长必须 4.0s：JS 动画表里辅助句 1.60s、重点字<em> 2.70s 才开始
    #    原来渲 1.4s → 辅助句与重点字永远不出（成片"文字欠缺"的根因）
    ("A4n_01钩子",4.0),("A4n_02反常识",4.0),("A4n_03方法",4.0),("A4n_04金句",4.0),
    ("A5n_01钩子",4.0),("A5n_02具象",4.0),("A5n_03核心",4.0),("A5n_04方法",4.0),
    ("B3n_01钩子",4.0),("B3n_02痛点",4.0),("B3n_03方法",4.0),("B3n_04关键",4.0),("B3n_05具象",4.0),
    ("B4n_01钩子",4.0),("B4n_02反常识",4.0),("B4n_03具象",4.0),("B4n_04方法",4.0),("B4n_05金句",4.0),
    ("封面A4",6.0),("封面A5",6.0),("封面B3",6.0),("封面B4",6.0),
    ("闭环A4",5.0),("闭环A5",5.0),("闭环B3",5.0),("闭环B4",5.0),
]

if __name__ == "__main__":
    names = sys.argv[1:]
    todo = [t for t in TASKS if not names or t[0] in names]
    print(f"共 {len(todo)} 个任务")
    ok = 0
    for nm, d in todo:
        try:
            if asyncio.run(render(nm, d)): ok += 1
        except Exception as e:
            print(f"  ❌ {nm} 异常 {type(e).__name__}", flush=True)
    print(f"\n完成 {ok}/{len(todo)}")
