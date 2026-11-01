import Cocoa
import WebKit

class AppDelegate: NSObject, NSApplicationDelegate, NSWindowDelegate {
    var window: NSWindow!
    var webView: WKWebView!
    var serverProcess: Process?
    let port = 5678
    let serverURLString = "http://127.0.0.1:5678"

    func applicationDidFinishLaunching(_ notification: Notification) {
        setupMenu()
        setupAppIcon()
        startServerIfNeeded()
        createWindow()
        loadApp()
    }

    func setupAppIcon() {
        if let iconURL = Bundle.main.url(forResource: "AppIcon", withExtension: "icns"),
           let image = NSImage(contentsOf: iconURL) {
            NSApplication.shared.applicationIconImage = image
        }
    }

    func setupMenu() {
        let mainMenu = NSMenu()

        // App Menu
        let appMenuItem = NSMenuItem()
        mainMenu.addItem(appMenuItem)
        let appMenu = NSMenu()
        appMenuItem.submenu = appMenu

        let appName = "SoundCloud Downloader"
        appMenu.addItem(withTitle: "О программе \(appName)", action: #selector(NSApplication.orderFrontStandardAboutPanel(_:)), keyEquivalent: "")
        appMenu.addItem(NSMenuItem.separator())
        appMenu.addItem(withTitle: "Скрыть \(appName)", action: #selector(NSApplication.hide(_:)), keyEquivalent: "h")
        let hideOthers = NSMenuItem(title: "Скрыть остальные", action: #selector(NSApplication.hideOtherApplications(_:)), keyEquivalent: "h")
        hideOthers.keyEquivalentModifierMask = [.command, .option]
        appMenu.addItem(hideOthers)
        appMenu.addItem(withTitle: "Показать все", action: #selector(NSApplication.unhideAllApplications(_:)), keyEquivalent: "")
        appMenu.addItem(NSMenuItem.separator())
        appMenu.addItem(withTitle: "Завершить \(appName)", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")

        // Edit Menu (Essential for Cmd+C, Cmd+V, Cmd+A)
        let editMenuItem = NSMenuItem()
        mainMenu.addItem(editMenuItem)
        let editMenu = NSMenu(title: "Правка")
        editMenuItem.submenu = editMenu
        editMenu.addItem(withTitle: "Отменить", action: Selector(("undo:")), keyEquivalent: "z")
        editMenu.addItem(withTitle: "Повторить", action: Selector(("redo:")), keyEquivalent: "Z")
        editMenu.addItem(NSMenuItem.separator())
        editMenu.addItem(withTitle: "Вырезать", action: #selector(NSText.cut(_:)), keyEquivalent: "x")
        editMenu.addItem(withTitle: "Скопировать", action: #selector(NSText.copy(_:)), keyEquivalent: "c")
        editMenu.addItem(withTitle: "Вставить", action: #selector(NSText.paste(_:)), keyEquivalent: "v")
        editMenu.addItem(withTitle: "Выбрать все", action: #selector(NSText.selectAll(_:)), keyEquivalent: "a")

        // Window Menu
        let windowMenuItem = NSMenuItem()
        mainMenu.addItem(windowMenuItem)
        let windowMenu = NSMenu(title: "Окно")
        windowMenuItem.submenu = windowMenu
        windowMenu.addItem(withTitle: "Свернуть", action: #selector(NSWindow.performMiniaturize(_:)), keyEquivalent: "m")
        windowMenu.addItem(withTitle: "Увеличить", action: #selector(NSWindow.performZoom(_:)), keyEquivalent: "")

        NSApplication.shared.mainMenu = mainMenu
    }

    func isServerAlive() -> Bool {
        guard let url = URL(string: "\(serverURLString)/api/status") else { return false }
        var request = URLRequest(url: url)
        request.timeoutInterval = 0.5
        let semaphore = DispatchSemaphore(value: 0)
        var alive = false
        let task = URLSession.shared.dataTask(with: request) { _, response, _ in
            if let http = response as? HTTPURLResponse, http.statusCode == 200 {
                alive = true
            }
            semaphore.signal()
        }
        task.resume()
        _ = semaphore.wait(timeout: .now() + 0.6)
        return alive
    }

    func findPythonExecutable() -> URL {
        // 1. Try finding python3 in user environment via /usr/bin/which
        let whichProcess = Process()
        whichProcess.executableURL = URL(fileURLWithPath: "/usr/bin/which")
        whichProcess.arguments = ["python3"]
        let pipe = Pipe()
        whichProcess.standardOutput = pipe
        do {
            try whichProcess.run()
            whichProcess.waitUntilExit()
            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            if let output = String(data: data, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines),
               !output.isEmpty, FileManager.default.isExecutableFile(atPath: output) {
                return URL(fileURLWithPath: output)
            }
        } catch {}

        // 2. Check standard Homebrew & system locations
        let candidates = [
            "/opt/homebrew/bin/python3",
            "/usr/local/bin/python3",
            "/usr/bin/python3"
        ]
        for path in candidates {
            if FileManager.default.isExecutableFile(atPath: path) {
                return URL(fileURLWithPath: path)
            }
        }
        return URL(fileURLWithPath: "/usr/bin/python3")
    }

    func startServerIfNeeded() {
        // Terminate any stale orphaned server process on this port to ensure current bundle version runs
        let killProcess = Process()
        killProcess.executableURL = URL(fileURLWithPath: "/bin/sh")
        killProcess.arguments = ["-c", "lsof -ti :\(port) | xargs kill -9 2>/dev/null || true"]
        try? killProcess.run()
        killProcess.waitUntilExit()

        // Locate server.py (prefer bundled version in Resources)
        let appBundlePath = Bundle.main.bundlePath
        let possibleScriptPaths = [
            Bundle.main.resourcePath.map { $0 + "/server.py" } ?? "",
            (appBundlePath as NSString).deletingLastPathComponent + "/server.py",
            FileManager.default.currentDirectoryPath + "/server.py"
        ]

        var scriptPath: String?
        for path in possibleScriptPaths {
            if FileManager.default.fileExists(atPath: path) {
                scriptPath = path
                break
            }
        }

        guard let validScript = scriptPath else {
            print("Error: Could not locate server.py")
            return
        }

        let process = Process()
        let pyURL = findPythonExecutable()
        process.executableURL = pyURL
        process.arguments = [validScript, "\(port)"]
        process.currentDirectoryURL = URL(fileURLWithPath: (validScript as NSString).deletingLastPathComponent)

        do {
            try process.run()
            self.serverProcess = process
            print("Started backend server process (PID: \(process.processIdentifier))")
        } catch {
            print("Failed to run python server: \(error)")
        }

        // Wait up to 3 seconds for port to open
        let startTime = Date()
        while Date().timeIntervalSince(startTime) < 3.0 {
            if isServerAlive() {
                print("Backend server successfully responsive!")
                break
            }
            Thread.sleep(forTimeInterval: 0.1)
        }
    }

    func createWindow() {
        let width: CGFloat = 980
        let height: CGFloat = 740
        let screenSize = NSScreen.main?.visibleFrame.size ?? CGSize(width: 1200, height: 800)
        let rect = NSRect(
            x: (screenSize.width - width) / 2,
            y: (screenSize.height - height) / 2,
            width: width,
            height: height
        )

        window = NSWindow(
            contentRect: rect,
            styleMask: [.titled, .closable, .miniaturizable, .resizable, .fullSizeContentView],
            backing: .buffered,
            defer: false
        )

        window.title = "SoundCloud Downloader"
        window.titlebarAppearsTransparent = true
        window.titleVisibility = .hidden
        window.minSize = NSSize(width: 820, height: 600)
        window.backgroundColor = NSColor(red: 0.05, green: 0.05, blue: 0.06, alpha: 1.0)
        window.delegate = self

        // Configure WKWebView
        let config = WKWebViewConfiguration()
        config.preferences.setValue(true, forKey: "developerExtrasEnabled")

        webView = WKWebView(frame: window.contentView!.bounds, configuration: config)
        webView.autoresizingMask = [.width, .height]
        webView.setValue(false, forKey: "drawsBackground") // Transparent background
        window.contentView?.addSubview(webView)

        window.makeKeyAndOrderFront(nil)
        NSApplication.shared.activate(ignoringOtherApps: true)
    }

    func loadApp() {
        if let url = URL(string: serverURLString) {
            let request = URLRequest(url: url, cachePolicy: .reloadIgnoringLocalCacheData, timeoutInterval: 10.0)
            webView.load(request)
        }
    }

    func windowShouldClose(_ sender: NSWindow) -> Bool {
        NSApplication.shared.terminate(self)
        return true
    }

    func windowDidBecomeKey(_ notification: Notification) {
        webView?.evaluateJavaScript("if (typeof checkClipboardForSoundCloud === 'function') { checkClipboardForSoundCloud(); }", completionHandler: nil)
    }

    func applicationWillTerminate(_ notification: Notification) {
        if let proc = serverProcess, proc.isRunning {
            proc.terminate()
        }
    }
}

let app = NSApplication.shared
app.setActivationPolicy(.regular)
let delegate = AppDelegate()
app.delegate = delegate
app.run()
