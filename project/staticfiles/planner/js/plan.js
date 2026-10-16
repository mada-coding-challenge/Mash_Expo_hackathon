/* صفحة خطتي: تاريخ اليوم، الساعة الحالية، إشعار المسار السريع */
(() => {

    /* ---- الساعة الحالية بصيغة 4:52 م ---- */
    const clock = document.getElementById("nowClock");

    const tick = () => {
        if (!clock) return;
        const d = new Date();
        const h = d.getHours();
        clock.textContent =
            `${h % 12 || 12}:${String(d.getMinutes()).padStart(2, "0")} ${h < 12 ? "ص" : "م"}`;
    };

    tick();
    setInterval(tick, 30000);


    /* ---- شارة التاريخ: "اليوم · 13 الثلاثاء" ---- */
    const chip = document.getElementById("dateChip");

    if (chip) {
        const d = new Date(chip.dataset.date + "T00:00:00");
        const now = new Date();
        const sameDay = d.toDateString() === now.toDateString();
        const weekday = new Intl.DateTimeFormat("ar-u-nu-latn", { weekday: "long" }).format(d);
        chip.textContent = `${sameDay ? "اليوم · " : ""}${d.getDate()} ${weekday}`;
    }


    /* ---- Toast: يظهر مرة واحدة لكل تصريح ثم يختفي ---- */
    const toast = document.getElementById("toast");

    if (toast) {
        const key = "mashi-pass-" + toast.dataset.key;
        let seen = false;

        try {
            seen = sessionStorage.getItem(key) === "1";
            sessionStorage.setItem(key, "1");
        } catch (_) { /* التخزين غير متاح */ }

        if (seen) {
            toast.remove();
        } else {
            setTimeout(() => {
                toast.classList.add("is-leaving");
                setTimeout(() => toast.remove(), 350);
            }, 4000);
        }
    }

})();
