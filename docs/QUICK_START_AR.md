# التشغيل السريع لـ ForgeMind AI 3.0 على Windows

## المتطلبات

- Python 3.11 أو أحدث.
- Node.js 22 LTS أو أحدث.
- اتصال بالإنترنت أثناء تثبيت المكتبات.
- اتصال بالإنترنت فقط عند تنزيل بيانات التدريب الحقيقية.

## التثبيت

1. فك ملف ZIP داخل مجلد عادي.
2. افتح المجلد `forgemind-ai`.
3. شغّل `SETUP_WINDOWS.bat` مرة واحدة.
4. بعد النجاح شغّل `START_FORGEMIND.bat`.
5. افتح `http://localhost:3000`.

لا تشغّل المشروع من داخل ZIP. يبدو الأمر بديهيًا، ومع ذلك يصر Windows على منح البشر فرصة جديدة لاكتشافه.

## الحسابات الأولية

```text
admin@forgemind.ai          ForgeMind#2026
manager@forgemind.ai        ForgeMind#2026
maintenance@forgemind.ai    ForgeMind#2026
quality@forgemind.ai        ForgeMind#2026
```

## اللغة والمظهر

- استخدم الزرين العائمين أسفل الشاشة لتبديل العربية والإنجليزية والمظهر.
- أو افتح صفحة `Settings` واختر اللغة وLight أوDark أوSystem.
- عند اختيار العربية يتحول اتجاه التطبيق إلى RTL.
- تُحفظ الخيارات داخل المتصفح.

## الروابط

```text
التطبيق       http://localhost:3000
Swagger       http://localhost:8000/docs
API Health    http://localhost:8000/health
```

## تدريب النماذج الحقيقية

بعد نجاح التثبيت، شغّل:

```text
TRAIN_REAL_MODELS.bat
```

اختر MetroPT-3 أوKSDD أو الاثنين. سيحاول السكربت تنزيل البيانات الرسمية وتدريب النماذج ثم حفظها داخل `backend/ml/models`. أعد تشغيل التطبيق بعد انتهاء التدريب.

عند استخدام KSDD يجب الالتزام بترخيصها غير التجاري أو الحصول على إذن مناسب.

## التحقق

شغّل:

```text
VERIFY_PROJECT.bat
```

وهو ينفذ اختبارات الـBackend وفحص TypeScript وبناء Next.js الإنتاجي.

## حفظ البيانات

```text
backend/forgemind.db
backend/storage/inspections/
backend/storage/reports/
backend/ml/models/
```

لا تحذف `forgemind.db` إذا كنت تريد الاحتفاظ بالبيانات.

## نسخة احتياطية

```powershell
powershell -ExecutionPolicy Bypass -File scripts/BACKUP_LOCAL_DATA.ps1
```

## التشغيل اليدوي

CMD أول:

```bat
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python -m fastapi dev app/main.py --host 127.0.0.1 --port 8000
```

CMD ثانٍ:

```bat
cd frontend
npm ci
copy .env.example .env.local
npm run dev
```
