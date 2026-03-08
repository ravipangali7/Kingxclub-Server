# WebSocket (real-time messages) deployment

The Messages feature uses a WebSocket at **`/ws/messages/`** for real-time delivery. If you see **404** for `GET /ws/messages/?token=...`, the request is reaching a **WSGI** server (e.g. gunicorn), which does not handle WebSockets.

## Fix: run ASGI for WebSocket

WebSockets require an **ASGI** server. Two options:

### Option A: Run Daphne for the whole site

Serve both HTTP and WebSocket with Daphne:

```bash
daphne -b 0.0.0.0 -p 8000 karnalix.asgi:application
```

Then point nginx (or your reverse proxy) to this process instead of gunicorn for the app.

### Option B: Run Gunicorn + Daphne and proxy by path

- Keep **gunicorn** for HTTP (e.g. on port 8000).
- Run **Daphne** for WebSocket (e.g. on port 8001):

  ```bash
  daphne -b 127.0.0.1 -p 8001 karnalix.asgi:application
  ```

- In **nginx**, send only `/ws/` to Daphne and the rest to gunicorn:

  ```nginx
  location /ws/ {
      proxy_pass http://127.0.0.1:8001;
      proxy_http_version 1.1;
      proxy_set_header Upgrade $http_upgrade;
      proxy_set_header Connection "upgrade";
      proxy_set_header Host $host;
      proxy_set_header X-Real-IP $remote_addr;
  }
  location / {
      proxy_pass http://127.0.0.1:8000;
      # ... usual proxy headers
  }
  ```

Without this, the Messages page still works via **REST + polling**; only real-time push will be missing until `/ws/` is served by ASGI.
