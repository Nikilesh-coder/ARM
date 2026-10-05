# ReportForge AI — Platform Foundation (Stage 1)

> **AI-Powered Academic Documentation Platform for College Students**
>
> *"Upload your college format once. ReportForge AI learns the document structure and uses it to generate future reports."*

---

## 1. System Architecture & Foundation Overview

ReportForge AI enforces a clean separation of concerns:
- **Client Tier**: Next.js 14+ (App Router), React, TypeScript, Tailwind CSS, Lucide icons, custom design tokens.
- **API & Core Gateway**: FastAPI application with dependency injection, CORS middleware, centralized configuration, and structured logging.
- **Storage Subsystem**: Pluggable `StorageProvider` abstraction (`LocalStorageProvider` for offline/development/testing, `SupabaseStorageProvider` for cloud object storage).
- **AI Subsystem**: Pluggable `AIProvider` abstraction (`GeminiProvider` for Google Gemini models, `MockAIProvider` for deterministic testing).
- **Document Subsystem**: Pluggable `DocumentService` abstraction connecting to `packages/template_intelligence` (deterministic OpenXML AST parser) and `packages/document_engine` (Word document synthesis).
- **Database Subsystem**: Connection lifecycle manager with Supabase / PostgreSQL support and Row Level Security (RLS) migrations.

---

## 2. Directory Layout

```
ARM/
├── apps/
│   ├── web/                                  # Next.js 14+ TypeScript Frontend
│   │   ├── src/
│   │   │   ├── app/                          # App router (page.tsx, layout.tsx, globals.css)
│   │   │   └── lib/                          # TypeScript API client (api-client.ts)
│   │   ├── package.json
│   │   ├── tailwind.config.ts
│   │   └── tsconfig.json
│   └── api/                                  # FastAPI Application
│       ├── main.py                           # App entry point, CORS, GET /health
│       ├── core/                             # Core foundations
│       │   ├── config.py                     # Pydantic v2 settings & environment variables
│       │   ├── database.py                   # Database connection manager & health checks
│       │   ├── exceptions.py                 # Custom domain exceptions & global handlers
│       │   ├── logging.py                    # Structured logging setup
│       │   └── response.py                   # Standard ApiResponse envelope conventions
│       ├── routers/                          # API endpoints (/health, /projects, /templates, /reports)
│       ├── schemas/                          # Pydantic DTO models
│       └── services/                         # Pluggable service providers
│           ├── ai/                           # AIProvider, GeminiProvider, MockAIProvider
│           ├── document/                     # DocumentService, StandardDocumentService
│           └── storage/                      # StorageProvider, LocalStorageProvider, SupabaseStorageProvider
├── packages/
│   ├── template_intelligence/                # OpenXML parser and TemplateSchema generator
│   └── document_engine/                      # Deterministic python-docx document assembler
├── supabase/
│   └── migrations/                           # PostgreSQL schema, RLS policies, indexes
├── tests/                                    # Automated pytest suite (12 passing tests)
│   ├── conftest.py
│   ├── test_health.py
│   ├── test_foundation_services.py
│   ├── test_template_parser.py
│   ├── test_document_assembler.py
│   └── test_api_endpoints.py
├── .env.example                              # Comprehensive environment template
└── README.md
```

---

## 3. Local Setup Guide

### Prerequisites
- Python 3.12+ (Tested on Python 3.14.3)
- Node.js 18+ (Tested on Node.js 20.18.0 LTS & npm 10.8.2)

### 3.1 Python Backend Setup
```powershell
# 1. Activate virtual environment
.\.venv\Scripts\Activate.ps1

# 2. Run test suite
pytest tests

# 3. Run linter & type check
flake8 apps\api packages tests --max-line-length=140
mypy apps\api packages tests --ignore-missing-imports

# 4. Start the FastAPI development server
python -m uvicorn apps.api.main:app --reload --port 8000
```

- **Health Endpoint**: `http://127.0.0.1:8000/health` (Returns `{"status": "healthy"}`)
- **Diagnostics**: `http://127.0.0.1:8000/api/v1/health`
- **Interactive Swagger Docs**: `http://127.0.0.1:8000/docs`

### 3.2 Frontend Setup
```powershell
cd apps\web

# Install dependencies (already provisioned)
npm install

# Run ESLint check
npm run lint

# Run production build & type check
npm run build

# Start Next.js development server
npm run dev
```

- **Web Dashboard**: `http://localhost:3000`

---

## 4. Health Check Specification

### Basic Health Check (Requested Requirement)
`GET /health`

**Response:**
```json
{
  "status": "healthy"
}
```

### Detailed Subsystem Diagnostics
`GET /api/v1/health`

**Response:**
```json
{
  "status": "healthy",
  "service": "reportforge-api",
  "environment": "development",
  "timestamp": "2026-09-27T08:24:52.001675+00:00",
  "subsystems": {
    "database": {
      "status": "connected",
      "provider": "postgresql",
      "database_configured": true
    },
    "storage": {
      "provider": "LocalStorageProvider",
      "configured": true
    },
    "ai": {
      "provider": "MockAIProvider",
      "configured": true
    }
  }
}
```

---

## 5. Security Principles Implemented
1. **Server-Side API Key Isolation**: No AI credentials or database secrets are ever bundled into frontend bundles.
2. **Untrusted Evidence Isolation**: Text and files uploaded by students are treated strictly as untrusted data.
3. **Deterministic Document Assembly**: The LLM never touches final document styles or layout; formatting is governed by the deterministic document engine.
