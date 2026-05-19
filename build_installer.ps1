$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Release = Join-Path $Root 'release'
$AppDir = Join-Path $Release 'win-unpacked'
$OutDir = Join-Path $Release 'installer-build'
$ZipPath = Join-Path $OutDir 'payload.zip'
$StubCs = Join-Path $OutDir 'SetupStub.cs'
$StubExe = Join-Path $OutDir 'SetupStub.exe'
$SetupExe = Join-Path $Release 'YouTube Auto Pusher Setup ver1.exe'

if (!(Test-Path $AppDir)) { throw "Missing app dir: $AppDir" }
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
Remove-Item $ZipPath,$StubExe,$SetupExe -Force -ErrorAction SilentlyContinue
Compress-Archive -Path (Join-Path $AppDir '*') -DestinationPath $ZipPath -Force

@'
using System;
using System.IO;
using System.IO.Compression;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Windows.Forms;

class SetupStub {
    static readonly byte[] Marker = System.Text.Encoding.ASCII.GetBytes("<<YTAP_PAYLOAD_ZIP_V1>>");

    [STAThread]
    static int Main() {
        try {
            string exe = System.Reflection.Assembly.GetExecutingAssembly().Location;
            byte[] all = File.ReadAllBytes(exe);
            int idx = LastIndexOf(all, Marker);
            if (idx < 0) throw new Exception("Installer payload not found.");

            string defaultRoot = Directory.Exists(@"A:\\") ? @"A:\\ALL-TOOLS" : Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            Directory.CreateDirectory(defaultRoot);
            string installDir = PickInstallDir(Path.Combine(defaultRoot, "YouTube Auto Pusher"));
            if (String.IsNullOrWhiteSpace(installDir)) return 0;
            installDir = Path.GetFullPath(installDir);

            if (Directory.Exists(installDir)) {
                var confirm = MessageBox.Show(
                    "Thư mục đã tồn tại, setup sẽ ghi đè app trong thư mục này:\n\n" + installDir + "\n\nTiếp tục?",
                    "YouTube Auto Pusher Setup",
                    MessageBoxButtons.YesNo,
                    MessageBoxIcon.Question
                );
                if (confirm != DialogResult.Yes) return 0;
                Directory.Delete(installDir, true);
            }
            Directory.CreateDirectory(installDir);

            using (var ms = new MemoryStream(all, idx + Marker.Length, all.Length - idx - Marker.Length))
            using (var zip = new ZipArchive(ms, ZipArchiveMode.Read)) {
                zip.ExtractToDirectory(installDir);
            }

            string appExe = Path.Combine(installDir, "YouTube Auto Pusher.exe");
            CreateShortcut(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory), "YouTube Auto Pusher.lnk"), appExe, installDir);
            string startMenu = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.StartMenu), "Programs", "YouTube Auto Pusher.lnk");
            CreateShortcut(startMenu, appExe, installDir);

            Process.Start(new ProcessStartInfo(appExe) { WorkingDirectory = installDir, UseShellExecute = true });
            Console.WriteLine("YouTube Auto Pusher installed to: " + installDir);
            MessageBox.Show("Đã cài xong YouTube Auto Pusher tại:\n\n" + installDir, "YouTube Auto Pusher Setup", MessageBoxButtons.OK, MessageBoxIcon.Information);
            return 0;
        } catch (Exception ex) {
            Console.Error.WriteLine(ex.ToString());
            try { System.Windows.Forms.MessageBox.Show(ex.Message, "YouTube Auto Pusher Setup", System.Windows.Forms.MessageBoxButtons.OK, System.Windows.Forms.MessageBoxIcon.Error); } catch {}
            return 1;
        }
    }

    static string PickInstallDir(string defaultPath) {
        using (var dialog = new FolderBrowserDialog()) {
            dialog.Description = "Chọn thư mục cài đặt YouTube Auto Pusher";
            dialog.SelectedPath = defaultPath;
            dialog.ShowNewFolderButton = true;
            var result = dialog.ShowDialog();
            if (result != DialogResult.OK) return null;
            string selected = dialog.SelectedPath;
            if (Path.GetFileName(selected).Equals("YouTube Auto Pusher", StringComparison.OrdinalIgnoreCase)) return selected;
            return Path.Combine(selected, "YouTube Auto Pusher");
        }
    }

    static int LastIndexOf(byte[] src, byte[] pattern) {
        for (int i = src.Length - pattern.Length; i >= 0; i--) {
            bool ok = true;
            for (int j = 0; j < pattern.Length; j++) if (src[i + j] != pattern[j]) { ok = false; break; }
            if (ok) return i;
        }
        return -1;
    }

    static void CreateShortcut(string shortcutPath, string targetPath, string workingDir) {
        Type shellType = Type.GetTypeFromProgID("WScript.Shell");
        dynamic shell = Activator.CreateInstance(shellType);
        dynamic shortcut = shell.CreateShortcut(shortcutPath);
        shortcut.TargetPath = targetPath;
        shortcut.WorkingDirectory = workingDir;
        shortcut.IconLocation = targetPath;
        shortcut.Save();
    }
}
'@ | Set-Content -Path $StubCs -Encoding UTF8

$refs = @('System.IO.Compression.dll','System.IO.Compression.FileSystem.dll','System.Windows.Forms.dll','Microsoft.CSharp.dll')
Add-Type -OutputAssembly $StubExe -OutputType ConsoleApplication -ReferencedAssemblies $refs -Path $StubCs
[byte[]]$stub = [IO.File]::ReadAllBytes($StubExe)
[byte[]]$marker = [Text.Encoding]::ASCII.GetBytes('<<YTAP_PAYLOAD_ZIP_V1>>')
[byte[]]$zip = [IO.File]::ReadAllBytes($ZipPath)
$fs = [IO.File]::Create($SetupExe)
try {
  $fs.Write($stub, 0, $stub.Length)
  $fs.Write($marker, 0, $marker.Length)
  $fs.Write($zip, 0, $zip.Length)
} finally { $fs.Dispose() }
Write-Host "SETUP_EXE=$SetupExe"
Write-Host "SIZE_MB=$([math]::Round((Get-Item $SetupExe).Length / 1MB, 2))"
