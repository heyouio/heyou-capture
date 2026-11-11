"""Build an ad-hoc signed, explicitly experimental native-architecture Mac app."""
import platform
import plistlib
import subprocess
from pathlib import Path
import PyInstaller.__main__

if platform.system() != 'Darwin': raise SystemExit('Run this build on macOS (or the GitHub macOS workflow).')
PyInstaller.__main__.run(['--noconfirm','--windowed','--name','HeyouCapture',
    '--osx-bundle-identifier','io.heyou.capture','--collect-all','customtkinter',
    '--icon','assets/heyou.icns','--add-data','assets:assets',
    '--add-data','browser_macos.js:.','app.py'])
bundle=Path('dist/HeyouCapture.app')
info=bundle/'Contents/Info.plist'
with info.open('rb') as f: values=plistlib.load(f)
values.update(NSAppleEventsUsageDescription='Heyou Capture visits and scrolls your selected Chrome tabs to save local screenshots.',
              NSScreenCaptureUsageDescription='Heyou Capture saves the selected display, including the real system clock, to your chosen folder.',
              NSHighResolutionCapable=True, CFBundleShortVersionString='0.1.0', CFBundleVersion='1')
with info.open('wb') as f: plistlib.dump(values,f)
subprocess.run(['codesign','--force','--deep','--sign','-',str(bundle)],check=True)
arch='arm64' if platform.machine()=='arm64' else 'x64'
subprocess.run(['ditto','-c','-k','--sequesterRsrc','--keepParent',str(bundle),f'dist/HeyouCapture-macOS-{arch}-experimental.zip'],check=True)
