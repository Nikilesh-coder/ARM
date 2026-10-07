# ARM (ReportForge AI) — Production Deployment Guide

This guide documents the end-to-end production deployment process for the ARM platform.

```text
GitHub Repository
   ├── Frontend (apps/web) ─────────► Vercel (Next.js)
   │                                     │
   │                                     ▼ HTTPS (NEXT_PUBLIC_API_URL)
   └── Backend (apps/api + packages) ─► Render (FastAPI / Uvicorn)
                                         │
                                         ├─► Supabase (PostgreSQL, Auth, Storage)
                                         └─► AI & Image Providers (Gemini, xKiro, Cloudflare, HF, Together)
```

---

## 1. BACKEND DEPLOYMENT (RENDER)

### Option A: Using `render.yaml` (Recommended Blueprint)
1. In the Render Dashboard, click **New +** $\rightarrow$ **Blueprint**.
2. Connect your GitHub repository.
3. Render will automatically detect [`render.yaml`](file:///c:/Users/A9959/OneDrive/Desktop/ARM/render.yaml) and configure the `arm-backend` service.
4. Fill in the required environment secrets when prompted.

### Option B: Manual Web Service Setup
1. In Render Dashboard, click **New +** $\rightarrow$ **Web Service**.
2. Connect your GitHub repository.
3. Configure the following service settings:
   - **Name**: `arm-backend`
   - **Region**: Choose closest to your users / Supabase region (e.g., Frankfurt / Singapore / Oregon)
   - **Branch**: `main`
   - **Root Directory**: `.` (leave empty or set to repository root)
   - **Runtime**: `Python 3`
   - **Build Command**:
     ```bash
     pip install --upgrade pip && pip install -r requirements.txt
     ```
   - **Start Command**:
     ```bash
     uvicorn apps.api.main:app --host 0.0.0.0 --port $PORT
     ```
   - **Health Check Path**: `/health`

### Render Environment Variables
Add the following environment variables in the Render Dashboard (**Environment** tab):

| Variable Name | Example / Recommended Value | Description |
|---|---|---|
| `PYTHON_VERSION` | `3.11.9` | Locks stable Python runtime |
| `ENVIRONMENT` | `production` | Enables production security & logging |
| `DEBUG` | `false` | Disables debug stack traces in production |
| `PROJECT_NAME` | `ReportForge AI` | Application title |
| `API_V1_STR` | `/api/v1` | Base API prefix |
| `LOG_LEVEL` | `INFO` | Standard production logging level |
| `FRONTEND_URL` | `https://<arm-frontend>.vercel.app` | Vercel domain to allow in CORS |
| `CORS_ORIGINS` | `https://<arm-frontend>.vercel.app` | Comma-separated allowed origins |
| `STORAGE_PROVIDER` | `supabase` | Uses Supabase Storage for templates/reports |
| `STORAGE_BUCKET_TEMPLATES` | `templates` | Bucket for college DOCX templates |
| `STORAGE_BUCKET_EVIDENCE` | `evidence` | Bucket for user uploaded project evidence |
| `STORAGE_BUCKET_REPORTS` | `reports` | Bucket for generated final DOCX reports |
| `SUPABASE_URL` | `https://<project-ref>.supabase.co` | Supabase API endpoint |
| `SUPABASE_ANON_KEY` | `<your-supabase-anon-key>` | Supabase public key |
| `SUPABASE_SERVICE_ROLE_KEY` | `<your-service-role-key>` | Server-side only Supabase service role key |
| `DATABASE_URL` | `postgresql://...` | Supabase PostgreSQL direct connection string |
| `DEFAULT_AI_PROVIDER` | `gemini` | Primary AI text & structured logic engine |
| `DEFAULT_AI_MODEL` | `gemini-2.5-flash` | Gemini model variant |
| `GEMINI_API_KEY` | `<your-gemini-api-key>` | Google AI Studio API key |
| `DEFAULT_IMAGE_PROVIDER` | `xkiro` | Primary image generation provider |
| `XKIRO_API_KEY` | `<your-xkiro-supernova-key>` | SenseNova / Supernova API key |
| `XKIRO_MODEL` | `sensenova/sensenova-u1.5-lite` | Supernova model |
| `XKIRO_FREE_ONLY` | `true` | Restricts to free tiers |
| `CLOUDFLARE_ACCOUNT_ID` | `<your-cloudflare-account-id>` | Cloudflare Workers AI Account ID |
| `CLOUDFLARE_API_TOKEN` | `<your-cloudflare-api-token>` | Cloudflare Workers AI Token |
| `HF_TOKEN` | `<your-huggingface-token>` | Hugging Face inference token |
| `TOGETHER_API_KEY` | `<your-together-api-key>` | Together AI fallback key |
| `SECRET_KEY` | `<random-32-byte-hex-string>` | Cryptographic session signing key |

---

## 2. FRONTEND DEPLOYMENT (VERCEL)

1. In the Vercel Dashboard, click **Add New...** $\rightarrow$ **Project**.
2. Import your GitHub repository.
3. Configure the Project Settings:
   - **Framework Preset**: `Next.js`
   - **Root Directory**: Click *Edit* and select `apps/web`
   - **Build Command**: `next build` (Default)
   - **Output Directory**: `.next` (Default)
   - **Install Command**: `npm install` (Default)

### Vercel Environment Variables
Add the following in Vercel (**Settings** $\rightarrow$ **Environment Variables**):

| Variable Name | Value | Description |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `https://arm-backend.onrender.com` | Live Render backend URL (no trailing slash) |
| `NEXT_PUBLIC_SUPABASE_URL` | `https://<project-ref>.supabase.co` | Supabase API URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | `<your-supabase-anon-key>` | Supabase anon public key |

> [!IMPORTANT]
> Never set `SUPABASE_SERVICE_ROLE_KEY` in Vercel. That key must remain strictly on Render.

---

## 3. SUPABASE CONFIGURATION

1. **Authentication $\rightarrow$ URL Configuration**:
   - **Site URL**: Set to `https://<arm-frontend>.vercel.app`
   - **Redirect URLs**: Add:
     - `https://<arm-frontend>.vercel.app/**`
     - `http://localhost:3000/**` (for local development)
2. **Storage Buckets**:
   Verify that the following storage buckets exist under Supabase **Storage**:
   - `templates`
   - `evidence`
   - `reports`
3. **Database**:
   Run database migrations if initializing a fresh Supabase project (schemas located in `supabase/migrations/`).

---

## 4. VERIFYING THE PRODUCTION DEPLOYMENT

Once both services are deployed:

1. **Backend Health Check**:
   ```bash
   curl -i https://<arm-backend>.onrender.com/health
   # Expected: HTTP 200 {"status": "healthy"}
   ```
2. **CORS Verification**:
   ```bash
   curl -i -X OPTIONS https://<arm-backend>.onrender.com/api/v1/health \
     -H "Origin: https://<arm-frontend>.vercel.app" \
     -H "Access-Control-Request-Method: GET"
   # Expected: Access-Control-Allow-Origin: https://<arm-frontend>.vercel.app
   ```
3. **Frontend E2E Flow**:
   - Open `https://<arm-frontend>.vercel.app`
   - Sign up / Log in $\rightarrow$ Verify persistent session survives page refresh
   - Upload DOCX template $\rightarrow$ Verify template preservation and registration
   - Run Guided Report or quick test $\rightarrow$ Verify DOCX download works via production API URL
