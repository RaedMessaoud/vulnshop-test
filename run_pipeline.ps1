# ============================================================================
# DevSecOps Pipeline - Local Execution Script (Windows PowerShell)
# ============================================================================
# Usage: .\run_pipeline.ps1
# This script runs the complete DevSecOps pipeline locally without GitHub Actions
# ============================================================================

# Configuration
$WorkspaceDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonVersion = "3.11"
$AppUrl = "http://localhost:5000"
$Timeout = 10

# Colors
$Colors = @{
    Red = [ConsoleColor]::Red
    Green = [ConsoleColor]::Green
    Yellow = [ConsoleColor]::Yellow
    Blue = [ConsoleColor]::Cyan
    Bold = ""
}

function Write-ColoredOutput {
    param(
        [string]$Message,
        [ConsoleColor]$ForegroundColor = [ConsoleColor]::White,
        [bool]$Bold = $false
    )
    
    if ($Bold) {
        Write-Host $Message -ForegroundColor $ForegroundColor -BackgroundColor Black
    } else {
        Write-Host $Message -ForegroundColor $ForegroundColor
    }
}

function Write-Section {
    param([string]$Title)
    Write-Host ""
    Write-ColoredOutput "━━ $Title ━━" -ForegroundColor Cyan
    Write-Host ""
}

# ============================================================================
# Header
# ============================================================================
Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   🔒 DevSecOps Pipeline - Local Execution (Windows)    ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ============================================================================
# Phase 0: Prerequisites Check
# ============================================================================
Write-Section "Phase 0: Prerequisites Check"

# Check Python
try {
    $PythonPath = (Get-Command python -ErrorAction Stop).Path
    Write-ColoredOutput "✅ Python found: $PythonPath" -ForegroundColor Green
} catch {
    Write-ColoredOutput "❌ Python not found. Please install Python 3.11+" -ForegroundColor Red
    exit 1
}

# Check pip
try {
    $PipVersion = python -m pip --version 2>$null
    Write-ColoredOutput "✅ pip is available" -ForegroundColor Green
} catch {
    Write-ColoredOutput "❌ pip not found" -ForegroundColor Red
    exit 1
}

# Check and install dependencies
Write-Host "📦 Checking Python packages..."
$Packages = @("bandit", "safety", "pytest", "requests", "flask")

foreach ($pkg in $Packages) {
    try {
        python -c "import $pkg" 2>$null
        Write-ColoredOutput "  ✅ $pkg" -ForegroundColor Green
    } catch {
        Write-ColoredOutput "  ⏳ Installing $pkg..." -ForegroundColor Yellow
        python -m pip install -q $pkg 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-ColoredOutput "  ✅ $pkg installed" -ForegroundColor Green
        } else {
            Write-ColoredOutput "  ❌ Failed to install $pkg" -ForegroundColor Red
        }
    }
}

# ============================================================================
# Phase 1: SAST - Bandit Code Analysis
# ============================================================================
Write-Section "Phase 1: SAST - Bandit Analysis"

if (Test-Path "shop_vuln.py") {
    Write-Host "🔍 Scanning Python code with Bandit..."
    
    try {
        bandit -r shop_vuln.py -f json -o bandit-report.json 2>$null
        
        if (Test-Path "bandit-report.json") {
            $BanitContent = Get-Content "bandit-report.json" | ConvertFrom-Json
            $IssueCount = ($BanitContent.results | Measure-Object).Count
            Write-ColoredOutput "✅ Bandit completed - Found $IssueCount potential issues" -ForegroundColor Green
        } else {
            Write-ColoredOutput "❌ Bandit report not generated" -ForegroundColor Red
        }
    } catch {
        Write-ColoredOutput "⚠️  Error running Bandit: $_" -ForegroundColor Yellow
    }
} else {
    Write-ColoredOutput "❌ shop_vuln.py not found" -ForegroundColor Red
}

# ============================================================================
# Phase 2: SCA - Safety Dependency Check
# ============================================================================
Write-Section "Phase 2: SCA - Dependency Check"

if (Test-Path "requirements.txt") {
    Write-Host "📦 Checking dependencies with Safety..."
    
    try {
        safety check -r requirements.txt --json | Out-File -FilePath safety-report.json -Encoding UTF8 2>$null
        safety check -r requirements.txt | Out-File -FilePath safety-output.txt -Encoding UTF8 2>$null
        
        Write-ColoredOutput "✅ Safety check completed" -ForegroundColor Green
    } catch {
        Write-ColoredOutput "⚠️  Error running Safety: $_" -ForegroundColor Yellow
    }
} else {
    Write-ColoredOutput "❌ requirements.txt not found" -ForegroundColor Red
}

# ============================================================================
# Phase 3: DAST - Dynamic Application Security Testing
# ============================================================================
Write-Section "Phase 3: DAST - Dynamic Testing"

# Start app
Write-Host "🚀 Starting Flask application..."

# Kill any existing process on port 5000
$ExistingProcess = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*shop_vuln*" }
if ($ExistingProcess) {
    Write-Host "⚠️  Killing existing Flask process..."
    $ExistingProcess | Stop-Process -Force
    Start-Sleep -Seconds 1
}

# Start new process
$AppProcess = Start-Process -FilePath python -ArgumentList "shop_vuln.py" -PassThru -NoNewWindow -RedirectStandardError "app-error.log" -RedirectStandardOutput "app.log"
Write-Host "  PID: $($AppProcess.Id)"

# Wait for app to be ready
$Retry = 0
$MaxRetries = 30
$AppReady = $false

while ($Retry -lt $MaxRetries) {
    try {
        $TestConnection = Invoke-WebRequest -Uri "$AppUrl/" -Method Get -TimeoutSec 5 -ErrorAction SilentlyContinue
        if ($TestConnection.StatusCode -eq 200) {
            Write-ColoredOutput "✅ Application is responding on $AppUrl" -ForegroundColor Green
            $AppReady = $true
            break
        }
    } catch {
        # Connection failed, app not ready yet
    }
    
    $Retry++
    Write-Host "  ⏳ Waiting for app... ($Retry/$MaxRetries)"
    Start-Sleep -Seconds 1
}

if (-not $AppReady) {
    Write-ColoredOutput "❌ Application failed to start" -ForegroundColor Red
    Get-Content "app.log" | Write-Host
    exit 1
}

# Run pytest DAST
Write-Host "🧪 Running pytest DAST tests..."

if (Test-Path ".github/workflows/test_security.py") {
    try {
        python -m pytest .github/workflows/test_security.py -v --tb=short | Tee-Object -FilePath pytest-output.log
        Write-ColoredOutput "✅ Pytest tests completed" -ForegroundColor Green
    } catch {
        Write-ColoredOutput "⚠️  Error running pytest: $_" -ForegroundColor Yellow
    }
} else {
    Write-ColoredOutput "❌ test_security.py not found" -ForegroundColor Red
}

# Run advanced DAST
Write-Host "🔐 Running advanced DAST tests..."

$DastResults = @()

# Test 1: Login SQL Injection
Write-Host "  Test 1: SQL Injection - Login"
try {
    $LoginResponse = Invoke-WebRequest -Uri "$AppUrl/login" -Method Post `
        -Body "username=admin&password=%27%20OR%20%271%27%3D%271" `
        -TimeoutSec 10 -UseBasicParsing -ErrorAction SilentlyContinue
    
    if ($LoginResponse.Content -match "(profil|dashboard)" -or $LoginResponse.StatusCode -eq 200) {
        Write-Host "  ❌ VULNERABILITY: SQL Injection in login"
        $DastResults += "❌ VULNERABILITY: SQL Injection in login"
    } else {
        Write-Host "  ✅ Login SQL injection protection OK"
        $DastResults += "✅ Login SQL injection protection OK"
    }
} catch {
    Write-Host "  ⚠️  Could not connect to login endpoint"
}

# Test 2: Profile Protection
Write-Host "  Test 2: Authentication - Profile"
try {
    $ProfileResponse = Invoke-WebRequest -Uri "$AppUrl/profile" -Method Get `
        -TimeoutSec 10 -UseBasicParsing -MaximumRedirection 0 -ErrorAction SilentlyContinue
    
    $HttpCode = $ProfileResponse.StatusCode
    Write-Host "  ✅ Profile response: HTTP $HttpCode"
    $DastResults += "✅ Profile check completed (HTTP $HttpCode)"
} catch {
    if ($_.Exception.Response) {
        $HttpCode = $_.Exception.Response.StatusCode
        Write-Host "  ✅ Profile protection OK (HTTP $HttpCode)"
        $DastResults += "✅ Profile protection OK (HTTP $HttpCode)"
    } else {
        Write-Host "  ⚠️  Could not reach profile endpoint"
    }
}

# Save DAST results
$DastResults | Out-File -FilePath dast-results.txt -Encoding UTF8

Write-ColoredOutput "✅ Advanced DAST tests completed" -ForegroundColor Green

# Stop app
Write-Host "`n🛑 Stopping Flask application..."
try {
    $AppProcess | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
}
catch {
    Write-Host "⚠️  Could not stop app process gracefully"
}

# ============================================================================
# Phase 4: Generate Security Report
# ============================================================================
Write-Section "Phase 4: Security Report Generation"

Write-Host "📊 Generating comprehensive security report..."

if (Test-Path "generate_report.py") {
    try {
        python generate_report.py 2>$null
        
        if (Test-Path "SECURITY_REPORT.md") {
            Write-ColoredOutput "✅ Security report generated: SECURITY_REPORT.md" -ForegroundColor Green
        } else {
            Write-ColoredOutput "⚠️  Report file not created" -ForegroundColor Yellow
        }
    } catch {
        Write-ColoredOutput "❌ Error generating report: $_" -ForegroundColor Red
    }
} else {
    Write-ColoredOutput "❌ generate_report.py not found" -ForegroundColor Red
}

# ============================================================================
# Phase 5: Display Results
# ============================================================================
Write-Section "Phase 5: Results Summary"

if (Test-Path "SECURITY_REPORT.md") {
    Write-Host ""
    Write-Host "════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "📋 SECURITY REPORT" -ForegroundColor Cyan -NoNewline
    Write-Host ""
    Write-Host "════════════════════════════════════════════════════════" -ForegroundColor Cyan
    
    Get-Content "SECURITY_REPORT.md" | Write-Host
    
    Write-Host "════════════════════════════════════════════════════════" -ForegroundColor Cyan
}

# ============================================================================
# Phase 6: Artifact Summary
# ============================================================================
Write-Section "Phase 6: Artifacts Generated"

$Artifacts = @(
    "bandit-report.json",
    "safety-report.json",
    "safety-output.txt",
    "dast-results.txt",
    "pytest-output.log",
    "SECURITY_REPORT.md",
    "app.log"
)

$FilesGenerated = 0
foreach ($file in $Artifacts) {
    if (Test-Path $file) {
        $Size = (Get-Item $file).Length
        $SizeKB = [math]::Round($Size / 1KB, 2)
        Write-ColoredOutput "✅ $file ($($SizeKB) KB)" -ForegroundColor Green
        $FilesGenerated++
    }
}

Write-Host ""
Write-Host "Total: $FilesGenerated artifacts generated" -ForegroundColor Cyan

# ============================================================================
# Phase 7: Summary & Next Steps
# ============================================================================
Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   ✅ Pipeline Execution Completed                      ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════╝" -ForegroundColor Cyan

Write-Host ""
Write-Host "📊 Next Steps:" -ForegroundColor Green
Write-Host "  1. Review the SECURITY_REPORT.md file"
Write-Host "  2. Check individual report files for details"
Write-Host "  3. Fix identified vulnerabilities in shop_vuln.py"
Write-Host "  4. Commit and push to GitHub to trigger CI/CD pipeline"
Write-Host ""

Write-Host "📝 To push to GitHub:" -ForegroundColor Green
Write-Host "  git add ."
Write-Host "  git commit -m 'DevSecOps pipeline implementation'"
Write-Host "  git push origin main  # or your branch"
Write-Host ""

Write-Host "💡 Tips:" -ForegroundColor Green
Write-Host "  - Review Bandit findings in: bandit-report.json"
Write-Host "  - Check dependencies in: safety-output.txt"
Write-Host "  - See DAST results in: dast-results.txt"
Write-Host "  - Full report in: SECURITY_REPORT.md"
Write-Host ""

Write-Host "📖 For more information, see: DEVSECOPS_GUIDE.md" -ForegroundColor Yellow
Write-Host ""

exit 0
