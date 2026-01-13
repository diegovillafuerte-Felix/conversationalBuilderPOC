# Railway Deployment Plan for Felix Backend

> **Status:** Planned for future implementation

## Overview

Deploy the FastAPI backend to Railway with PostgreSQL and Redis services.

## Prerequisites

- Railway account (https://railway.app)
- Railway CLI installed (`npm install -g @railway/cli`)
- `OPENAI_API_KEY` ready

## Code Changes Required

### 1. Update Dockerfile for Railway PORT

**File:** `backend/Dockerfile`

Change the CMD to use Railway's dynamic PORT:

```dockerfile
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

### 2. Create Railway Configuration

**File:** `backend/railway.toml` (NEW)

```toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "Dockerfile"

[deploy]
healthcheckPath = "/health"
healthcheckTimeout = 300
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

### 3. Update main.py (Optional)

If running directly without Docker:

```python
# At the bottom of main.py
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)
```

## Deployment Steps

### Step 1: Login to Railway

```bash
railway login
```

### Step 2: Initialize Project

```bash
cd backend
railway init
# Choose "Empty Project" or create from dashboard
```

### Step 3: Add PostgreSQL Plugin

```bash
railway add -p postgresql
```

This automatically sets `DATABASE_URL` in the environment.

### Step 4: Add Redis Plugin

```bash
railway add -p redis
```

This automatically sets `REDIS_URL` in the environment.

### Step 5: Set Environment Variables

Via Railway dashboard or CLI:

```bash
railway variables set OPENAI_API_KEY=your_key_here
railway variables set DEBUG=false
railway variables set SECRET_KEY=your_production_secret
```

### Step 6: Deploy

```bash
railway up
```

Or connect GitHub repo for automatic deployments:

```bash
railway link
# Then push to GitHub to trigger deploy
```

## Environment Variables Summary

| Variable | Source | Description |
|----------|--------|-------------|
| `DATABASE_URL` | Railway PostgreSQL plugin | Auto-set by Railway |
| `REDIS_URL` | Railway Redis plugin | Auto-set by Railway |
| `PORT` | Railway | Auto-set, dynamic port |
| `OPENAI_API_KEY` | Manual | Your LLM API key |
| `DEBUG` | Manual | Set to `false` for production |
| `SECRET_KEY` | Manual | Production secret key |

## Verification

After deployment:

1. Check Railway logs for startup success
2. Visit `https://your-app.railway.app/health` - should return health status
3. Visit `https://your-app.railway.app/` - should return app info
4. Test the chat API endpoint

## Optional Enhancements

- **Custom Domain:** Configure in Railway dashboard under Settings > Domains
- **CORS:** Update `main.py` to restrict allowed origins for production
- **Monitoring:** Railway provides built-in metrics and logs
