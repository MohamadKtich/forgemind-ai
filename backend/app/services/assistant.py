from __future__ import annotations
from sqlalchemy import func
from sqlalchemy.orm import Session
from ..models import Alert, Inspection, Machine, MachinePrediction, MaintenanceRecord, ProductionRecord, SensorReading

ISSUE_AR={"bearing degradation":"تدهور المحمل","thermal overload":"حمل حراري زائد","tool wear":"تآكل الأداة","pressure instability":"عدم استقرار الضغط","speed imbalance":"عدم اتزان السرعة","normal operation":"تشغيل طبيعي"}
RISK_AR={"healthy":"سليم","warning":"تحذير","high":"مرتفع","critical":"حرج"}
PRIORITY_AR={"routine":"روتيني","planned":"مخطط","high":"مرتفع","immediate":"فوري"}


class AssistantService:
    def _snapshot(self, db: Session) -> dict:
        machines = db.query(Machine).filter(Machine.archived == False).all()
        ranked = []
        for machine in machines:
            prediction = db.query(MachinePrediction).filter(MachinePrediction.machine_id == machine.id).order_by(MachinePrediction.created_at.desc()).first()
            reading = db.query(SensorReading).filter(SensorReading.machine_id == machine.id).order_by(SensorReading.recorded_at.desc()).first()
            if prediction:
                ranked.append((machine, prediction, reading))
        ranked.sort(key=lambda row: row[1].failure_probability, reverse=True)
        produced, rejected, downtime = db.query(
            func.coalesce(func.sum(ProductionRecord.produced), 0),
            func.coalesce(func.sum(ProductionRecord.rejected), 0),
            func.coalesce(func.sum(ProductionRecord.downtime_minutes), 0),
        ).one()
        open_alerts = db.query(Alert).filter(Alert.acknowledged == False).count()
        open_maintenance = db.query(MaintenanceRecord).filter(MaintenanceRecord.status.in_(["open", "scheduled", "in_progress"])).count()
        latest_inspection = db.query(Inspection).order_by(Inspection.created_at.desc()).first()
        return {"machines":machines,"ranked":ranked,"produced":int(produced),"rejected":int(rejected),"downtime":float(downtime),"open_alerts":open_alerts,"open_maintenance":open_maintenance,"latest_inspection":latest_inspection}

    def answer(self, db: Session, question: str, locale: str = "en") -> dict:
        q=question.lower().strip();ar=locale=="ar";data=self._snapshot(db);ranked=data["ranked"]
        evidence={"machines_considered":len(ranked),"open_alerts":data["open_alerts"],"open_maintenance":data["open_maintenance"],"produced":data["produced"],"rejected":data["rejected"],"downtime_minutes":round(data["downtime"],1),"response_locale":locale}
        if not ranked:
            answer="لا توجد تنبؤات للآلات بعد. أرسل قراءة حساس أو شغّل محاكاة المصنع." if ar else "No machine predictions exist yet. Submit a sensor reading or start the factory simulation."
            return {"answer":answer,"evidence":evidence,"mode":"data-grounded"}
        top_machine,top_prediction,top_reading=ranked[0]
        specific=next(((m,p,r) for m,p,r in ranked if m.code.lower() in q or m.name.lower() in q),None)
        target_machine,target_prediction,target_reading=specific or (top_machine,top_prediction,top_reading)
        driver_items=target_prediction.explanation.get("top_drivers",[])[:4]
        drivers=", ".join(item["feature"].replace("_"," ") for item in driver_items)
        ar_drivers="، ".join({"temperature":"درجة الحرارة","vibration":"الاهتزاز","pressure":"الضغط","rpm":"سرعة الدوران","tool wear":"تآكل الأداة","torque":"العزم"}.get(item["feature"].replace("_"," "),item["feature"].replace("_"," ")) for item in driver_items)
        reason_words=["why","cause","risk","explain","لماذا","سبب","خطر","اشرح"]
        maintenance_words=["maintenance","priority","first","schedule","صيانة","أولوية","أولا","جدول"]
        production_words=["production","shift","today","summary","oee","إنتاج","وردية","اليوم","ملخص","الأداء"]
        quality_words=["defect","inspection","quality","reject","عيب","فحص","جودة","مرفوض"]
        compare_words=["compare","ranking","performance","best","worst","قارن","ترتيب","أفضل","أسوأ"]
        report_words=["report","executive","management","تقرير","تنفيذي","إدارة"]
        if any(word in q for word in reason_words):
            if ar:
                sensor_note=""
                if target_reading:sensor_note=f" أحدث القراءات: حرارة {target_reading.temperature:.1f}°م، واهتزاز {target_reading.vibration:.3f}، وضغط {target_reading.pressure:.1f}، وسرعة {target_reading.rpm:.0f} دورة/دقيقة."
                answer=(f"الآلة {target_machine.code} في مستوى خطر {RISK_AR.get(target_prediction.risk_level,target_prediction.risk_level)}، باحتمال عطل {target_prediction.failure_probability:.0%} ودرجة صحة {target_prediction.health_score:.0f}/100. "
                        f"المشكلة الأكثر احتمالًا هي {ISSUE_AR.get(target_prediction.likely_issue,target_prediction.likely_issue)}. أبرز العوامل: {ar_drivers or 'نمط الحساسات الأخير'}.{sensor_note} الإجراء الموصى به: {self._recommendation_ar(target_prediction.likely_issue)}")
            else:
                sensor_note=f" Latest readings: {target_reading.temperature:.1f}°C, vibration {target_reading.vibration:.3f}, pressure {target_reading.pressure:.1f}, and {target_reading.rpm:.0f} RPM." if target_reading else ""
                answer=(f"{target_machine.code} is currently {target_prediction.risk_level} risk with a {target_prediction.failure_probability:.0%} failure probability and a {target_prediction.health_score:.0f}/100 health score. The most likely issue is {target_prediction.likely_issue}. Primary drivers are {drivers or 'the latest sensor pattern'}.{sensor_note} Recommended action: {target_prediction.recommendation}")
        elif any(word in q for word in maintenance_words):
            if ar:
                lines=[f"{m.code}: {RISK_AR.get(p.risk_level,p.risk_level)}، صحة {p.health_score:.0f}/100، أولوية {PRIORITY_AR.get(p.maintenance_priority,p.maintenance_priority)}" for m,p,_ in ranked[:4]]
                answer=f"ابدأ بصيانة {top_machine.code}. {self._recommendation_ar(top_prediction.likely_issue)} ترتيب الأولوية الحالي: "+"؛ ".join(lines)+"."
            else:
                lines=[f"{m.code}: {p.risk_level}, health {p.health_score:.0f}/100, priority {p.maintenance_priority}" for m,p,_ in ranked[:4]];answer=f"Maintain {top_machine.code} first. {top_prediction.recommendation} Current priority order: "+"; ".join(lines)+"."
        elif any(word in q for word in production_words):
            reject_rate=data["rejected"]/data["produced"]*100 if data["produced"] else 0
            answer=(f"إجمالي الإنتاج المسجل {data['produced']} وحدة، منها {data['rejected']} مرفوضة، بنسبة رفض {reject_rate:.1f}%، ووقت توقف {data['downtime']:.1f} دقيقة. يوجد {data['open_alerts']} تنبيه مفتوح و{data['open_maintenance']} مهمة صيانة نشطة." if ar else f"Recorded production totals {data['produced']} units with {data['rejected']} rejects, a {reject_rate:.1f}% reject rate, and {data['downtime']:.1f} minutes of downtime. There are {data['open_alerts']} open alerts and {data['open_maintenance']} active maintenance tasks.")
        elif any(word in q for word in quality_words):
            inspection=data["latest_inspection"]
            if not inspection:answer="لم تُسجّل فحوصات بصرية. افتح مراقبة الجودة وافحص صورة منتج لإنشاء نتيجة قابلة للتتبع." if ar else "No visual inspections have been recorded. Open Quality Control and inspect a product image to create a traceable result."
            elif ar:answer=f"آخر فحص للمنتج {inspection.product_name} كانت نتيجته {'معيب' if inspection.status=='defective' else 'سليم'} بثقة {inspection.confidence:.0%} باستخدام {inspection.inspection_mode.replace('_',' ')}. العيوب المكتشفة: {'، '.join(inspection.defect_types) if inspection.defect_types else 'لا يوجد'}. درجة الشذوذ {inspection.anomaly_score:.0%}."
            else:answer=f"The latest inspection for {inspection.product_name} was {inspection.status} at {inspection.confidence:.0%} confidence using {inspection.inspection_mode.replace('_',' ')}. Detected defects: {', '.join(inspection.defect_types) if inspection.defect_types else 'none'}. The anomaly score was {inspection.anomaly_score:.0%}."
        elif any(word in q for word in compare_words):
            answer=("ترتيب مخاطر الآلات: "+"؛ ".join(f"{m.code} {p.health_score:.0f}/100 ({RISK_AR.get(p.risk_level,p.risk_level)})" for m,p,_ in ranked[:6])+"." if ar else "Machine risk ranking: "+"; ".join(f"{m.code} {p.health_score:.0f}/100 ({p.risk_level})" for m,p,_ in ranked[:6])+".")
        elif any(word in q for word in report_words):
            reject_rate=data["rejected"]/data["produced"]*100 if data["produced"] else 0
            answer=(f"الملخص التنفيذي: {len(data['machines'])} آلة نشطة، و{data['produced']} وحدة منتجة، ونسبة رفض {reject_rate:.1f}%، و{data['open_alerts']} تنبيه غير محلول. أعلى خطر للآلة {top_machine.code} بنسبة {top_prediction.failure_probability:.0%}. أنشئ النظرة التنفيذية من صفحة التقارير للحصول على ملف قابل للتنزيل." if ar else f"Executive summary: {len(data['machines'])} active machines, {data['produced']} units produced, {reject_rate:.1f}% reject rate, and {data['open_alerts']} unresolved alerts. Highest risk is {top_machine.code} at {top_prediction.failure_probability:.0%}. Generate the Executive Overview from Reports for a downloadable record.")
        else:
            answer=(f"يتابع ForgeMind عدد {len(data['machines'])} من الآلات. أعلى خطر حالي للآلة {top_machine.code} بنسبة {top_prediction.failure_probability:.0%}، مع {data['open_alerts']} تنبيه مفتوح. اسأل عن خطر آلة أو أولوية الصيانة أو أداء الإنتاج أو فحوصات الجودة أو الملخص التنفيذي." if ar else f"ForgeMind is tracking {len(data['machines'])} machines. The highest current risk is {top_machine.code} at {top_prediction.failure_probability:.0%}, with {data['open_alerts']} open alerts. Ask about a machine risk, maintenance priority, production performance, quality inspections, or an executive summary.")
        return {"answer":answer,"evidence":evidence,"mode":"data-grounded-local-engine"}

    @staticmethod
    def _recommendation_ar(issue:str)->str:
        return {"bearing degradation":"افحص حالة المحمل والتشحيم ومحاذاة العمود، وخفّض الحمل حتى يعود الاهتزاز إلى الحد المسموح.","thermal overload":"افحص تدفق التبريد والحمل الكهربائي وحرارة العملية قبل دورة الإنتاج التالية.","tool wear":"افحص الأداة أو استبدلها، وتحقق من حدود العزم وأعد المعايرة.","pressure instability":"افحص الأختام والمنظّم والصمامات ومصدر الضغط بحثًا عن تسرب أو انسداد.","speed imbalance":"افحص محاذاة الاقتران وأجزاء القيادة ووحدة التحكم في السرعة.","normal operation":"استمر بالمراقبة الدورية والصيانة الوقائية."}.get(issue,"نفّذ فحصًا هندسيًا للحالة قبل متابعة التشغيل.")


assistant_service=AssistantService()
