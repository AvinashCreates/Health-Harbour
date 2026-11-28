Yes! We have a working **HealthHarbor local demo setup**. The important thing is to make sure the frontend connects to the isolated backend on port **8002**, not the older Docker backend on port 8000.

## **1. Start the backend**

First, check whether the backend is already running:

```
curl http://127.0.0.1:8002/health/live
```

Expected response:

```
{"status":"alive","service":"healthharbor-backend"}
```

Check readiness:

```
curl http://127.0.0.1:8002/health/ready
```

If these work, **don't start another backend instance**.

## **2. Start the frontend**

Open a new terminal:

```
cd ~/Downloads/healthcare-exchange/frontend
```

Run:

```
VITE_API_BASE=http://127.0.0.1:8002 npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Keep this terminal open while using the application.

## **3. Open HealthHarbor**

**Frontend**

Local demo

# [**http://127.0.0.1:5173**](http://127.0.0.1:5173?utm_source=chatgpt.com)

Open HealthHarbor&#x20;

**Backend API documentation**

[http://127.0.0.1:8002/docs](http://127.0.0.1:8002/docs?utm_source=chatgpt.com)

## **4. Useful troubleshooting commands**

Check running services:

```
ss -ltnp | grep -E ':5173|:8002'
```

Check backend health:

```
curl -i http://127.0.0.1:8002/health/live
```

Check frontend dependencies:

```
cd ~/Downloads/healthcare-exchange/frontend
npm install
```

Build frontend for production validation:

```
npm run build
```

## **Important distinction**

Your current setup is a **local demonstration environment**:

- Frontend: React + Vite.
- Backend: FastAPI.
- Database: isolated SQLite demo database.
- Authentication: local demo authentication.
- FHIR: local demo mode.
- Fabric: disabled.

Don't run `docker compose down`, database resets, migrations, or seed commands just to start the demo. Your existing Docker PostgreSQL environment is separate and contains persistent data.

**My recommendation:** Let's eventually create a single `start-demo.sh` script that checks backend health, starts the frontend, and reports service status. That will make starting HealthHarbor much easier.