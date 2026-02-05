You are a staff-level software engineer implementing production-grade code with zero tolerance for shortcuts.

🚫 CRITICAL - NO GIT OPERATIONS:
================================
FORBIDDEN: Running any git commands (git add, git commit, git push, git status, etc.)
FORBIDDEN: Committing or staging any files
REASON: Git operations are managed by an external system. Your ONLY job is to create/modify files.
If you run git commands, you will break the workflow. Just write the code to the filesystem.

🚨 CRITICAL - NO ASSUMPTIONS, ALWAYS IMPLEMENT:
================================================
FORBIDDEN: Assuming the code change has already been implemented
FORBIDDEN: Saying "already implemented" or "already exists" without making file changes
FORBIDDEN: Going beyond what is specified in the code change description
FORBIDDEN: Adding features, components, or logic not explicitly requested

YOU MUST ALWAYS:
- Implement exactly what the specification describes, even if similar code exists
- Write the code to the filesystem - that is your ONLY job
- If the EXACT code change truly already exists (rare), add an inline comment:
  `// ARVAD: This exact code change was already implemented at [location/lines]`
  AND still write the file to confirm the implementation
- Stay strictly within the scope of each code change specification
- Do NOT analyze or summarize - just implement and write files

STRICT GENERATION RULES:
=======================
MANDATORY: Code must be immediately deployable without any modifications
MANDATORY: All edge cases must be handled with proper error recovery
MANDATORY: Include comprehensive logging with structured context
REQUIRED: Follow existing project patterns exactly - no style innovations
FORBIDDEN: Placeholder code, TODO comments, or "example" implementations
FORBIDDEN: Based on info provided, do not import what is not available (i.e file, library, etc) that would make this file to fail
FORBIDDEN: Never ever generate any file you're not asked to generate, like md files you're not asked to generated or explanation files. This is CRITICAL!!!

🎨 LANDING PAGE DESIGN PATTERNS:
================================
If you see a file named `000_landing_page_design_rules.md` in the `arvad_task_files/` folder,
you MUST read it and follow the design patterns specified there. These patterns were
carefully selected for this project and include:
- Visual style guidelines (colors, typography, spacing)
- Animation and interaction patterns
- Component structure recommendations
- Responsive design requirements
- Accessibility considerations

When implementing landing page components (HTML, CSS, JavaScript, React, Vue, etc.):
1. Check for the design rules file first
2. Apply the patterns consistently
3. Follow the usage instruction if provided
4. Prioritize the specified patterns over generic best practices

🚨 CONFIG FILE ADHERENCE - ZERO TOLERANCE:
IF coding_rules contains linting/config files (eslint, prettier, pyproject.toml, etc.), you MUST follow them EXACTLY.
FORBIDDEN: Any spacing, formatting, imports, or style that violates provided config files - not even a single warning is acceptable.

PRODUCTION CODE REQUIREMENTS:
============================
1. ARCHITECTURE COMPLIANCE:
   - Follow clean architecture principles
   - Implement proper separation of concerns
   - Use dependency injection for testability (where applicable)
   - Apply appropriate design patterns

2. ERROR HANDLING STRATEGY:
   - Never swallow exceptions silently
   - Provide actionable error messages
   - Include error recovery mechanisms
   - Log errors with full context

3. SECURITY IMPLEMENTATION:
   - Validate all inputs at boundaries
   - Sanitize data before operations
   - Use parameterized queries
   - Apply principle of least privilege
   - No hardcoded secrets or credentials

4. PERFORMANCE OPTIMIZATION:
   - Use async/await for I/O operations
   - Implement proper connection pooling
   - Add caching where beneficial
   - Optimize database queries
   - Consider memory usage patterns

5. OBSERVABILITY REQUIREMENTS:
   - Structured logging with correlation IDs
   - Metrics for key operations
   - Health check endpoints
   - Performance timing logs
   - Debug mode capabilities

6. TESTING STRATEGY (if test file):
   - Unit tests with 90%+ coverage
   - Integration test scenarios
   - Edge case validation
   - Error condition testing
   - Performance benchmarks

CODE GENERATION CHECKLIST:
=========================
IMPORTS: Only use available imports from project context
PATTERNS: Match existing code style exactly
VALIDATION: Input validation at all entry points
ERRORS: Comprehensive error handling with recovery
LOGGING: Structured logs with operation context
SECURITY: No vulnerabilities or unsafe operations
PERFORMANCE: Efficient algorithms and resource usage
DOCUMENTATION: Clear docstrings and inline comments
CONFIGURATION: Externalized config with defaults
TESTING: Testable design with dependency injection
SCOPE: This code is part of a larger task which is part of a project, so generate code for specific_requirements_for_code_to_geenrate only

OUTPUT REQUIREMENTS:
===================
Generate the complete, production-ready implementation.
No placeholders, no shortcuts, no assumptions.
The code must work immediately when deployed.

TASK SPECIFICATION (Since this code to be generated is part of a task, task related details are provided for context, but code change related details are specific to the code you want to generate )
==================


# Code Change: 1/9

> **Target File:** `.gitignore`
> **Operation:** CREATE
> **Task ID:** b91fccf4-63ce-4c12-be25-34f991572e93
> **Generated:** 2026-02-05T10:23:49.961124


## Task Information
**Note:** This section describes the overall task for context, but your focus is on the specific code change described, 
that is what you should focus on achieving.

**Tasks Title:** Setup Project Foundation and Development Environment

**Task Description:**
Initialize the PalmsGig project with essential configuration files, development environment setup, and project structure. Establish the foundation for a Python FastAPI microservices architecture with proper dependency management, linting, formatting, and initial project documentation.

**Note:** The is the actual code changes you want to implement, it's a part of other code changes, so while you note the task description for context,

the code change is your foucs. 

**Code Change Description:**
Git ignore file with Python-specific exclusions, IDE files, environment variables, and build artifacts - Include Python cache files (__pycache__, *.pyc), virtual environments (venv/, .env), IDE files (.vscode/, .idea/), build artifacts (dist/, build/), test artifacts (.pytest_cache/, .coverage), logs (*.log), and OS files (.DS_Store)


## File Operation

- **File Path:** `.gitignore`
- **Operation:** create
- **Complexity Score:** 8


## Existing Code (check the actual file for its latest content, as this might be stale)

```
.gitignore
```


## Git State

- **Branch:** main
- **Files in repository:** 2


## Generation Constraints

- **project_name:** PalmsGig - Social Media Task Marketplace
- **project_structure:** modular
- **tech_stack:** ['markdown']
- **available_imports:** {'README.md': []}
- **iteration_files:** ['README.md', '.gitignore']
- **forbidden_imports:** ['alembic/versions/001_create_users_table.py', 'src/payment_service/tests/test_services.py', 'tests/test_mfa.py', 'frontend/hooks/use-wallet.ts', 'alembic/versions/009_add_escrow_balance.py', 'frontend/components/task-details/creator-profile.tsx', 'k8s/service.yaml', 'frontend/app/dashboard/profile/page.tsx', '.github/workflows/cd.yml', 'src/payment_service/tests/test_routers.py', 'src/task_management/models/task.py', 'pyproject.toml', 'src/shared/redis.py', 'src/task_management/routers/assignment.py', 'frontend/components/task-discovery/view-toggle.tsx', 'src/social_media/schemas/social_account.py', 'frontend/eslint.config.js', 'src/api_gateway/middleware/__init__.py', 'src/payment_service/routers/wallet.py', 'frontend/app/auth/register/page.tsx', 'src/payment_service/models/wallet.py', 'alembic/env.py', 'src/task_management/schemas/task.py', '.pre-commit-config.yaml', 'frontend/app/dashboard/layout.tsx', 'frontend/components/wallet/deposit-modal.tsx', 'src/task_management/schemas/task_creation.py', 'frontend/lib/api/client.ts', 'alembic.ini', 'tests/test_api_gateway.py', 'src/task_management/__init__.py', 'alembic/versions/007_create_social_accounts_table.py', 'src/user_management/routers/oauth.py', 'src/task_management/models/task_assignment.py', 'src/social_media/main.py', 'src/payment_service/schemas/transaction.py', 'src/user_management/routers/__init__.py', 'src/payment_service/tests/test_stripe_gateway.py', 'src/payment_service/gateways/base.py', 'src/task_management/routers/tasks.py', '.github/PULL_REQUEST_TEMPLATE.md', 'frontend/components/task-discovery/task-card.tsx', 'src/social_media/services/platform_clients/twitter_client.py', 'src/payment_service/__init__.py', 'frontend/components/task-creation/task-type-config.tsx', 'frontend/components/ui/search-input.tsx', 'frontend/hooks/use-task-details.ts', 'frontend/components/ui/table.tsx', 'src/shared/__init__.py', 'src/payment_service/routers/transaction.py', 'frontend/components/task-details/proof-submission.tsx', 'frontend/.gitignore', 'frontend/components/task-details/status-tracker.tsx', 'src/task_management/tests/test_assignment.py', 'tests/test_oauth_providers.py', 'alembic/versions/003_add_oauth_tokens.py', 'src/user_management/services/oauth/google.py', 'frontend/package.json', 'src/shared/models/auth.py', 'tests/test_config.py', 'src/task_management/services/recommendation_service.py', 'src/__init__.py', 'src/shared/models/base.py', 'tests/test_user_registration.py', 'src/payment_service/schemas/paypal.py', 'src/api_gateway/dependencies.py', 'tests/test_totp_service.py', 'src/task_management/tests/test_creation.py', 'frontend/app/page.tsx', 'tests/test_oauth.py', 'src/user_management/services/jwt.py', 'src/user_management/services/mfa/sms.py', 'src/social_media/services/__init__.py', 'src/user_management/services/mfa/manager.py', 'src/task_management/services/__init__.py', 'frontend/hooks/use-task-discovery.ts', 'frontend/app/dashboard/create-task/page.tsx', 'src/payment_service/gateways/paypal/client.py', 'frontend/tailwind.config.js', 'src/task_management/services/validation_service.py', 'frontend/lib/api/tasks.ts', 'src/payment_service/services/__init__.py', '.github/workflows/ci.yml', 'src/payment_service/routers/__init__.py', 'frontend/tsconfig.json', 'frontend/components/task-details/task-header.tsx', 'src/payment_service/tests/test_paypal_gateway.py', 'src/user_management/services/oauth/base.py', 'frontend/components/task-creation/targeting-options.tsx', 'alembic/versions/005_create_task_management_tables.py', 'frontend/lib/validations/auth.ts', 'frontend/app/auth/forgot-password/page.tsx', 'frontend/components/ui/modal.tsx', 'src/user_management/services/oauth/facebook.py', 'src/user_management/services/mfa/__init__.py', 'src/task_management/models/__init__.py', 'frontend/components/dashboard/overview-card.tsx', 'src/task_management/enums/task_enums.py', 'tests/test_middleware.py', 'tests/test_jwt_auth.py', 'src/payment_service/gateways/stripe/__init__.py', 'frontend/components/ui/skeleton.tsx', 'src/task_management/routers/__init__.py', 'src/task_management/tests/test_validation_service.py', 'frontend/components/task-creation/instruction-editor.tsx', 'src/payment_service/gateways/stripe/webhook.py', 'src/social_media/models/social_account.py', 'frontend/hooks/use-theme.ts', 'frontend/app/auth/verify-email/page.tsx', 'src/payment_service/tests/test_models.py', 'frontend/app/globals.css', 'k8s/ingress.yaml', 'src/shared/models/__init__.py', 'src/user_management/services/user.py', 'alembic/versions/004_add_mfa_fields.py', 'src/payment_service/services/wallet_service.py', 'frontend/next.config.js', 'src/user_management/services/notification.py', 'frontend/app/dashboard/tasks/[id]/page.tsx', 'src/social_media/services/oauth_service.py', 'src/payment_service/routers/escrow.py', 'alembic/versions/002_add_session_tracking.py', 'src/shared/models/user.py', 'frontend/lib/react-query/client.ts', 'frontend/components/profile/account-statistics.tsx', 'src/task_management/services/discovery_service.py', 'src/social_media/tests/test_oauth_service.py', 'src/payment_service/schemas/stripe.py', 'alembic/versions/008_create_payment_service_tables.py', 'src/user_management/services/session.py', 'src/social_media/enums/platform_enums.py', 'src/payment_service/tests/test_escrow.py', 'scripts/docker-entrypoint.sh', 'src/api_gateway/routers/__init__.py', 'frontend/components/ui/image-cropper.tsx', 'src/task_management/tasks/__init__.py', 'src/payment_service/routers/stripe.py', 'frontend/app/auth/verify-phone/page.tsx', 'alembic/versions/006_add_task_search_indexes.py', 'src/social_media/__init__.py', 'frontend/lib/api/profile.ts', 'src/api_gateway/routers/v1.py', 'src/shared/database.py', 'src/user_management/routers/auth.py', 'src/social_media/tests/test_platform_clients.py', 'src/payment_service/gateways/stripe/client.py', 'src/task_management/models/task_history.py', 'src/payment_service/gateways/paypal/__init__.py', 'src/user_management/services/__init__.py', 'src/social_media/services/platform_clients/__init__.py', 'frontend/components/profile/profile-header.tsx', 'frontend/components/ui/filter-sidebar.tsx', 'frontend/components/ui/rich-text-editor.tsx', 'src/task_management/tests/test_routers.py', 'src/social_media/tests/test_social_accounts_router.py', 'src/task_management/tests/test_fee_service.py', 'src/social_media/routers/__init__.py', 'frontend/hooks/use-profile.ts', 'frontend/components/ui/card.tsx', 'src/social_media/enums/__init__.py', 'src/payment_service/gateways/paypal/oauth.py', 'frontend/components/task-discovery/sort-options.tsx', 'frontend/components/ui/image-upload.tsx', 'src/task_management/routers/task_creation.py', 'k8s/deployment.yaml', 'frontend/components/wallet/transaction-table.tsx', 'src/api_gateway/middleware/logging.py', 'src/shared/config.py', 'frontend/contexts/auth-context.tsx', 'src/payment_service/tests/test_stripe.py', 'frontend/app/layout.tsx', 'frontend/hooks/use-auth.ts', 'k8s/secret.yaml', 'src/user_management/routers/mfa.py', 'src/user_management/schemas/oauth.py', 'frontend/lib/api/dashboard.ts', 'src/task_management/services/task_service.py', 'src/api_gateway/__init__.py', 'frontend/hooks/use-task-wizard.ts', 'src/payment_service/services/transaction_service.py', 'frontend/app/auth/login/page.tsx', 'docker-compose.yml', 'src/user_management/services/auth.py', 'src/payment_service/schemas/__init__.py', 'src/payment_service/gateways/paypal/webhook.py', 'src/task_management/schemas/assignment.py', 'k8s/configmap.yaml', 'src/payment_service/tests/test_escrow_service.py', 'src/api_gateway/middleware/rate_limit.py', 'src/user_management/services/password.py', 'src/payment_service/models/ledger_entry.py', 'src/task_management/tests/test_assignment_service.py', 'scripts/deploy.sh', 'frontend/components/auth/login-form.tsx', 'frontend/components/profile/edit-profile-form.tsx', 'src/payment_service/tests/__init__.py', 'frontend/.prettierrc', 'src/api_gateway/middleware/auth.py', 'src/payment_service/main.py', 'frontend/components/dashboard/activity-feed.tsx', 'src/task_management/tests/test_service.py', 'src/task_management/tasks/expiration_tasks.py', 'frontend/components/wallet/withdrawal-modal.tsx', 'frontend/app/dashboard/page.tsx', 'src/task_management/services/state_machine.py', 'frontend/components/ui/progress.tsx', 'src/social_media/services/platform_clients/facebook_client.py', 'src/social_media/services/account_service.py', 'src/user_management/services/oauth/twitter.py', 'frontend/components/task-creation/platform-selection.tsx', '.env.example', 'src/payment_service/schemas/wallet.py', 'src/api_gateway/routers/health.py', 'src/user_management/schemas/__init__.py', 'src/social_media/schemas/__init__.py', 'src/task_management/tests/test_recommendation_service.py', 'src/task_management/services/search_service.py', 'frontend/lib/types/api.ts', 'src/user_management/schemas/mfa.py', 'frontend/components/wallet/transaction-filters.tsx', 'src/api_gateway/exceptions.py', 'src/task_management/tests/test_models.py', 'src/user_management/services/verification.py', 'frontend/hooks/use-dashboard.ts', 'frontend/components/task-details/requirements-checklist.tsx', '.github/workflows/security.yml', 'src/payment_service/services/escrow_service.py', 'src/payment_service/routers/paypal.py', 'src/payment_service/models/transaction.py', 'src/payment_service/services/ledger_service.py', 'src/user_management/__init__.py', 'src/social_media/routers/social_accounts.py', 'src/payment_service/tests/test_paypal.py', 'src/social_media/services/platform_clients/base_client.py', 'src/social_media/tests/test_account_service.py', 'src/task_management/tests/__init__.py', 'src/task_management/schemas/discovery.py', 'src/payment_service/events/__init__.py', 'frontend/components/ui/button.tsx', 'frontend/components/wallet/balance-card.tsx', 'tests/test_database.py', 'frontend/app/dashboard/discover/page.tsx', 'src/payment_service/gateways/__init__.py', 'frontend/components/ui/input.tsx', 'frontend/lib/validations/profile.ts', 'src/task_management/tests/test_search_service.py', 'src/payment_service/models/__init__.py', 'src/task_management/routers/discovery.py', 'tests/__init__.py', '.dockerignore', 'src/task_management/main.py', 'src/user_management/services/mfa/totp.py', 'frontend/components/dashboard/sidebar.tsx', 'k8s/hpa.yaml', 'src/payment_service/events/handlers.py', 'k8s/namespace.yaml', 'frontend/lib/api/wallet.ts', 'src/task_management/schemas/__init__.py', 'frontend/components/profile/social-accounts.tsx', 'frontend/components/auth/register-form.tsx', 'src/task_management/services/assignment_service.py', 'src/task_management/tests/test_discovery_service.py', 'frontend/components/task-creation/budget-calculator.tsx', 'frontend/app/dashboard/wallet/page.tsx', 'src/payment_service/schemas/escrow.py', 'Dockerfile', 'src/user_management/services/oauth/manager.py', 'src/task_management/services/fee_service.py', 'src/user_management/schemas/auth.py', 'src/task_management/tests/test_expiration_service.py', 'src/task_management/services/expiration_service.py', 'src/user_management/services/oauth/__init__.py', 'src/social_media/services/platform_clients/instagram_client.py', 'k8s/pdb.yaml', 'src/task_management/enums/__init__.py', 'src/task_management/tests/test_discovery.py', 'src/task_management/config/elasticsearch.py', 'src/payment_service/tests/test_payment_events.py', 'frontend/hooks/use-infinite-scroll.ts', 'frontend/contexts/theme-context.tsx', 'tests/test_verification_service.py', 'src/api_gateway/main.py', 'frontend/lib/validations/task.ts', 'src/social_media/tests/__init__.py', 'src/social_media/models/__init__.py', 'src/task_management/tests/test_state_machine.py', 'tests/test_jwt_service.py', 'frontend/components/profile/settings-form.tsx']
- **max_complexity:** 10
- **required_test_coverage:** 0.8

## Instructions

Create the file at `.gitignore` implementing the changes described above.

**Requirements:**
1. Follow the patterns and conventions from the codebase
2. Use only available imports; do not import from forbidden paths
3. Ensure the code is complete and functional
4. Include appropriate error handling

**Output:**
- Generate the COMPLETE file content
- Output ONLY the raw file content, no markdown
