#!/usr/bin/env bash
# ⚔️ NAKAMA PRE-PUSH HOOK — JANGAN SKIP! ⚔️
# Runs before every `git push`. Blocks push if checks fail.
# Install: ln -sf ../../scripts/pre-push.sh .git/hooks/pre-push
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'
PASS=0
FAIL=0

echo ""
echo "⚔️  NAKAMA PRE-PUSH CHECK — verifying before push..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── 1. BACKEND IMPORT CHECK ──────────────────────────────────
echo ""
echo "📦 Check 1: Backend import..."
if [ -d "backend" ]; then
    if OFFLINE_MODE=1 PYTHONPATH=backend python3 -c "
import sys
sys.path.insert(0, 'backend')
from app.main import app
print(f'  ✅ App v{app.version} OK, {len(app.routes)} routes')
" 2>&1 | grep -v 'fastapi_mcp\|INFO'; then
        echo -e "${GREEN}  ✅ PASS${NC}: Backend imports OK"
        PASS=$((PASS + 1))
    else
        echo -e "${RED}  ❌ FAIL${NC}: Backend import failed — fix before pushing!"
        FAIL=$((FAIL + 1))
    fi
else
    echo -e "${YELLOW}  ⚠️  SKIP${NC}: No backend directory"
fi

# ── 2. FRONTEND BUILD CHECK ──────────────────────────────────
echo ""
echo "📦 Check 2: Frontend build..."
if [ -d "frontend" ]; then
    if (cd frontend && timeout 120 npm run build > /tmp/nakama-build.log 2>&1); then
        echo -e "${GREEN}  ✅ PASS${NC}: Frontend build OK"
        PASS=$((PASS + 1))
    else
        echo -e "${RED}  ❌ FAIL${NC}: Frontend build failed — check /tmp/nakama-build.log"
        tail -20 /tmp/nakama-build.log
        FAIL=$((FAIL + 1))
    fi
else
    echo -e "${YELLOW}  ⚠️  SKIP${NC}: No frontend directory"
fi

# ── 3. DEAD COMPONENT CHECK ──────────────────────────────────
echo ""
echo "📦 Check 3: Dead components..."
if [ -d "frontend/components" ]; then
    DEAD=0
    for f in frontend/components/*.tsx; do
        name=$(basename "$f" .tsx)
        count=$(grep -rl "$name" frontend/app/*.tsx frontend/app/**/*.tsx 2>/dev/null | wc -l)
        if [ "$count" -eq 0 ]; then
            echo -e "  ${YELLOW}⚠️  DEAD${NC}: components/$name.tsx — not imported in any page"
            DEAD=$((DEAD + 1))
        fi
    done
    if [ "$DEAD" -eq 0 ]; then
        echo -e "${GREEN}  ✅ PASS${NC}: No dead components"
        PASS=$((PASS + 1))
    else
        echo -e "${YELLOW}  ⚠️  WARN${NC}: $DEAD dead component(s) — review before pushing"
        # Warning only, don't block
        PASS=$((PASS + 1))
    fi
fi

# ── 4. DUPLICATE ROUTE CHECK ──────────────────────────────────
echo ""
echo "📦 Check 4: Duplicate frontend routes..."
if [ -d "frontend/app" ]; then
    DUPS=$(find frontend/app -name 'page.tsx' | sed 's|/page.tsx||' | sed 's|/(protected)||g' | sort | uniq -d)
    if [ -z "$DUPS" ]; then
        echo -e "${GREEN}  ✅ PASS${NC}: No duplicate routes"
        PASS=$((PASS + 1))
    else
        echo -e "${RED}  ❌ FAIL${NC}: Duplicate routes found:"
        echo "$DUPS"
        FAIL=$((FAIL + 1))
    fi
fi

# ── 5. ENV VAR LEAK CHECK ──────────────────────────────────
echo ""
echo "📦 Check 5: No exposed API keys..."
if [ -d "frontend" ]; then
    LEAKS=$(grep -rn 'NEXT_PUBLIC_API_KEY' frontend/app/ frontend/components/ 2>/dev/null || true)
    if [ -z "$LEAKS" ]; then
        echo -e "${GREEN}  ✅ PASS${NC}: No exposed API keys"
        PASS=$((PASS + 1))
    else
        echo -e "${RED}  ❌ FAIL${NC}: NEXT_PUBLIC_API_KEY found:"
        echo "$LEAKS"
        FAIL=$((FAIL + 1))
    fi
fi

# ── SUMMARY ──────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "  ✅ PASS: $PASS  |  ❌ FAIL: $FAIL"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ "$FAIL" -gt 0 ]; then
    echo ""
    echo -e "${RED}🚫 PUSH BLOCKED!${NC} Fix $FAIL failing check(s) above, then push again."
    echo "   Use --no-verify to bypass (NOT RECOMMENDED): git push --no-verify"
    exit 1
else
    echo -e "${GREEN}⚔️  All checks passed! Proceeding with push...${NC}"
    exit 0
fi
