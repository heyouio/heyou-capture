# Contributing

Start with an issue describing the user-visible problem and the operating system/browser versions. For macOS, use the Mac tester report template. Please test only with public pages and avoid uploading diagnostic logs without reviewing URLs and file paths.

Development: Python 3.12, `pip install -r requirements.txt`, then `python app.py`.

Portable tests: `python -m unittest test_portable.py`.

Windows UI checks: `python -m unittest test_app.py`. The isolated Chrome integration test is `python test_chrome_capture.py --ui`; it opens local test pages in a separate browser profile and checks tab restoration, image counts, progress events, and PNG-only exports.

macOS has a separate native backend. Build results alone must not be described as functional macOS validation. Include hardware, macOS, Chrome, permission state, monitor arrangement, and evidence of complete top-to-bottom capture when reporting results.

Keep generated captures, logs, builds, virtual environments, credentials, and browser profiles out of commits. Tests should not require private Heyou services. PRs should explain the behavior change and how it was verified.
