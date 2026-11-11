from fastapi import FastAPI, Request, HTTPException
import os
from supabase import create_client, Client

app = FastAPI()

# Эти данные мы возьмем из переменных окружения на Render
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.post("/webhook/lava")
async def lava_webhook(request: Request):
    try:
        payload = await request.json()
        print("Получены данные от Lava.top:", payload) # Для отладки в логах Render
        
        # Ищем email покупателя в запросе. 
        # В Lava.top он обычно передается в поле 'buyer_email' или 'email'
        buyer_email = payload.get('buyer_email') or payload.get('email')
        
        if buyer_email:
            # Добавляем или обновляем пользователя в базе данных
            supabase.table('user_subscriptions').upsert(
                {'email': buyer_email, 'is_pro': True},
                on_conflict='email'
            ).execute()
            print(f"✅ Пользователь {buyer_email} успешно активирован в базе данных.")
            return {"status": "success", "message": "User activated"}
        else:
            print("⚠️ В запросе не найден email покупателя.")
            return {"status": "error", "message": "Email not found in payload"}
            
    except Exception as e:
        print(f"❌ Ошибка при обработке вебхука: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
