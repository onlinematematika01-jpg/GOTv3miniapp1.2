# GOTv3 Mini App — Railway Deployment

## Arxitektura

```
[Telegram Bot] ──→ [PostgreSQL DB] ←── [Mini App API (FastAPI)]
                                              ↑
                                    [Mini App Frontend (nginx)]
                                              ↑
                                         [Foydalanuvchi]
```

## Railway'da Qo'shish

### 1. Backend Service yaratish

Railway dashboard'da "New Service" → "GitHub Repo" →
- Root directory: `miniapp/backend`
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

**Environment variables:**
```
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname
```

> ⚠️ Railway'da PostgreSQL URL `postgresql://` ko'rinishida keladi.
> FastAPI uchun `postgresql+asyncpg://` ga o'zgartiring!

### 2. Frontend Service yaratish

Railway'da "New Service" → "GitHub Repo" →
- Root directory: `miniapp/frontend`
- Ya `nixpacks` yoki static hosting ishlatiladi

**Frontend'dagi API_BASE'ni o'zgartiring:**
```javascript
// frontend/index.html ichida:
const API_BASE = 'https://your-backend.railway.app';
```

### 3. Backend'ga `models.py` qo'shish

GOTv3 asosiy proyektdagi `database/models.py` faylini
`miniapp/backend/models.py` ga nusxa oling:

```bash
cp database/models.py miniapp/backend/models.py
```

### 4. CORS sozlash

Backend `main.py`'dagi CORS qismida frontend URL qo'shing:
```python
allow_origins=["https://your-frontend.railway.app", "*"]
```

## Mahalliy ishga tushirish

```bash
cd miniapp
docker-compose up --build
```

Frontend: http://localhost:3000  
API: http://localhost:8000/docs

## API Endpoints

| Endpoint | Tavsif |
|----------|--------|
| `GET /api/map` | Barcha xarita ma'lumotlari |
| `GET /api/house/{id}` | Xonadon detallari |
| `GET /api/chronicles` | Voqealar xronikasi |
| `GET /api/leaderboard` | Kuch reytingi |
| `GET /health` | Server holati |

## Telegram Bot bilan integratsiya

Botda mini app tugmasi qo'shish:
```python
from aiogram.types import WebAppInfo, InlineKeyboardButton

web_app_btn = InlineKeyboardButton(
    text="🗺 Westeros Xaritasi",
    web_app=WebAppInfo(url="https://your-frontend.railway.app")
)
```

## Funksiyalar

- 🗺 **Westeros xaritasi** — barcha 9 hudud vizual ko'rinishida
- 🏰 **Xonadon markerlari** — har bir xonadon xaritada ko'rinadi
- ⚔️ **Urush ko'rsatgichlari** — faol urushlar qizil o'qlar bilan
- 🤝 **Ittifoq chiziqlari** — ittifoqdosh xonadonlar bog'langan
- 📊 **Xonadon paneli** — a'zolar, resurslar, tarix
- 🏆 **Reyting** — kuch bo'yicha top-10
- 📜 **Xronika** — so'nggi 20 ta voqea
- 🔄 **Auto-refresh** — har 30 soniyada yangilanadi
