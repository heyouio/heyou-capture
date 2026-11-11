"""Record the real Windows app with only public PRs in an isolated Chrome profile.

Optional recording dependency: pip install imageio-ffmpeg
Run from the repository root. No microphone or other desktop windows are recorded.
"""
import os
from pathlib import Path
import sys
import time
import subprocess
from unittest.mock import patch
import tkinter as tk
from PIL import ImageGrab
import imageio_ffmpeg

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app import App
from platform_windows import browsers, monitors, user32, native_handle

URLS = ['https://github.com/microsoft/vscode/pull/347612', 'https://github.com/microsoft/vscode/pull/347605']
FPS = 8
OUT = ROOT/'marketing'/'heyou-capture-demo.mp4'
def main():
    session=ROOT/'.demo-session'
    session.mkdir(exist_ok=True)
    os.environ['LOCALAPPDATA']=str(session/'app-data')
    chrome=Path(os.environ.get('PROGRAMFILES', r'C:\Program Files'))/'Google/Chrome/Application/chrome.exe'
    process=subprocess.Popen([str(chrome),'--user-data-dir='+str(session/'profile'),'--no-first-run','--no-default-browser-check','--disable-notifications','--force-renderer-accessibility','--new-window',*URLS],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    window=None;root=None;writer=None
    try:
        for _ in range(180):
            window=next((w for w in browsers() if 'Google Chrome' in w[1] and any(key in w[1] for key in ('rounded primary','Preserve code order'))),None)
            if window:break
            time.sleep(.25)
        if not window:raise RuntimeError('Public PR pages did not load; no recording was made.')
        display,bbox=next((item for item in monitors() if item[1][0]==0),monitors()[0])
        user32.ShowWindow(window[0],9)
        user32.SetWindowPos(window[0],None,bbox[0]+20,bbox[1]+20,bbox[2]-bbox[0]-40,bbox[3]-bbox[1]-80,0x0014)
        user32.ShowWindow(window[0],3)
        user32.SetWindowPos(window[0],-1,0,0,0,0,0x0003)
        user32.SetForegroundWindow(window[0])
        time.sleep(3)
        ImageGrab.grab(bbox=bbox,all_screens=True).save(session/'display-check.png')
        if '--review' in sys.argv:
            print('Review privacy frame:',session/'display-check.png',flush=True)
            input('Press Enter after reviewing the frame. ')
        root=tk.Tk()
        with patch('app.browsers',return_value=[window]):
            app=App(root)
            app.browser.current(1);app.follow_browser_display()
            app.output.set(str(session/'exports'));app.delay.set(1.0)
            root.update()
            app.preview()
            other=next((r for m,r in monitors() if m!=display),None)
            if other is None:raise RuntimeError('This demo requires a second display so the live app stays out of the captured PRs.')
            user32.SetWindowPos(native_handle(root),None,other[0]+20,other[1]+20,1180,920,0x0014)
            root.update()
            root.attributes('-topmost',True)
            app.preview()
            first_shot=ImageGrab.grab(window=native_handle(root))
            video_size=(first_shot.width//2*2,first_shot.height//2*2)
            writer=imageio_ffmpeg.write_frames(str(OUT),video_size,fps=FPS,codec='libx264',pix_fmt_in='rgb24',pix_fmt_out='yuv420p',quality=8,output_params=['-movflags','+faststart'],macro_block_size=1)
            writer.send(None)
            started=time.monotonic();capture_started=False;finished=None;frames=0
            while True:
                tick=time.monotonic();root.update()
                if not capture_started and tick-started>3:
                    app.start();capture_started=True
                if capture_started and not app.busy and finished is None:finished=tick
                if tick-started>150:raise RuntimeError('Recording timed out; inspect capture status.')
                shot=ImageGrab.grab(window=native_handle(root))
                if shot.width<500 or shot.height<300:raise RuntimeError('The app window could not be recorded safely.')
                if (shot.width//2*2,shot.height//2*2) != video_size:
                    raise RuntimeError('App window size changed during recording.')
                frame=shot.convert('RGB').crop((0,0,*video_size))
                writer.send(frame.tobytes());frames+=1
                if frames==8:frame.save(ROOT/'marketing'/'demo-poster.png')
                if finished and tick-finished>5:break
                time.sleep(max(0,1/FPS-(time.monotonic()-tick)))
            if app.collection.count == 0:raise RuntimeError('No screenshots were captured: '+app.status.get())
            print('VIDEO:',OUT)
            print('RESULT:',app.status.get())
    finally:
        if writer:writer.close()
        if root:
            from test_app import close_root
            close_root(root)
        if window:
            import ctypes
            user32.PostMessageW.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_size_t,ctypes.c_ssize_t]
            user32.PostMessageW(window[0],0x10,0,0)
        try:process.wait(timeout=3)
        except subprocess.TimeoutExpired:pass

if __name__=='__main__':main()
