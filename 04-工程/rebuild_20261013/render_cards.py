# -*- coding: utf-8 -*-
"""卡片动画渲染器（重建版 2026-10-13）——本机 headless Chrome + CDP 逐帧截图
   铁律：动画脚本必须写进临时 HTML（不能靠 Runtime.evaluate 注入）；每 lane 独立 user-data-dir。
   用法: python render_cards.py <任务json> <lane号> <lane总数>
   任务json: [{"html":..., "out":..., "frames":120, "fps":30}, ...]
"""
import os, sys, json, time, shutil, subprocess, base64, threading, http.client
sys.stdout.reconfigure(encoding='utf-8')
import websockets.sync.client as wsc

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
FFM = r"C:/Users/Dell/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.1-full_build/bin/ffmpeg.exe"
ROOT = "E:/心理咨询IP/04-工程/rebuild_20261013"
ANIM = open(os.path.join(ROOT, "anim.js"), encoding="utf-8").read()
W, H = 1080, 1920


class Lane:
    def __init__(self, idx, port):
        self.idx, self.port = idx, port
        self.prof = os.path.join(ROOT, "chrome_prof", "lane%d" % idx)
        os.makedirs(self.prof, exist_ok=True)
        self.proc = None
        self.ws = None
        self.msg = 0

    def start(self):
        if self.proc and self.proc.poll() is None:
            return
        self.proc = subprocess.Popen([
            CHROME, "--headless=new", "--remote-debugging-port=%d" % self.port,
            "--user-data-dir=" + self.prof, "--window-size=%d,%d" % (W, H),
            "--force-device-scale-factor=1", "--hide-scrollbars", "--disable-gpu",
            "--no-first-run", "--no-default-browser-check", "--disable-extensions",
            "--disable-background-timer-throttling", "--mute-audio", "about:blank",
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        tgt = None
        for _ in range(60):
            time.sleep(0.5)
            try:
                c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
                c.request("GET", "/json/list"); r = json.loads(c.getresponse().read()); c.close()
                for t in r:
                    if t.get("type") == "page" and t.get("webSocketDebuggerUrl"):
                        tgt = t["webSocketDebuggerUrl"]; break
                if tgt:
                    break
            except Exception:
                pass
        if not tgt:
            raise RuntimeError("lane%d chrome 未起来" % self.idx)
        self.ws = wsc.connect(tgt, max_size=64 * 1024 * 1024, open_timeout=20)
        self.cmd("Page.enable"); self.cmd("Runtime.enable")
        self.cmd("Emulation.setDeviceMetricsOverride", width=W, height=H, deviceScaleFactor=1, mobile=False)

    def cmd(self, method, **params):
        self.msg += 1
        self.ws.send(json.dumps({"id": self.msg, "method": method, "params": params}))
        while True:
            m = json.loads(self.ws.recv())
            if m.get("id") == self.msg:
                if "error" in m:
                    raise RuntimeError("%s -> %s" % (method, m["error"]))
                return m.get("result", {})

    def shoot(self, html, outdir, frames, fps=30):
        os.makedirs(outdir, exist_ok=True)
        for f in os.listdir(outdir):
            os.remove(os.path.join(outdir, f))
        tmp = os.path.join(ROOT, "tmp_html", "lane%d_%s.html" % (self.idx, os.path.basename(outdir)))
        os.makedirs(os.path.dirname(tmp), exist_ok=True)
        raw = open(html, encoding="utf-8").read()
        assert "</body>" in raw, html
        patched = raw.replace("</body>", "<script>%s</script></body>" % ANIM)   # ★注入写进文件
        open(tmp, "w", encoding="utf-8").write(patched)
        self.cmd("Page.navigate", url="file:///" + tmp.replace("\\", "/"))
        time.sleep(0.9)
        for i in range(frames):
            t = i / float(fps)
            self.cmd("Runtime.evaluate", expression="window.__setT(%f); 1" % t)
            # ★ JPEG 帧（q92）：PNG 每帧 2MB、6 车道时 18s/帧；JPEG 约 350KB，实测提速 6-8 倍
            r = self.cmd("Page.captureScreenshot", format="jpeg", quality=92, captureBeyondViewport=False)
            open(os.path.join(outdir, "f%04d.jpg" % i), "wb").write(base64.b64decode(r["data"]))
        return tmp

    def stop(self):
        try:
            if self.ws: self.ws.close()
        except Exception: pass
        if self.proc and self.proc.poll() is None:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(self.proc.pid)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def encode(frames_dir, out, fps=30):
    os.makedirs(os.path.dirname(out), exist_ok=True)
    src = os.path.join(frames_dir, "f%04d.jpg")
    if not os.path.exists(os.path.join(frames_dir, "f0000.jpg")):
        src = os.path.join(frames_dir, "f%04d.png")
    r = subprocess.run([FFM, "-y", "-v", "error", "-framerate", str(fps),
                        "-i", src, "-c:v", "libx264", "-preset", "veryfast", "-crf", "17",
                        "-pix_fmt", "yuv420p", "-r", str(fps), out], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError("编码失败 %s: %s" % (out, r.stderr[-400:]))
    return out


def main():
    tasks = json.load(open(sys.argv[1], encoding="utf-8"))
    idx, total = int(sys.argv[2]), int(sys.argv[3])
    mine = [t for i, t in enumerate(tasks) if i % total == idx]
    lane = Lane(idx, 9333 + idx)
    ok, bad = 0, []
    try:
        lane.start()
        for n, t in enumerate(mine, 1):
            name = os.path.splitext(os.path.basename(t["out"]))[0]
            fd = os.path.join(ROOT, "frames", name)
            t0 = time.time()
            try:
                lane.shoot(t["html"], fd, t.get("frames", 120), t.get("fps", 30))
                encode(fd, t["out"], t.get("fps", 30))
                ok += 1
                print("  [L%d %d/%d] %-34s %4.1fs" % (idx, n, len(mine), name, time.time() - t0), flush=True)
            except Exception as e:
                bad.append((name, str(e)[:200])); print("  [L%d] ✗ %s -> %s" % (idx, name, str(e)[:200]), flush=True)
            shutil.rmtree(fd, ignore_errors=True)
    finally:
        lane.stop()
    print("LANE%d DONE ok=%d bad=%d %s" % (idx, ok, len(bad), bad), flush=True)


if __name__ == "__main__":
    main()
