# Desktop startup

The main window starts hidden and maximized. The frontend sets the native background for the chosen theme before revealing it. A recovery timeout reveals the window if frontend readiness fails. The private database worker is started by Tauri and has no visible console in Windows release builds.

These existing startup measures are preserved. The 0.2.7 Windows build, black-flash behavior, and worker process lifecycle require confirmation on Windows.
