# Mac beta: help us test

This port is experimental. It has a native macOS implementation and automated build checks, but requires human testing on physical Apple Silicon and Intel Macs. Chrome is the only supported Mac browser in this first beta. Safari and other Chromium variants are not claimed to work.

## Setup

1. Download the matching Apple Silicon or Intel ZIP from Releases. Unzip and move HeyouCapture.app to Applications.
2. The beta is ad-hoc signed, not Developer ID signed or notarized. If Gatekeeper blocks it, use the standard macOS **Privacy & Security → Open Anyway** flow only if you trust this source. Do not disable Gatekeeper globally.
3. Grant **Screen & System Audio Recording** when macOS asks. Audio is not captured by this app. Restart after granting access.
4. Allow the app to control Google Chrome under **Automation**. In Chrome, enable **View → Developer → Allow JavaScript from Apple Events**. This lets the app read scroll dimensions and scroll the selected tab through Chrome's scripting interface.
5. Show the menu bar, clock, and date. Disable automatically hiding the menu bar. Use a normally maximized Chrome window, not fullscreen. The app captures the real macOS clock at the top, rather than adding a fake bottom clock.
6. If the global Escape shortcut does not work, report whether Accessibility/Input Monitoring permissions were granted. Do not grant unrelated permissions as a workaround.

References: [Apple's screen-recording permission guide](https://support.apple.com/guide/mac-help/control-access-screen-system-audio-recording-mchld6aa7d23/mac), [Chromium's AppleScript guide](https://www.chromium.org/developers/applescript/).

## Test with public content

- One non-scrolling page → one PNG.
- One long public GitHub PR → overlapping images from top to bottom.
- A window with three tabs, including a duplicate URL → three distinct folders.
- Start in the middle of a page → capture begins at the top and restores the original position.
- The original active tab is restored after the batch.
- Every screenshot includes the actual menu-bar date and clock.
- No JSON files inside the export collection.
- Retina and non-Retina displays; multiple monitors; an external monitor to the left of the main display.
- Permission denied → understandable message, no silent success.
- Esc → partial images retained, incomplete status.

The live companion is intentionally disabled on Mac until monitor placement and capture permissions are validated. The finished collection still appears afterward.

## Report

Use the **Mac beta tester report** issue form. Include chip, macOS/Chrome versions, display scaling, tested cases, expected/actual behavior, and sanitized screenshots if useful. Build success does not count as a passed capture test.
