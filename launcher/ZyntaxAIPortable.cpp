// ZyntaxAI Native Portable Launcher -- MIT license for this launcher source.
// Builds with Microsoft Visual C++ as a normal GUI-subsystem Windows executable.
// Persistent application state is redirected directly by the patched upstream app.
// TraceGuard is intentionally report-only: this launcher never removes host folders.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <shellapi.h>
#include <filesystem>
#include <fstream>
#include <string>
#include <vector>
#include <sstream>
#include <algorithm>
#include <cwctype>

namespace fs = std::filesystem;

static std::wstring quote(const std::wstring& arg) {
    if (arg.find_first_of(L" \t\"") == std::wstring::npos && !arg.empty()) return arg;
    std::wstring result = L"\"";
    size_t slashes = 0;
    for (wchar_t c : arg) {
        if (c == L'\\') { ++slashes; continue; }
        if (c == L'"') {
            result.append(slashes * 2 + 1, L'\\');
            result += L'"';
            slashes = 0;
            continue;
        }
        result.append(slashes, L'\\');
        slashes = 0;
        result += c;
    }
    result.append(slashes * 2, L'\\');
    result += L'"';
    return result;
}

static std::wstring variable(const wchar_t* name) {
    DWORD count = GetEnvironmentVariableW(name, nullptr, 0);
    if (!count) return {};
    std::wstring value(count, L'\0');
    DWORD written = GetEnvironmentVariableW(name, value.data(), count);
    if (!written || written >= count) return {};
    value.resize(written);
    return value;
}

static fs::path executable_path() {
    std::wstring buffer(32768, L'\0');
    DWORD size = GetModuleFileNameW(nullptr, buffer.data(), static_cast<DWORD>(buffer.size()));
    if (!size || size >= buffer.size()) return {};
    buffer.resize(size);
    return fs::path(buffer);
}

static void show_error(const std::wstring& message) {
    MessageBoxW(nullptr, message.c_str(), L"ZyntaxAI Portable", MB_OK | MB_ICONERROR);
}

struct TraceCandidate {
    std::wstring label;
    fs::path path;
    bool before;
};

static std::vector<TraceCandidate> get_candidates() {
    std::vector<TraceCandidate> out;
    const struct { const wchar_t* env; const wchar_t* name; } roots[] = {
        {L"APPDATA", L"Roaming"}, {L"LOCALAPPDATA", L"Local"},
        {L"PROGRAMDATA", L"ProgramData"}
    };
    for (const auto& root : roots) {
        auto value = variable(root.env);
        if (value.empty()) continue;
        // Exact target-specific candidates, never a parent-wide recursive scan.
        for (const auto& relative : { L"dev.theholyonez.zyntaxai", L"TheHolyOneZ\\ZyntaxAI" }) {
            fs::path p = fs::path(value) / relative;
            std::error_code ec;
            out.push_back({std::wstring(root.name) + L"/" + relative,
                           p, fs::exists(p, ec)});
        }
    }
    return out;
}

static std::string narrow_utf8(const std::wstring& wide) {
    if (wide.empty()) return {};
    int bytes = WideCharToMultiByte(CP_UTF8, 0, wide.c_str(),
            static_cast<int>(wide.size()), nullptr, 0, nullptr, nullptr);
    if (bytes <= 0) return {};
    std::string result(bytes, '\0');
    WideCharToMultiByte(CP_UTF8, 0, wide.c_str(), static_cast<int>(wide.size()),
            result.data(), bytes, nullptr, nullptr);
    return result;
}

static void write_report(const fs::path& data, const std::vector<TraceCandidate>& candidates,
                         const std::wstring& event, DWORD exit_code) {
    std::error_code ec;
    const fs::path dir = data / L"TraceGuard";
    fs::create_directories(dir, ec);
    if (ec) return;
    std::ofstream file(dir / L"Report.txt", std::ios::binary | std::ios::trunc);
    if (!file) return;
    file << "ZyntaxAI Native Portable - TraceGuard report-only monitor\r\n"
         << "Event: " << narrow_utf8(event) << "\r\nExit code: " << exit_code << "\r\n"
         << "App data redirection: ZYNTAX_DATA_DIR (source-level)\r\n"
         << "WebView2: Data/WebView2 (source-level patched window construction)\r\n"
         << "API credentials: encrypted file in portable Data (source-level)\r\n"
         << "No filesystem cleanup or registry cleanup was performed.\r\n"
         << "EXISTENCE IS NOT PROOF OF OWNERSHIP. Inspect the following candidates manually.\r\n";
    for (const auto& candidate : candidates) {
        std::error_code check_error;
        bool after = fs::exists(candidate.path, check_error);
        file << narrow_utf8(candidate.label) << " | before=" << (candidate.before ? "yes" : "no")
             << " | after=" << (after ? "yes" : "no")
             << " | path=" << narrow_utf8(candidate.path.wstring())
             << " | attribution=unverified | action=report-only\r\n";
    }
}


// Use only this app's HKCU Run value. No scheduler, service or elevation.
static bool recognized_portable_entry(std::wstring text) {
    std::transform(text.begin(), text.end(), text.begin(),
                   [](wchar_t c) { return static_cast<wchar_t>(towlower(c)); });
    return text.find(L"zyntaxaiportable.exe") != std::wstring::npos;
}

static void write_manager_status(const fs::path& data, const std::wstring& message) {
    std::error_code ec;
    auto dir = data / L"TraceGuard";
    fs::create_directories(dir, ec);
    if (ec) return;
    std::ofstream file(dir / L"ManagerStatus.txt", std::ios::binary | std::ios::trunc);
    if (file) file << narrow_utf8(message) << "\r\n";
}

static int manage_startup(const fs::path& launcher, const fs::path& data,
                          const std::wstring& action) {
    static constexpr wchar_t path[] = L"Software\\Microsoft\\Windows\\CurrentVersion\\Run";
    static constexpr wchar_t name[] = L"ZyntaxAIPortable";
    const std::wstring expected = L"\"" + launcher.wstring() + L"\" --minimized";
    HKEY key = nullptr;
    LONG result = ERROR_SUCCESS;
    const bool installing = action == L"--autostart-install";
    if (installing) {
        result = RegCreateKeyExW(HKEY_CURRENT_USER, path, 0, nullptr, 0,
                                 KEY_READ | KEY_SET_VALUE, nullptr, &key, nullptr);
    } else {
        result = RegOpenKeyExW(HKEY_CURRENT_USER, path, 0, KEY_READ | KEY_SET_VALUE, &key);
    }
    if (result == ERROR_FILE_NOT_FOUND && !installing) {
        write_manager_status(data, L"Autostart: disabled (no per-user Run key).");
        return 0;
    }
    if (result != ERROR_SUCCESS || !key) {
        write_manager_status(data, L"Cannot access per-user startup key; Windows error " + std::to_wstring(result));
        return 20;
    }
    DWORD type = 0;
    DWORD bytes = 0;
    LONG query = RegQueryValueExW(key, name, nullptr, &type, nullptr, &bytes);
    std::wstring old_value;
    if (query == ERROR_SUCCESS) {
        if ((type != REG_SZ && type != REG_EXPAND_SZ) || bytes < sizeof(wchar_t) || (bytes % sizeof(wchar_t))) {
            RegCloseKey(key);
            write_manager_status(data, L"Refusing to touch an unexpected or malformed startup registry value.");
            return 21;
        }
        old_value.assign(bytes / sizeof(wchar_t), L'\0');
        result = RegQueryValueExW(key, name, nullptr, &type,
                                  reinterpret_cast<LPBYTE>(old_value.data()), &bytes);
        if (result != ERROR_SUCCESS) {
            RegCloseKey(key);
            write_manager_status(data, L"Could not read existing startup entry.");
            return 22;
        }
        while (!old_value.empty() && old_value.back() == L'\0') old_value.pop_back();
    } else if (query != ERROR_FILE_NOT_FOUND) {
        RegCloseKey(key);
        write_manager_status(data, L"Could not inspect existing startup entry.");
        return 23;
    }
    if (!old_value.empty() && !recognized_portable_entry(old_value)) {
        RegCloseKey(key);
        write_manager_status(data, L"Refusing to overwrite/delete another application's entry with this value name.");
        return 24;
    }
    if (action == L"--autostart-status") {
        if (old_value.empty()) write_manager_status(data, L"Autostart: disabled.");
        else if (_wcsicmp(old_value.c_str(), expected.c_str()) == 0)
            write_manager_status(data, L"Autostart: enabled; correct current path; minimized to system tray.");
        else write_manager_status(data, L"Autostart: stale or mismatched path; choose Install/Repair.");
        RegCloseKey(key);
        return 0;
    }
    if (installing) {
        result = RegSetValueExW(key, name, 0, REG_SZ,
                reinterpret_cast<const BYTE*>(expected.c_str()),
                static_cast<DWORD>((expected.size() + 1) * sizeof(wchar_t)));
    } else if (action == L"--autostart-remove") {
        result = old_value.empty() ? ERROR_SUCCESS : RegDeleteValueW(key, name);
    } else result = ERROR_INVALID_PARAMETER;
    RegCloseKey(key);
    if (result != ERROR_SUCCESS) {
        write_manager_status(data, L"Registry operation failed. Win32 error " + std::to_wstring(result));
        return 25;
    }
    write_manager_status(data, installing ? L"Autostart installed/repaired to current portable EXE with --minimized."
                                          : L"Autostart removed (only our managed value).");
    return 0;
}

int WINAPI wWinMain(HINSTANCE, HINSTANCE, PWSTR, int) {
    const fs::path launcher = executable_path();
    if (launcher.empty()) { show_error(L"Cannot locate the portable launcher."); return 2; }
    const fs::path root = launcher.parent_path();
    const fs::path app = root / L"App" / L"ZyntaxAI" / L"zyntax.exe";
    const fs::path data = root / L"Data";
    const fs::path zyntax_data = data / L"ZyntaxAI";
    const fs::path webview_data = data / L"WebView2";
    std::error_code ec;
    if (!fs::is_regular_file(app, ec)) {
        show_error(L"Missing App\\ZyntaxAI\\zyntax.exe. Re-extract a complete release ZIP.");
        return 3;
    }
    fs::create_directories(zyntax_data, ec);
    if (ec) { show_error(L"Cannot create Data\\ZyntaxAI. Check portable drive permissions."); return 4; }
    fs::create_directories(webview_data, ec);
    if (ec) { show_error(L"Cannot create Data\\WebView2. Check portable drive permissions."); return 5; }
    // Test write permission without touching any existing file or host user profile.
    const auto probe = data / L".zyntax-write-probe";
    {
        std::ofstream test(probe, std::ios::binary | std::ios::trunc);
        if (!test) { show_error(L"Portable Data is not writable."); return 6; }
        test << "ok";
        if (!test.good()) { show_error(L"Portable Data write test failed."); return 7; }
    }
    fs::remove(probe, ec);
    int argc = 0;
    LPWSTR* argv = CommandLineToArgvW(GetCommandLineW(), &argc);
    if (!argv) { show_error(L"Cannot read command-line arguments."); return 8; }
    if (argc == 2 && (std::wstring(argv[1]) == L"--autostart-install" ||
                      std::wstring(argv[1]) == L"--autostart-remove" ||
                      std::wstring(argv[1]) == L"--autostart-status")) {
        std::wstring action(argv[1]);
        LocalFree(argv);
        return manage_startup(launcher, data, action);
    }
    if (argc == 2 && std::wstring(argv[1]) == L"--self-test") {
        LocalFree(argv);
        write_report(data, get_candidates(), L"self-test passed; application was not launched", 0);
        return 0;
    }
    const auto traces = get_candidates();
    if (!SetEnvironmentVariableW(L"ZYNTAX_DATA_DIR", zyntax_data.c_str()) ||
        !SetEnvironmentVariableW(L"ZYNTAX_PORTABLE_MODE", L"1") ||
        !SetEnvironmentVariableW(L"ZYNTAX_PORTABLE_WEBVIEW_DIR", webview_data.c_str())) {
        LocalFree(argv);
        show_error(L"Cannot configure portable data environment.");
        return 9;
    }
    std::wstring command = quote(app.wstring());
    for (int i = 1; i < argc; ++i) { command += L" "; command += quote(argv[i]); }
    LocalFree(argv);
    std::vector<wchar_t> mutable_command(command.begin(), command.end());
    mutable_command.push_back(L'\0');
    STARTUPINFOW si{};
    si.cb = sizeof(si);
    PROCESS_INFORMATION pi{};
    const std::wstring cwd = app.parent_path().wstring();
    if (!CreateProcessW(app.c_str(), mutable_command.data(), nullptr, nullptr,
                        FALSE, 0, nullptr, cwd.c_str(), &si, &pi)) {
        DWORD error = GetLastError();
        write_report(data, traces, L"launch failed", error);
        show_error(L"Could not start ZyntaxAI. Win32 error " + std::to_wstring(error) +
                   L". Check Data\\TraceGuard\\Report.txt.");
        return 10;
    }
    CloseHandle(pi.hThread);
    WaitForSingleObject(pi.hProcess, INFINITE);
    DWORD result = 1;
    GetExitCodeProcess(pi.hProcess, &result);
    CloseHandle(pi.hProcess);
    write_report(data, traces, L"application process exited", result);
    return static_cast<int>(result);
}
