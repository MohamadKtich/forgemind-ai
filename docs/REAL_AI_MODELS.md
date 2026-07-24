# نماذج ForgeMind المبنية على بيانات صناعية حقيقية

## حالة التشغيل

يعرض ForgeMind مصدر كل نموذج وحالته من صفحة **AI Models** ومن `GET /api/models/status`:

- **Generic fallback:** مرفق ويعمل لجميع أنواع الآلات، لكنه مدرّب على Benchmark مولّد وليس قياسات مصنع.
- **MetroPT-3:** يُستخدم فقط للضواغط وAPU بعد وجود ملف الوزن الحقيقي.
- **KolektorSDD:** يُستخدم لفحص الجودة بعد وجود ملف الوزن الحقيقي.
- عند غياب الوزن، تظهر حالة fallback صراحة.

## MetroPT-3

المسار يقرأ CSV الحقيقي على دفعات، ويجمّعه إلى نوافذ دقيقة، ويبني هدفًا من تقارير الأعطال المنشورة، ثم يستخدم تقسيمًا زمنيًا يمنع تسرب المستقبل:

- قبل يونيو 2020: تدريب، ويشمل الحدثين الأول والثاني.
- يونيو 2020: تحقق، ويشمل الحدث الثالث.
- يوليو وما بعده: اختبار محتجز، ويشمل الحدث الرابع.

تتم مقارنة:

- Logistic Regression.
- Random Forest.
- Histogram Gradient Boosting.

ويتم اختيار Decision threshold على Validation، ثم حفظ مقاييس الاختبار والـConfusion Matrix وROC.

```bat
cd backend
.venv\Scripts\activate
python ml\train_metropt.py "C:\datasets\MetroPT3(AirCompressor).csv"
```

النواتج:

```text
ml/models/metropt_air_compressor.joblib
ml/models/metropt_air_compressor.metadata.json
ml/reports/metropt/confusion_matrix.png
ml/reports/metropt/roc_curve.png
```

## KolektorSDD

المسار يقرأ الصور والأقنعة، ويستخرج HOG وTexture وEdge وIntensity وHSV features، ويقارن:

- Logistic Regression.
- Random Forest.
- Extra Trees.

يوفر النموذج احتمال العيب على مستوى الصورة، بينما تحدد طبقة الرؤية مناطق العيب وترسم Bounding Boxes. هذا تصميم CPU-friendly، وليس ادعاء أن كل لابتوب تحول فجأة إلى عنقود GPU.

```bat
cd backend
.venv\Scripts\activate
python ml\train_ksdd.py "C:\datasets\KolektorSDD"
```

النواتج:

```text
ml/models/quality_inspector.joblib
ml/models/quality_inspector.metadata.json
ml/reports/quality/confusion_matrix.png
ml/reports/quality/roc_curve.png
```

KSDD مرخصة CC BY-NC-SA 4.0. الاستخدام التجاري يحتاج الالتزام بالشروط أو إذنًا من أصحاب البيانات.

## التدريب بنقرة واحدة

شغّل `TRAIN_REAL_MODELS.bat` بعد `SETUP_WINDOWS.bat` على جهاز متصل بالإنترنت. يمكن أيضًا تنزيل البيانات يدويًا وتشغيل السكربتات بالأوامر أعلاه.

## اختبار عقود التدريب

تحتوي السكربتات على `--quick` للتحقق من أن القراءة والتقسيم والتدريب والحفظ والرسوم تعمل على Fixture صغيرة. لا تستخدم `--quick` لإنتاج الأوزان النهائية.

## شرط الإنتاج

حتى بعد التدريب على بيانات عامة حقيقية، يجب إعادة المعايرة أو التدريب على صور وحساسات المصنع المستهدف، لأن اختلاف الكاميرا والإضاءة وعائلة المعدة وتعريف العطل يمكنه تحويل رقم جميل في التقرير إلى قرار سيئ مكلف جدًا.
