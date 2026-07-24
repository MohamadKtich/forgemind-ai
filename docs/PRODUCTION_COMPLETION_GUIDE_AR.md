# دليل إكمال ForgeMind AI للإنتاج

هذه النسخة Production Candidate وليست نظام تحكم صناعي معتمد. اتبع بالترتيب:

1. انسخ `backend/.env.example` إلى `backend/.env`.
2. ضع `DATABASE_URL` الخاص بـ Supabase Session Pooler مع `sslmode=require`.
3. ولّد أسرارًا عشوائية طويلة لـ `SECRET_KEY`, `DEVICE_API_KEY`, `LOCAL_RECOVERY_KEY`.
4. شغّل `alembic upgrade head` لإنشاء القاعدة.
5. شغّل `python scripts/migrate_database.py --source sqlite:///... --target postgresql+psycopg://...`.
6. أنشئ Storage bucket خاص باسم `forgemind-private` وضع URL وService Role Key في بيئة الخادم فقط.
7. عطّل `SEED_DEFAULT_USERS` و`ALLOW_LOCAL_REGISTRATION` قبل النشر.
8. شغّل الاختبارات ثم GitHub Actions.
9. درّب MetroPT-3 وKSDD عبر ملفات Colab الموجودة في `notebooks/`.
10. لا تربط أوامر إيقاف المعدات الحقيقية قبل مراجعة سلامة وموافقة بشرية.
