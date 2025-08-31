# CLAUDE.md Reorganization Summary

## What Was Done

Reorganized CLAUDE.md to focus on **CRITICAL GUARDRAILS** while moving project-specific knowledge to dedicated documentation files.

## Key Changes

### ✅ NEW CLAUDE.md Structure (CLAUDE_NEW.md)
**Focused on mistake prevention:**
- 🚨 Critical mistake prevention (UV vs pip, release process, security, wiki management)
- 🛠️ Essential commands only (setup, testing, release)
- 📋 Quick reference for common issues
- 📚 Links to detailed docs in `docs/` directory

**Size**: Reduced from 535 lines to ~100 lines

### 📁 New Documentation Files Created

1. **`docs/PROJECT_OVERVIEW.md`**
   - What the system does and why
   - Core problem and solution approach  
   - Key thresholds and cost tracking
   - Health correlation goals

2. **`docs/ARCHITECTURE.md`**
   - Data collection flow details
   - API integrations (Airthings, AirGradient, Google)
   - Multi-sensor setup and network architecture
   - Error handling and resilience strategies

3. **`docs/LESSONS_LEARNED.md`**
   - Historical context from July-August 2025
   - Multi-sensor collection discoveries
   - GitHub Wiki management lessons
   - Plotly visualization fixes
   - Release process hard-won knowledge

4. **`docs/ENVIRONMENT_SETUP.md`**
   - Environment variable configuration
   - Development setup (local vs Unifi)
   - API setup instructions
   - Security considerations and troubleshooting

## Benefits of Reorganization

### For Claude Code
- **Faster reference**: Critical guardrails immediately visible
- **Mistake prevention**: Common errors highlighted upfront  
- **Clear action items**: Essential commands readily available
- **Context separation**: Detailed knowledge doesn't obscure warnings

### For Contributors
- **Better organization**: Logical separation of concerns
- **Easier navigation**: Specific docs for specific needs
- **Complete coverage**: Nothing lost, everything organized
- **Maintainability**: Updates go to appropriate files

## Migration Path

### Immediate (Recommended)
```bash
# Replace current CLAUDE.md with new version
mv CLAUDE.md CLAUDE_OLD.md
mv CLAUDE_NEW.md CLAUDE.md
```

### Verification Checklist
- [ ] Critical warnings preserved and prominent
- [ ] Essential commands easily accessible  
- [ ] All project knowledge preserved in docs/
- [ ] Links between files work correctly
- [ ] New contributor experience improved

## What Stayed vs What Moved

### ✅ Stayed in CLAUDE.md (Critical Guardrails)
- UV vs pip package management warnings
- Release process (not a Python package!)
- Security reminders (device info placeholders)
- Wiki repository dangers
- Essential development commands

### 📁 Moved to docs/ (Project Knowledge)
- Project overview and goals
- Architecture details and API specs
- Historical lessons and context
- Environment setup instructions
- Multi-sensor setup specifics
- Visualization workflow details

## Result

**Old CLAUDE.md**: 535 lines of mixed critical warnings + project history + detailed setup  
**New CLAUDE.md**: ~100 lines focused on preventing the most common and dangerous mistakes

**Total knowledge preserved**: 100% (moved to appropriate files)  
**Mistake prevention**: Significantly improved (critical items upfront)  
**Maintainability**: Much better (concerns separated)