"""Select the native backend without importing another platform's APIs."""
import sys
if sys.platform == 'win32':
    import platform_windows as backend
elif sys.platform == 'darwin':
    import platform_macos as backend
else:
    raise RuntimeError('Heyou Capture currently supports Windows and macOS.')
