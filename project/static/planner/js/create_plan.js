/* ==========================================================
   معالج إنشاء الخطة (3 خطوات)
   1) الوقت  2) الاهتمامات  3) الأجنحة
   كل الخطوات داخل <form> واحد، والإرسال عادي (POST) للسيرفر.
========================================================== */

(() => {

    const $  = (sel, root = document) => root.querySelector(sel);
    const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

    /* ---------- ثوابت ---------- */
    const OPEN = 10 * 60;           // إكسبو يفتح 10:00 ص
    const CLOSE = 23 * 60;          // ويغلق 11:00 م
    const ITEM_H = 49;              // ارتفاع عنصر داخل العجلة (px)
    const HOURS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];
    const MINUTES = [0, 15, 30, 45];
    const PERIODS = ["ص", "م"];

    /* ---------- عناصر الصفحة ---------- */
    const steps = $$(".wizard-step");
    const bars = $$(".stepbar i");
    const nextBtn = $("#nextBtn");
    const backBtn = $("#backBtn");
    const footSummary = $("#footSummary");

    const startInput = $("#id_start_time");
    const endInput = $("#id_end_time");
    const dateHidden = $("#id_visit_date");

    let current = 0;


    /* ==========================================================
       الخطوة 1 — الوقت
    ========================================================== */

    // الحالة: الدقائق منذ منتصف الليل
    const time = { start: 16 * 60, end: 21 * 60 };

    // لو رجع الفورم بخطأ من السيرفر نستعيد القيم المرسلة
    const readHidden = (input, fallback) => {
        const m = /^(\d{1,2}):(\d{2})/.exec(input?.value || "");
        return m ? (+m[1]) * 60 + (+m[2]) : fallback;
    };

    time.start = readHidden(startInput, time.start);
    time.end = readHidden(endInput, time.end);

    // 570 -> { text: "9:30", period: "ص" }
    const to12 = (mins) => {
        const h24 = Math.floor(mins / 60) % 24;
        const m = mins % 60;
        return {
            text: `${h24 % 12 || 12}:${String(m).padStart(2, "0")}`,
            period: h24 < 12 ? "ص" : "م",
        };
    };

    const hhmm = (mins) =>
        `${String(Math.floor(mins / 60)).padStart(2, "0")}:${String(mins % 60).padStart(2, "0")}`;

    // مدة بالعربية: "5 ساعات" / "ساعتان" / "ساعة و30 د"
    const durationLabel = (mins) => {
        if (mins <= 0) return "—";
        const h = Math.floor(mins / 60);
        const m = mins % 60;
        let hl = "";
        if (h === 1) hl = "ساعة";
        else if (h === 2) hl = "ساعتان";
        else if (h >= 3 && h <= 10) hl = `${h} ساعات`;
        else if (h > 10) hl = `${h} ساعة`;
        if (!h) return `${m} د`;
        return m ? `${hl} و${m} د` : hl;
    };

    const pct = (mins) =>
        Math.min(100, Math.max(0, ((mins - OPEN) / (CLOSE - OPEN)) * 100));

    function renderTime() {

        const s = to12(time.start);
        const e = to12(time.end);

        $("#startText").innerHTML = `${s.text} <span>${s.period}</span>`;
        $("#endText").innerHTML = `${e.text} <span>${e.period}</span>`;

        const label = durationLabel(time.end - time.start);
        $("#durationBadge").textContent = label;
        $("#sheetDuration").textContent = label;

        $("#tabStart").textContent = `من · ${s.text} ${s.period}`;
        $("#tabEnd").textContent = `إلى · ${e.text} ${e.period}`;

        // الشريط الأخضر (RTL: البداية من اليمين)
        const fill = $("#rangeFill");
        const a = pct(time.start);
        const b = pct(time.end);
        fill.style.insetInlineStart = `${Math.min(a, b)}%`;
        fill.style.width = `${Math.max(0, b - a)}%`;

        // القيم المخفية التي يقرأها Django
        startInput.value = hhmm(time.start);
        endInput.value = hhmm(time.end);
    }

    function timeProblem() {
        const d = time.end - time.start;
        if (d < 30) return "وقت المغادرة يجب أن يكون بعد وقت الوصول بـ 30 دقيقة على الأقل.";
        if (d > 12 * 60) return "الحد الأقصى لمدة الزيارة 12 ساعة.";
        return "";
    }

    /* ---------- اختيار اليوم ---------- */

    const dayFmt = new Intl.DateTimeFormat("ar-u-nu-latn", { weekday: "long" });
    const shortFmt = new Intl.DateTimeFormat("ar-u-nu-latn", { day: "numeric", month: "long" });

    const iso = (d) =>
        `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

    const today = new Date();
    $("#chipToday").textContent = `اليوم · ${today.getDate()} ${dayFmt.format(today)}`;
    $("#dateInput").min = iso(today);

    function selectDay(date, chip) {
        dateHidden.value = iso(date);
        $$(".chip", $("#dayChips")).forEach((c) => c.classList.toggle("is-on", c === chip));
    }

    $$("#dayChips button.chip").forEach((btn) => {
        btn.addEventListener("click", () => {
            const d = new Date();
            d.setDate(d.getDate() + Number(btn.dataset.day));
            $("#customLabel").textContent = "اختر تاريخ";
            selectDay(d, btn);
        });
    });

    $("#chipCustom").addEventListener("click", () => {
        try { $("#dateInput").showPicker?.(); } catch (_) { /* بعض المتصفحات تمنعها */ }
    });

    $("#dateInput").addEventListener("change", (e) => {
        if (!e.target.value) return;
        const d = new Date(e.target.value + "T00:00:00");
        $("#customLabel").textContent = shortFmt.format(d);
        selectDay(d, $("#chipCustom"));
    });

    // القيمة الافتراضية: اليوم (أو ما رجع من السيرفر)
    if (dateHidden.value && dateHidden.value !== iso(today)) {
        const d = new Date(dateHidden.value + "T00:00:00");
        $("#customLabel").textContent = shortFmt.format(d);
        selectDay(d, $("#chipCustom"));
    } else {
        selectDay(today, $("#chipToday"));
    }


    /* ---------- Bottom sheet + العجلات ---------- */

    const wheels = {
        hour: $("#wheelHour"),
        minute: $("#wheelMinute"),
        period: $("#wheelPeriod"),
    };

    const fillWheel = (el, values, fmt = String) => {
        el.innerHTML = values.map((v) => `<div>${fmt(v)}</div>`).join("");
    };

    fillWheel(wheels.hour, HOURS);
    fillWheel(wheels.minute, MINUTES, (m) => String(m).padStart(2, "0"));
    fillWheel(wheels.period, PERIODS);

    let editing = "start";      // أي وقت نعدّله الآن
    let settingWheels = false;  // نمنع الحلقة عند تحريك العجلات برمجيًا

    const markSelected = (el, idx) =>
        [...el.children].forEach((c, i) => c.classList.toggle("is-sel", i === idx));

    function wheelIndex(el) {
        return Math.min(el.children.length - 1, Math.max(0, Math.round(el.scrollTop / ITEM_H)));
    }

    // ضبط العجلات على قيمة معينة (بالدقائق)
    function syncWheels(mins) {
        const h24 = Math.floor(mins / 60) % 24;
        const idxH = HOURS.indexOf(h24 % 12 || 12);
        const idxM = Math.max(0, MINUTES.indexOf(mins % 60));
        const idxP = h24 < 12 ? 0 : 1;

        settingWheels = true;
        wheels.hour.scrollTop = idxH * ITEM_H;
        wheels.minute.scrollTop = idxM * ITEM_H;
        wheels.period.scrollTop = idxP * ITEM_H;
        markSelected(wheels.hour, idxH);
        markSelected(wheels.minute, idxM);
        markSelected(wheels.period, idxP);
        setTimeout(() => { settingWheels = false; }, 120);
    }

    // قراءة العجلات وتحديث الحالة
    function readWheels() {
        const idxH = wheelIndex(wheels.hour);
        const idxM = wheelIndex(wheels.minute);
        const idxP = wheelIndex(wheels.period);

        markSelected(wheels.hour, idxH);
        markSelected(wheels.minute, idxM);
        markSelected(wheels.period, idxP);

        const h = HOURS[idxH] % 12 + (idxP === 1 ? 12 : 0);
        time[editing] = h * 60 + MINUTES[idxM];
        renderTime();
    }

    Object.values(wheels).forEach((el) => {
        let t;
        el.addEventListener("scroll", () => {
            if (settingWheels) return;
            clearTimeout(t);
            t = setTimeout(readWheels, 90);
        });
    });

    function setEditing(which) {
        editing = which;
        $("#tabStart").classList.toggle("is-on", which === "start");
        $("#tabEnd").classList.toggle("is-on", which === "end");
        $("#boxStart").classList.toggle("is-active", which === "start");
        $("#boxEnd").classList.toggle("is-active", which === "end");
        $("#sheetTitle").textContent = which === "start" ? "وقت الوصول" : "وقت المغادرة";
        syncWheels(time[which]);
    }

    function openSheet(which) {
        document.body.classList.add("sheet-open");
        setEditing(which);
    }

    function closeSheet() {
        document.body.classList.remove("sheet-open");
        const msg = timeProblem();
        const box = $("#timeError");
        box.hidden = !msg;
        box.textContent = msg;
    }

    $("#boxStart").addEventListener("click", () => openSheet("start"));
    $("#boxEnd").addEventListener("click", () => openSheet("end"));
    $("#tabStart").addEventListener("click", () => setEditing("start"));
    $("#tabEnd").addEventListener("click", () => setEditing("end"));
    $("#sheetDone").addEventListener("click", closeSheet);
    $("#sheetClose").addEventListener("click", closeSheet);
    $("#sheetBackdrop").addEventListener("click", closeSheet);
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") closeSheet();
    });


    /* ==========================================================
       الخطوة 2 — الاهتمامات (التحقق فقط، العرض من القالب)
    ========================================================== */

    const pickedInterests = () =>
        $$('input[name="interests"]:checked');

    $$('input[name="interests"]').forEach((i) =>
        i.addEventListener("change", () => {
            $("#interestError").hidden = pickedInterests().length > 0;
        })
    );


    /* ==========================================================
       الخطوة 3 — الأجنحة + الاقتراحات
    ========================================================== */

    const list = $("#pavList");
    const pavItems = $$(".pav-item", list);
    let userTouched = false;     // هل غيّر المستخدم الاختيار يدويًا؟
    let autoChecked = [];        // ما حددناه نحن تلقائيًا

    const pavChecks = () => $$('input[name="favorite_pavilions"]');

    function updateCount() {
        $("#pickCount").textContent = pavChecks().filter((c) => c.checked).length;
    }

    pavChecks().forEach((c) =>
        c.addEventListener("change", () => {
            userTouched = true;
            updateCount();
        })
    );

    // اقتراح أجنحة تتقاطع اهتماماتها مع ما اختاره المستخدم
    function computeSuggestions() {

        const picked = pickedInterests().map((i) => i.closest("label").dataset.name);

        // إلغاء ما حددناه تلقائيًا سابقًا (إن لم يلمسه المستخدم)
        if (!userTouched) {
            autoChecked.forEach((c) => (c.checked = false));
        }
        autoChecked = [];
        pavItems.forEach((it) => it.classList.remove("is-suggested"));

        const scored = pavItems
            .map((it) => {
                const names = it.dataset.interests.split(",").filter(Boolean);
                const common = names.filter((n) => picked.includes(n));
                return { it, common, score: common.length };
            })
            .filter((x) => x.score > 0)
            .sort((a, b) => b.score - a.score)
            .slice(0, 2);

        const banner = $("#aiBanner");

        if (!scored.length) {
            banner.hidden = true;
            updateCount();
            return;
        }

        // الأعلى توافقًا يظهر أولًا في القائمة
        [...scored].reverse().forEach(({ it }) => list.prepend(it));

        scored.forEach(({ it }) => {
            it.classList.add("is-suggested");
            const box = $("input", it);
            if (!userTouched && !box.checked) {
                box.checked = true;
                autoChecked.push(box);
            }
        });

        const names = scored.map(({ it }) => it.dataset.name).join(" و");
        const because = [...new Set(scored.flatMap((x) => x.common))].slice(0, 2).join(" و");

        $("#aiBannerText").textContent = `اقترحنا ${names} لأنك اخترت «${because}».`;
        banner.hidden = false;
        updateCount();
    }

    // البحث
    $("#pavSearch").addEventListener("input", (e) => {
        const q = e.target.value.trim();
        let visible = 0;
        pavItems.forEach((it) => {
            const hit = !q || it.dataset.name.includes(q) || it.dataset.interests.includes(q);
            it.hidden = !hit;
            if (hit) visible++;
        });
        $("#emptySearch").hidden = visible > 0;
    });

    // Enter داخل البحث لا يرسل الفورم
    $("#pavSearch").addEventListener("keydown", (e) => {
        if (e.key === "Enter") e.preventDefault();
    });

    // زر الفلتر: عرض المحدد فقط
    $("#onlySelected").addEventListener("click", (e) => {
        const on = list.classList.toggle("only-selected");
        e.currentTarget.classList.toggle("is-on", on);
    });


    /* ==========================================================
       التنقل بين الخطوات
    ========================================================== */

    function go(n) {

        current = n;

        steps.forEach((s, i) => (s.hidden = i !== n));
        bars.forEach((b, i) => b.classList.toggle("on", i <= n));

        backBtn.style.visibility = n === 0 ? "hidden" : "visible";
        footSummary.hidden = n !== 2;

        if (n === 2) {
            nextBtn.className = "btn btn-purple";
            nextBtn.innerHTML = '<svg class="ic"><use href="#i-sparkle"/></svg>ابنِ خطتي';
            computeSuggestions();
        } else {
            nextBtn.className = "btn";
            nextBtn.textContent = "متابعة";
        }

        window.scrollTo({ top: 0, behavior: "smooth" });
    }

    nextBtn.addEventListener("click", () => {

        if (current === 0) {
            const msg = timeProblem();
            const box = $("#timeError");
            box.hidden = !msg;
            box.textContent = msg;
            if (msg) return;
            go(1);
        }

        else if (current === 1) {
            if (!pickedInterests().length) {
                $("#interestError").hidden = false;
                return;
            }
            go(2);
        }

        else {
            nextBtn.disabled = true;
            $("#wizard").submit();
        }
    });

    backBtn.addEventListener("click", () => current > 0 && go(current - 1));

    // البداية
    renderTime();
    updateCount();

    // لو رجع الفورم بأخطاء الاهتمامات نبدأ من الخطوة المناسبة
    if ($(".form-errors") && !pickedInterests().length && time.end - time.start >= 30) {
        go(1);
    }

})();
