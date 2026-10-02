param(
    [Parameter(Mandatory=$true)]
    [string]$SourceRoot
)

$ErrorActionPreference = "Stop"
$SourceRoot = [IO.Path]::GetFullPath($SourceRoot)

$pathsFile = Join-Path $SourceRoot "crates\zyntax-store\src\paths.rs"
$secretsFile = Join-Path $SourceRoot "crates\zyntax-store\src\secrets.rs"

foreach ($p in @($pathsFile,$secretsFile)) {
    if (-not (Test-Path -LiteralPath $p -PathType Leaf)) {
        throw "Expected upstream source file was not found: $p"
    }
}

function Replace-Exact {
    param(
        [string]$Text,
        [string]$Old,
        [string]$New,
        [string]$Label
    )

    if ($Text.Contains($New)) {
        Write-Host "$Label already patched." -ForegroundColor DarkGray
        return $Text
    }

    if (-not $Text.Contains($Old)) {
        throw "Could not apply '$Label': upstream source no longer matches the expected code. Fail-closed so portability is not silently broken."
    }

    Write-Host "Applying: $Label" -ForegroundColor Cyan
    return $Text.Replace($Old,$New)
}

# ---------------------------------------------------------------------
# 1. ZyntaxAI application-owned storage
#
# Upstream currently uses:
#   ProjectDirs::from("dev", "TheHolyOneZ", "ZyntaxAI")
#
# On Windows, directories::ProjectDirs therefore resolves into Roaming
# AppData. The upstream Paths abstraction already has rooted_at(), which is
# perfect for a portable build. Make resolve() use a root beside the EXE:
#
#   <portable folder>\Data\ZyntaxStore\
#       config\settings.json
#       data\history.db
#       data\logs\
#       data\secrets.key
#       data\secrets.enc
#
# This makes direct launching of ZyntaxAI-Portable.exe portable too; it does
# not depend on a CMD launcher setting an environment variable.
# ---------------------------------------------------------------------

$paths = Get-Content -LiteralPath $pathsFile -Raw

$paths = Replace-Exact `
    -Text $paths `
    -Label "remove ProjectDirs import" `
    -Old 'use directories::ProjectDirs;' `
    -New '// Portable build: system ProjectDirs are intentionally not used.'

$oldErrors = @'
    #[error("could not determine this platform's application directories")]
    NoHomeDirectory,
'@

$newErrors = @'
    #[error("could not determine the running executable path: {0}")]
    ExecutablePath(#[source] std::io::Error),
    #[error("the running executable path has no parent directory")]
    NoExecutableDirectory,
'@

$paths = Replace-Exact `
    -Text $paths `
    -Label "portable executable path errors" `
    -Old $oldErrors `
    -New $newErrors

$oldResolve = @'
    pub fn resolve() -> Result<Self, PathsError> {
        let dirs = ProjectDirs::from("dev", "TheHolyOneZ", "ZyntaxAI")
            .ok_or(PathsError::NoHomeDirectory)?;

        let paths = Self {
            config_dir: dirs.config_dir().to_path_buf(),
            data_dir: dirs.data_dir().to_path_buf(),
        };
        paths.ensure_dirs()?;
        Ok(paths)
    }
'@

$newResolve = @'
    pub fn resolve() -> Result<Self, PathsError> {
        let executable = std::env::current_exe().map_err(PathsError::ExecutablePath)?;
        let executable_dir = executable
            .parent()
            .ok_or(PathsError::NoExecutableDirectory)?;

        Self::rooted_at(executable_dir.join("Data").join("ZyntaxStore"))
    }
'@

$paths = Replace-Exact `
    -Text $paths `
    -Label "redirect ZyntaxAI store beside executable" `
    -Old $oldResolve `
    -New $newResolve

# Add an explicit regression test.
$oldTestEnd = @'
    #[test]
    fn file_paths_live_under_the_right_directories() {
        let temp = tempfile::tempdir().expect("temp dir");
        let paths = Paths::rooted_at(temp.path()).expect("resolve");

        assert!(paths.settings_file().starts_with(paths.config_dir()));
        assert!(paths.history_db().starts_with(paths.data_dir()));
        assert!(paths.fallback_key_file().starts_with(paths.data_dir()));
    }
}
'@

$newTestEnd = @'
    #[test]
    fn file_paths_live_under_the_right_directories() {
        let temp = tempfile::tempdir().expect("temp dir");
        let paths = Paths::rooted_at(temp.path()).expect("resolve");

        assert!(paths.settings_file().starts_with(paths.config_dir()));
        assert!(paths.history_db().starts_with(paths.data_dir()));
        assert!(paths.fallback_key_file().starts_with(paths.data_dir()));
    }

    #[test]
    fn portable_root_has_expected_layout() {
        let temp = tempfile::tempdir().expect("temp dir");
        let paths = Paths::rooted_at(temp.path().join("Data").join("ZyntaxStore"))
            .expect("portable paths");

        assert!(paths.settings_file().ends_with("Data/ZyntaxStore/config/settings.json"));
        assert!(paths.history_db().ends_with("Data/ZyntaxStore/data/history.db"));
        assert!(paths.logs_dir().ends_with("Data/ZyntaxStore/data/logs"));
        assert!(paths.fallback_key_file().ends_with("Data/ZyntaxStore/data/secrets.key"));
        assert!(paths.fallback_secrets_file().ends_with("Data/ZyntaxStore/data/secrets.enc"));
    }
}
'@

$paths = Replace-Exact `
    -Text $paths `
    -Label "add portable path regression test" `
    -Old $oldTestEnd `
    -New $newTestEnd

Set-Content -LiteralPath $pathsFile -Value $paths -Encoding UTF8

# ---------------------------------------------------------------------
# 2. API-key storage
#
# Upstream already has a complete AES-256-GCM encrypted-file backend and a
# file_backed constructor. The ordinary new() chooses OS keychain when
# available. For the portable fork, force EncryptedFile so Windows
# Credential Manager is not required.
#
# The generated random 32-byte key and ciphertext both live in
# Data\ZyntaxStore\data. This is portable. It protects against casual reading
# but, as upstream itself documents, anyone who obtains the whole portable
# folder obtains both the encrypted secrets and the decryption key.
# ---------------------------------------------------------------------

$secrets = Get-Content -LiteralPath $secretsFile -Raw

$oldDescription = @'
            SecretBackend::EncryptedFile => {
                "No system keychain was found, so keys are stored in an encrypted file in \
                 ZyntaxAI's data directory. This protects against casual reading and backups, \
                 but not against other software running as your user."
            }
'@

$newDescription = @'
            SecretBackend::EncryptedFile => {
                "Portable build: keys are stored in an AES-256-GCM encrypted file in \
                 ZyntaxAI's portable data directory. This protects against casual reading \
                 and backups, but anyone with the complete portable folder also has the key."
            }
'@

$secrets = Replace-Exact `
    -Text $secrets `
    -Label "portable secret backend description" `
    -Old $oldDescription `
    -New $newDescription

$oldNew = @'
    pub fn new(key_file: PathBuf, secrets_file: PathBuf) -> Self {
        Self {
            backend: if keychain_is_usable() {
                SecretBackend::Keychain
            } else {
                tracing::warn!("no OS keychain available; falling back to encrypted file storage");
                SecretBackend::EncryptedFile
            },
            key_file,
            secrets_file,
        }
    }
'@

$newNew = @'
    pub fn new(key_file: PathBuf, secrets_file: PathBuf) -> Self {
        tracing::info!("portable build: using encrypted-file API key storage");
        Self {
            backend: SecretBackend::EncryptedFile,
            key_file,
            secrets_file,
        }
    }
'@

$secrets = Replace-Exact `
    -Text $secrets `
    -Label "force encrypted-file API-key backend" `
    -Old $oldNew `
    -New $newNew

Set-Content -LiteralPath $secretsFile -Value $secrets -Encoding UTF8

# Record exactly what was changed for the output package.
$revision = (git -C $SourceRoot rev-parse HEAD).Trim()

$marker = [ordered]@{
    patch = "ZyntaxAI true-portable"
    patch_version = "1.0"
    upstream_revision = $revision
    applied_at = (Get-Date).ToString("o")
    store_root = "./Data/ZyntaxStore"
    settings = "./Data/ZyntaxStore/config/settings.json"
    history = "./Data/ZyntaxStore/data/history.db"
    logs = "./Data/ZyntaxStore/data/logs"
    secret_backend = "EncryptedFile"
    secrets_key = "./Data/ZyntaxStore/data/secrets.key"
    secrets_file = "./Data/ZyntaxStore/data/secrets.enc"
    host_appdata_store = $false
    windows_credential_manager = $false
}

$marker |
    ConvertTo-Json -Depth 6 |
    Set-Content -LiteralPath (Join-Path $SourceRoot ".zyntax-true-portable-patch.json") -Encoding UTF8

Write-Host ""
Write-Host "True-portable source patch applied successfully." -ForegroundColor Green
Write-Host "Application-owned state root: .\Data\ZyntaxStore" -ForegroundColor Green
Write-Host "API-key backend: encrypted portable files" -ForegroundColor Green
