from fastapi import FastAPI, Request, HTTPException
import os
from supabase import create_client, Client
from datetime import datetime, timedelta, timezone

app = FastAPI()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.post("/webhook/lava")
async def lava_webhook(request: Request):
    try:
        payload = await request.json()
        print("Получены данные от Lava.top:", payload)
        
        buyer_email = payload.get('buyer_email') or payload.get('email')
        
        if buyer_email:
            # Считаем дату: сегодня + 31 день (с запасом на часовые пояса)
            valid_until = (datetime.now(timezone.utc) + timedelta(days=31)).isoformat()
            
            supabase.table('user_subscriptions').upsert(
                {
                    'email': buyer_email, 
                    'is_pro': True,
                    'valid_until': valid_until
                },
                on_conflict='email'
            ).execute()
            print(f"✅ Пользователь {buyer_email} активирован до {valid_until}.")
            return {"status": "success"}
        else:
            return {"status": "error", "message": "Email not found"}
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
