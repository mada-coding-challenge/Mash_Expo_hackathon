# تشغيل واجهة mashi مع الباك اند

## اللي تغيّر
- واجهات mashi صارت داخل مشروع الباك اند:
  - `templates/mashi/index.html` — صفحة التطبيق
  - `static/mashi/app.js` — كل الشاشات ومنطقها
  - `static/mashi/img/` — صور الأجنحة
- `mashi_web/` — طبقة API بصيغة JSON تربط الواجهة بدوال `planner/views.py` الموجودة.
- `project/urls.py`: صارت واجهة mashi هي الصفحة الرئيسية `/`، والواجهة القديمة لإنشاء الخطة انتقلت إلى `/old/`.
- ما فيه أي تعديل على `planner/` ولا الموديلات ولا قاعدة البيانات ولا `settings.py`.

## طريقة التشغيل
```bash
cd project
python -m venv venv
# ويندوز: venv\Scripts\activate    |   ماك/لينكس: source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```
بعدها افتح:
- تطبيق mashi: http://127.0.0.1:8000/
- الواجهة القديمة: http://127.0.0.1:8000/old/

مهم: شغّل السيرفر من المجلد الجديد، وأوقف أي سيرفر قديم شغّال (Ctrl+C) قبل التشغيل.

## ملاحظات
- «سجّل وصولك» يستخدم موقع الجهاز. المتصفح يسمح بالموقع فقط على `localhost` أو `https`.
  لو فتحتها من الجوال عبر IP الشبكة، استخدم زر «محاكاة الوصول (وضع العرض)»، وهو يظهر لأن `DEMO_MODE = True`.
- مدة زيارة التحدي في وضع العرض 10 ثواني (`DEMO_CHALLENGE_SECONDS`).
- رابط QR في المسار السريع يُبنى من `DEMO_BASE_URL` في `settings.py`. غيّره لعنوان جهازك عشان يشتغل المسح من الجوال.
- الخطة محفوظة في الجلسة (session)، فلو حدّثت الصفحة ترجع لخطتك.

## روابط الـ API (تحت /api/)
| الطريقة | المسار | الوظيفة |
|---|---|---|
| GET | bootstrap/ | الاهتمامات + الأجنحة + الخطة الحالية |
| POST | plans/ | بناء خطة (create_plan + موديل الاهتمامات) |
| GET | plans/<id>/ | تفاصيل الخطة |
| POST | plan-items/<id>/complete/ | إنهاء زيارة جناح |
| POST | plans/<id>/challenge/ | بدء تحدي «اكتشف واكسب» |
| GET | challenges/<id>/ | حالة التحدي |
| POST | challenge-visits/<id>/location/ | تسجيل وصول بالموقع |
| POST | challenge-visits/<id>/arrive/ | محاكاة الوصول (وضع العرض) |
| POST | challenge-visits/<id>/check/ | التحقق من انتهاء مدة الزيارة |
| GET | passes/<code>/ | تذكرة المسار السريع + QR |
| POST | passes/<code>/use/ | استخدام التذكرة |
