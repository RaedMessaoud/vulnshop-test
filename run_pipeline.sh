#!/bin/bash

# ============================================================================
# DevSecOps Pipeline - Local Execution Script
# ============================================================================
# Usage: bash run_pipeline.sh
# This script runs the complete DevSecOps pipeline locally without GitHub Actions
# ============================================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Configuration
WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_VERSION="3.11"
APP_URL="http://localhost:5000"
TIMEOUT=10

# ============================================================================
echo -e "${BLUE}${BOLD}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}${BOLD}║   🔒 DevSecOps Pipeline - Local Execution${NC}${BLUE}${BOLD}           ║${NC}"
echo -e "${BLUE}${BOLD}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# ============================================================================
# Phase 0: Prerequisites Check
# ============================================================================
echo -e "${YELLOW}━━ Phase 0: Prerequisites Check ━━${NC}"

check_python() {
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ Python not found${NC}"
        exit 1
    fi
    PYTHON_PATH=$(which python3)
    echo -e "${GREEN}✅ Python found: $PYTHON_PATH${NC}"
}

check_pip() {
    if ! python3 -m pip --version &> /dev/null; then
        echo -e "${RED}❌ pip not found${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ pip is available${NC}"
}

check_dependencies() {
    echo -e "\n📦 Checking Python packages..."
    
    PACKAGES=("bandit" "safety" "pytest" "requests" "flask")
    for pkg in "${PACKAGES[@]}"; do
        if python3 -c "import $pkg" 2>/dev/null; then
            echo -e "${GREEN}  ✅ $pkg${NC}"
        else
            echo -e "${YELLOW}  ⏳ $pkg needs installation${NC}"
            python3 -m pip install -q "$pkg" 2>/dev/null || echo -e "${RED}  ❌ Failed to install $pkg${NC}"
        fi
    done
}

check_python
check_pip
check_dependencies

# ============================================================================
# Phase 1: SAST - Bandit Code Analysis
# ============================================================================
echo -e "\n${YELLOW}━━ Phase 1: SAST - Bandit Analysis ━━${NC}"

run_bandit() {
    echo "🔍 Scanning Python code with Bandit..."
    
    if [ -f "shop_vuln.py" ]; then
        bandit -r shop_vuln.py -f json -o bandit-report.json 2>/dev/null || true
        
        if [ -f "bandit-report.json" ]; then
            ISSUES=$(python3 -c "import json; data=json.load(open('bandit-report.json')); print(len(data.get('results', [])))")
            echo -e "${GREEN}✅ Bandit completed - Found $ISSUES potential issues${NC}"
        else
            echo -e "${RED}❌ Bandit report not generated${NC}"
        fi
    else
        echo -e "${RED}❌ shop_vuln.py not found${NC}"
        return 1
    fi
}

run_bandit

# ============================================================================
# Phase 2: SCA - Safety Dependency Check
# ============================================================================
echo -e "\n${YELLOW}━━ Phase 2: SCA - Dependency Check ━━${NC}"

run_safety() {
    echo "📦 Checking dependencies with Safety..."
    
    if [ -f "requirements.txt" ]; then
        safety check -r requirements.txt --json > safety-report.json 2>&1 || true
        safety check -r requirements.txt > safety-output.txt 2>&1 || true
        
        if [ -f "safety-output.txt" ]; then
            VULN_COUNT=$(grep -c "CVE\|Vulnerability" safety-output.txt || echo "0")
            echo -e "${GREEN}✅ Safety check completed${NC}"
        else
            echo -e "${YELLOW}⚠️  Safety report not found${NC}"
        fi
    else
        echo -e "${RED}❌ requirements.txt not found${NC}"
        return 1
    fi
}

run_safety

# ============================================================================
# Phase 3: DAST - Dynamic Application Security Testing
# ============================================================================
echo -e "\n${YELLOW}━━ Phase 3: DAST - Dynamic Testing ━━${NC}"

start_app() {
    echo "🚀 Starting Flask application..."
    
    # Check if port 5000 is already in use
    if lsof -Pi :5000 -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Port 5000 already in use${NC}"
        echo "Killing existing process..."
        pkill -f "python.*shop_vuln" || true
        sleep 1
    fi
    
    # Start the app in background
    python3 shop_vuln.py > app.log 2>&1 &
    APP_PID=$!
    echo "  PID: $APP_PID"
    
    # Wait for app to be ready
    RETRY=0
    MAX_RETRIES=30
    while [ $RETRY -lt $MAX_RETRIES ]; do
        if curl -s "$APP_URL/" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Application is responding on $APP_URL${NC}"
            echo "$APP_PID" > app.pid
            return 0
        fi
        RETRY=$((RETRY + 1))
        echo "  ⏳ Waiting for app... ($RETRY/$MAX_RETRIES)"
        sleep 1
    done
    
    echo -e "${RED}❌ Application failed to start${NC}"
    cat app.log
    return 1
}

stop_app() {
    if [ -f app.pid ]; then
        APP_PID=$(cat app.pid)
        if kill -0 $APP_PID 2>/dev/null; then
            echo "🛑 Stopping Flask application (PID: $APP_PID)..."
            kill $APP_PID 2>/dev/null || true
            sleep 1
            rm app.pid
        fi
    fi
    pkill -f "python.*shop_vuln" 2>/dev/null || true
}

run_pytest_dast() {
    echo "🧪 Running pytest DAST tests..."
    
    if [ -f ".github/workflows/test_security.py" ]; then
        python3 -m pytest .github/workflows/test_security.py -v --tb=short 2>&1 | tee pytest-output.log || true
        echo -e "${GREEN}✅ Pytest tests completed${NC}"
    else
        echo -e "${RED}❌ test_security.py not found${NC}"
    fi
}

run_advanced_dast() {
    echo "🔐 Running advanced DAST tests..."
    
    DAST_RESULTS="dast-results.txt"
    > "$DAST_RESULTS"
    
    # Test 1: Login SQL Injection
    echo "  Test 1: SQL Injection - Login"
    LOGIN_RESPONSE=$(curl -s -X POST "$APP_URL/login" \
      -d "username=admin&password=%27%20OR%20%271%27%3D%271" \
      --connect-timeout 5 --max-time 10 2>/dev/null || echo "")
    
    if echo "$LOGIN_RESPONSE" | grep -qi "profil\|dashboard"; then
        echo "  ❌ VULNERABILITY: SQL Injection in login" | tee -a "$DAST_RESULTS"
    else
        echo "  ✅ Login SQL injection protection OK" | tee -a "$DAST_RESULTS"
    fi
    
    # Test 2: UNION Injection
    echo "  Test 2: SQL Injection - UNION"
    UNION_RESPONSE=$(curl -s "$APP_URL/search?q=%27%20UNION%20SELECT%201,2,3,4--" \
      --connect-timeout 5 --max-time 10 2>/dev/null || echo "")
    
    if [ ! -z "$UNION_RESPONSE" ]; then
        echo "  ✅ Search UNION test completed" | tee -a "$DAST_RESULTS"
    else
        echo "  ⚠️  No response to UNION test" | tee -a "$DAST_RESULTS"
    fi
    
    # Test 3: Profile Protection
    echo "  Test 3: Authentication - Profile"
    PROFILE_RESPONSE=$(curl -s -w "HTTP_CODE:%{http_code}" "$APP_URL/profile" \
      --connect-timeout 5 --max-time 10 2>/dev/null || echo "")
    
    HTTP_CODE=$(echo "$PROFILE_RESPONSE" | grep -o "HTTP_CODE:[0-9]*" | cut -d: -f2)
    if [ "$HTTP_CODE" = "302" ] || [ "$HTTP_CODE" = "301" ] || [ "$HTTP_CODE" = "401" ]; then
        echo "  ✅ Profile protection OK (HTTP $HTTP_CODE)" | tee -a "$DAST_RESULTS"
    else
        echo "  ⚠️  Profile response: HTTP $HTTP_CODE" | tee -a "$DAST_RESULTS"
    fi
    
    echo -e "${GREEN}✅ Advanced DAST tests completed${NC}"
}

# Actually run DAST
if ! start_app; then
    echo -e "${RED}❌ Cannot start app, skipping DAST tests${NC}"
else
    run_pytest_dast
    run_advanced_dast
    stop_app
fi

# ============================================================================
# Phase 4: Generate Security Report
# ============================================================================
echo -e "\n${YELLOW}━━ Phase 4: Security Report Generation ━━${NC}"

generate_report() {
    echo "📊 Generating comprehensive security report..."
    
    if [ -f "generate_report.py" ]; then
        python3 generate_report.py 2>&1 || true
        
        if [ -f "SECURITY_REPORT.md" ]; then
            echo -e "${GREEN}✅ Security report generated: SECURITY_REPORT.md${NC}"
            return 0
        else
            echo -e "${YELLOW}⚠️  Report file not created${NC}"
            return 1
        fi
    else
        echo -e "${RED}❌ generate_report.py not found${NC}"
        return 1
    fi
}

generate_report

# ============================================================================
# Phase 5: Display Results
# ============================================================================
echo -e "\n${YELLOW}━━ Phase 5: Results Summary ━━${NC}"

display_report() {
    if [ -f "SECURITY_REPORT.md" ]; then
        echo -e "\n${BLUE}${BOLD}════════════════════════════════════════════════════════${NC}"
        echo -e "${BLUE}${BOLD}📋 SECURITY REPORT${NC}"
        echo -e "${BLUE}${BOLD}════════════════════════════════════════════════════════${NC}"
        cat SECURITY_REPORT.md
        echo -e "${BLUE}${BOLD}════════════════════════════════════════════════════════${NC}"
        echo ""
    fi
}

display_report

# ============================================================================
# Phase 6: Artifact Summary
# ============================================================================
echo -e "${YELLOW}━━ Phase 6: Artifacts Generated ━━${NC}"
echo ""

FILES_GENERATED=0
for file in bandit-report.json safety-report.json safety-output.txt dast-results.txt pytest-output.log SECURITY_REPORT.md app.log; do
    if [ -f "$file" ]; then
        SIZE=$(du -h "$file" | cut -f1)
        echo -e "${GREEN}✅ $file${NC} ($SIZE)"
        FILES_GENERATED=$((FILES_GENERATED + 1))
    fi
done

echo ""
echo -e "${BLUE}Total: $FILES_GENERATED artifacts generated${NC}"

# ============================================================================
# Phase 7: Summary & Next Steps
# ============================================================================
echo -e "\n${BLUE}${BOLD}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}${BOLD}║   ✅ Pipeline Execution Completed${NC}${BLUE}${BOLD}                ║${NC}"
echo -e "${BLUE}${BOLD}╚════════════════════════════════════════════════════════╝${NC}"

echo ""
echo -e "${GREEN}📊 Next Steps:${NC}"
echo "  1. Review the SECURITY_REPORT.md file"
echo "  2. Check individual report files for details"
echo "  3. Fix identified vulnerabilities in shop_vuln.py"
echo "  4. Commit and push to GitHub to trigger CI/CD pipeline"
echo ""
echo -e "${GREEN}📝 To push to GitHub:${NC}"
echo "  git add ."
echo "  git commit -m 'DevSecOps pipeline implementation'"
echo "  git push origin main  # or your branch"
echo ""
echo -e "${GREEN}💡 Tips:${NC}"
echo "  - Review Bandit findings in: bandit-report.json"
echo "  - Check dependencies in: safety-output.txt"
echo "  - See DAST results in: dast-results.txt"
echo "  - Full report in: SECURITY_REPORT.md"
echo ""
echo -e "${YELLOW}📖 For more information, see: DEVSECOPS_GUIDE.md${NC}"
echo ""

exit 0
