import math

from math import radians, sin, cos, sqrt, atan2

from .models import Pavilion

# متوسط سرعة المشي بالمتر في الدقيقة
WALKING_SPEED_METERS_PER_MINUTE = 80


def calculate_distance(
    lat1,
    lon1,
    lat2,
    lon2
):
    """
    تحسب المسافة المباشرة بين موقعين بالمتر.
    """

    earth_radius = 6371

    lat1 = radians(float(lat1))
    lon1 = radians(float(lon1))

    lat2 = radians(float(lat2))
    lon2 = radians(float(lon2))

    difference_lat = lat2 - lat1
    difference_lon = lon2 - lon1

    a = (
        sin(difference_lat / 2) ** 2
        + cos(lat1)
        * cos(lat2)
        * sin(difference_lon / 2) ** 2
    )

    c = 2 * atan2(
        sqrt(a),
        sqrt(1 - a)
    )

    distance_km = earth_radius * c

    distance_meters = distance_km * 1000

    return round(distance_meters)


def calculate_walking_time(distance_meters):
    """
    تحول المسافة بالمتر إلى وقت مشي تقريبي بالدقائق.
    """

    walking_minutes = (
        distance_meters
        / WALKING_SPEED_METERS_PER_MINUTE
    )

    return math.ceil(walking_minutes)


def pavilion_travel_info(
    pavilion1,
    pavilion2
):
    """
    تحسب المسافة ووقت المشي بين جناحين.
    """

    if (
        pavilion1.latitude is None
        or pavilion1.longitude is None
        or pavilion2.latitude is None
        or pavilion2.longitude is None
    ):
        return {
            "distance": 0,
            "walking_time": 0
        }

    distance = calculate_distance(
        pavilion1.latitude,
        pavilion1.longitude,
        pavilion2.latitude,
        pavilion2.longitude
    )

    walking_time = calculate_walking_time(
        distance
    )

    return {
        "distance": distance,
        "walking_time": walking_time
    }


def get_interest_score(
    pavilion,
    selected_interest_ids
):
    """
    تحسب عدد الاهتمامات المشتركة بين
    المستخدم والجناح.
    """

    pavilion_interest_ids = set(
        pavilion.interests.values_list(
            "id",
            flat=True
        )
    )

    selected_interest_ids = set(
        selected_interest_ids
    )

    matching_interests = (
        pavilion_interest_ids
        & selected_interest_ids
    )

    return len(matching_interests)


def create_visit_plan(
    pavilions,
    selected_interests,
    favorite_pavilions,
    available_minutes
):
    """
    تنشئ خطة زيارة بدون AI.

    الأولوية:
    1. الأجنحة المفضلة.
    2. عدد الاهتمامات المشتركة.
    3. قرب الجناح من الجناح الحالي.
    4. عدم تجاوز الوقت المتاح.
    """

    selected_interest_ids = list(
        selected_interests.values_list(
            "id",
            flat=True
        )
    )

    favorite_ids = set(
        favorite_pavilions.values_list(
            "id",
            flat=True
        )
    )

    remaining_pavilions = list(pavilions)

    plan = []

    total_visit_time = 0
    total_walking_time = 0

    current_pavilion = None

    while remaining_pavilions:

        possible_pavilions = []

        for pavilion in remaining_pavilions:

            interest_score = get_interest_score(
                pavilion,
                selected_interest_ids
            )

            is_favorite = (
                pavilion.id in favorite_ids
            )

            # إذا كان أول جناح فلا يوجد مشي قبله
            if current_pavilion is None:

                travel_info = {
                    "distance": 0,
                    "walking_time": 0
                }

            else:

                travel_info = pavilion_travel_info(
                    current_pavilion,
                    pavilion
                )

            required_time = (
                pavilion.recommended_duration
                + travel_info["walking_time"]
            )

            current_total = (
                total_visit_time
                + total_walking_time
            )

            # هل يوجد وقت كافٍ لإضافة هذا الجناح؟
            if (
                current_total + required_time
                <= available_minutes
            ):

                possible_pavilions.append({
                    "pavilion": pavilion,
                    "favorite": is_favorite,
                    "interest_score": interest_score,
                    "distance": travel_info["distance"],
                    "walking_time": travel_info["walking_time"]
                })

        # لا يوجد أي جناح آخر يناسب الوقت المتبقي
        if not possible_pavilions:
            break

        # ترتيب الخيارات:
        # المفضل أولاً
        # ثم الأكثر توافقاً مع الاهتمامات
        # ثم الأقرب
        possible_pavilions.sort(
            key=lambda item: (
                not item["favorite"],
                -item["interest_score"],
                item["distance"]
            )
        )

        selected = possible_pavilions[0]

        pavilion = selected["pavilion"]

        total_walking_time += (
            selected["walking_time"]
        )

        total_visit_time += (
            pavilion.recommended_duration
        )

        plan.append({
            "pavilion": pavilion,
            "is_favorite": selected["favorite"],
            "interest_score":
                selected["interest_score"],
            "distance":
                selected["distance"],
            "walking_time":
                selected["walking_time"],
            "visit_duration":
                pavilion.recommended_duration
        })

        current_pavilion = pavilion

        remaining_pavilions.remove(
            pavilion
        )

    total_time = (
        total_visit_time
        + total_walking_time
    )

    remaining_time = (
        available_minutes
        - total_time
    )

    return {
        "items": plan,

        "available_time":
            available_minutes,

        "visit_time":
            total_visit_time,

        "walking_time":
            total_walking_time,

        "total_time":
            total_time,

        "remaining_time":
            remaining_time
    }
    
def create_ai_visit_plan(
    pavilions,
    ai_recommendations,
    available_minutes
):

    pavilion_dictionary = {
        pavilion.id: pavilion
        for pavilion in pavilions
    }

    plan = []

    total_visit_time = 0
    total_walking_time = 0

    current_pavilion = None

    used_ids = set()

    for recommendation in ai_recommendations:

        pavilion_id = (
            recommendation.pavilion_id
        )

        # حماية من ID غير موجود
        if pavilion_id not in pavilion_dictionary:
            continue

        # منع التكرار
        if pavilion_id in used_ids:
            continue

        pavilion = pavilion_dictionary[
            pavilion_id
        ]

        if current_pavilion is None:

            travel_info = {
                "distance": 0,
                "walking_time": 0
            }

        else:

            travel_info = pavilion_travel_info(
                current_pavilion,
                pavilion
            )

        required_time = (
            pavilion.recommended_duration
            + travel_info["walking_time"]
        )

        current_total = (
            total_visit_time
            + total_walking_time
        )

        # إذا لم يتسع الوقت لهذا الجناح
        # نتجاوزه ونحاول الجناح التالي
        if (
            current_total + required_time
            > available_minutes
        ):
            continue

        total_visit_time += (
            pavilion.recommended_duration
        )

        total_walking_time += (
            travel_info["walking_time"]
        )

        plan.append({
            "pavilion": pavilion,

            "reason":
                recommendation.reason,

            "distance":
                travel_info["distance"],

            "walking_time":
                travel_info["walking_time"],

            "visit_duration":
                pavilion.recommended_duration
        })

        used_ids.add(
            pavilion.id
        )

        current_pavilion = pavilion

    total_time = (
        total_visit_time
        + total_walking_time
    )

    return {
        "items": plan,

        "available_time":
            available_minutes,

        "visit_time":
            total_visit_time,

        "walking_time":
            total_walking_time,

        "total_time":
            total_time,

        "remaining_time":
            available_minutes - total_time
    }
    
def get_challenge_pavilions(
    crowded_pavilion
):
    return (

        Pavilion.objects
        .filter(
            is_active=True,
            crowd_level=Pavilion.CrowdLevel.LOW
        )
        .exclude(
            id=crowded_pavilion.id
        )
        [:3]
    )
    
def get_challenge_pavilions(plan, crowded_pavilion):

    # Pavilions already visited in the normal plan
    visited_ids = plan.items.filter(
        is_visited=True
    ).values_list(
        "pavilion_id",
        flat=True
    )

    # Find less crowded pavilions
    candidates = (
        Pavilion.objects
        .filter(is_active=True)
        .exclude(crowd_level=Pavilion.CrowdLevel.HIGH)
        .exclude(id=crowded_pavilion.id)
        .exclude(id__in=visited_ids)
    )

    return list(candidates[:3])

CHALLENGE_RADIUS_METERS = 100


def is_user_near_pavilion(
    user_latitude,
    user_longitude,
    pavilion
):
    if (
        pavilion.latitude is None
        or pavilion.longitude is None
    ):
        return False, None

    distance = calculate_distance(
        user_latitude,
        user_longitude,
        pavilion.latitude,
        pavilion.longitude
    )

    is_near = (
        distance <= CHALLENGE_RADIUS_METERS
    )

    return is_near, distance


# ==========================================
# Schedule (أوقات المحطات في صفحة خطتي)
# ==========================================

def _clock(total_minutes):
    """يحول الدقائق منذ منتصف الليل إلى ('4:50', 'م')."""

    total_minutes %= 24 * 60

    hour24, minute = divmod(total_minutes, 60)

    period = "ص" if hour24 < 12 else "م"

    hour12 = hour24 % 12 or 12

    return f"{hour12}:{minute:02d}", period


def format_time_range(start, end):
    """4:00 – 9:00 م  (تُستخدم في بطاقة وقت الزيارة)."""

    if not start or not end:
        return ""

    s_label, s_period = _clock(start.hour * 60 + start.minute)
    e_label, e_period = _clock(end.hour * 60 + end.minute)

    if s_period == e_period:
        return f"{s_label} – {e_label} {e_period}"

    return f"{s_label} {s_period} – {e_label} {e_period}"


def build_schedule(plan, items):
    """
    تحسب وقت بداية كل محطة:
    بداية الزيارة + مدة الأجنحة السابقة + وقت المشي بينها.
    """

    cursor = (
        plan.start_time.hour * 60 + plan.start_time.minute
        if plan.start_time
        else 10 * 60
    )

    rows = []
    previous = None

    for item in items:

        walk = 0

        if previous is not None:
            walk = pavilion_travel_info(
                previous.pavilion,
                item.pavilion
            )["walking_time"]

        cursor += walk

        label, period = _clock(cursor)

        rows.append({
            "item": item,
            "clock": label,
            "period": period,
            "walk": walk,
        })

        cursor += item.pavilion.recommended_duration

        previous = item

    return rows


def duration_label(minutes):
    """90 -> 'ساعة و30 د' ، 300 -> '5 ساعات'."""

    hours, mins = divmod(int(minutes), 60)

    if hours == 0:
        return f"{mins} د"

    if hours == 1:
        hours_label = "ساعة"
    elif hours == 2:
        hours_label = "ساعتان"
    elif hours <= 10:
        hours_label = f"{hours} ساعات"
    else:
        hours_label = f"{hours} ساعة"

    return f"{hours_label} و{mins} د" if mins else hours_label


# ==========================================
# Smart plan (موديل الاهتمامات + الوقت + المسافات)
# ==========================================

# أقصى خصم على درجة الجناح بسبب المشي الإضافي لإضافته
DISTANCE_PENALTY = 0.3
# المشي الإضافي (بالدقائق) الذي يصل عنده الخصم إلى أقصاه
DISTANCE_PENALTY_MINUTES = 15


class _WalkCache:
    """يحفظ أوقات المشي بين الأجنحة حتى لا تُحسب أكثر من مرة."""

    def __init__(self):
        self._cache = {}

    def __call__(self, a, b):
        key = (a.id, b.id) if a.id < b.id else (b.id, a.id)

        if key not in self._cache:
            self._cache[key] = pavilion_travel_info(a, b)

        return self._cache[key]


def _route_walking(route, walk):
    return sum(
        walk(route[i], route[i + 1])["walking_time"]
        for i in range(len(route) - 1)
    )


def _route_total(route, walk):
    return (
        sum(p.recommended_duration for p in route)
        + _route_walking(route, walk)
    )


def _two_opt(route, walk):
    """
    يعيد ترتيب الأجنحة لتقليل المشي (مسار مفتوح: لا نعود لنقطة البداية).
    مدة زيارة الأجنحة ثابتة، فالترتيب يؤثر على وقت المشي فقط.
    """

    if len(route) < 3:
        return route

    best = list(route)
    best_walk = _route_walking(best, walk)
    improved = True

    while improved:
        improved = False

        for i in range(len(best) - 1):
            for j in range(i + 1, len(best)):

                candidate = best[:i] + best[i:j + 1][::-1] + best[j + 1:]
                candidate_walk = _route_walking(candidate, walk)

                if candidate_walk < best_walk:
                    best, best_walk = candidate, candidate_walk
                    improved = True

    return best


def _cheapest_insertion(route, pavilion, walk):
    """أفضل موضع لإدخال الجناح في المسار، والمشي الإضافي الناتج."""

    if not route:
        return 0, 0

    base = _route_walking(route, walk)
    best_position, best_extra = None, None

    for position in range(len(route) + 1):
        candidate = route[:position] + [pavilion] + route[position:]
        extra = _route_walking(candidate, walk) - base

        if best_extra is None or extra < best_extra:
            best_position, best_extra = position, extra

    return best_position, best_extra


def create_smart_visit_plan(
    pavilions,
    scores,
    reasons,
    must_visit_ids,
    available_minutes,
    min_score=0.0
):
    """
    تبني خطة تراعي الاهتمامات والوقت والمسافات:

    1. الأجنحة التي اختارها المستخدم تدخل أولاً (الأعلى درجة أولاً)
       ما دام الوقت يكفي.
    2. ثم نضيف بقية الأجنحة: في كل خطوة نختار الجناح ذا القيمة الأعلى، حيث
       القيمة = درجة الموديل مع خصم بسيط إذا كان بعيدًا عن المسار،
       ونُدخله في الموضع الذي يضيف أقل مشي، بشرط ألا نتجاوز الوقت المتاح.
    3. بعد كل إضافة نعيد ترتيب المسار (2-opt) لتقليل المشي الكلي.
    """

    walk = _WalkCache()
    must_visit_ids = set(must_visit_ids)

    route = []
    skipped = []

    # ---- 1) الأجنحة المختارة ----
    must_visit = sorted(
        (p for p in pavilions if p.id in must_visit_ids),
        key=lambda p: -scores.get(p.id, 0)
    )

    for pavilion in must_visit:

        position, _ = _cheapest_insertion(route, pavilion, walk)
        candidate = _two_opt(
            route[:position] + [pavilion] + route[position:],
            walk
        )

        if _route_total(candidate, walk) <= available_minutes:
            route = candidate
        else:
            skipped.append(pavilion)

    # ---- 2) إكمال الوقت بأفضل الأجنحة حسب الموديل ----
    candidates = [
        p for p in pavilions
        if p.id not in must_visit_ids
        and scores.get(p.id, 0) > min_score
    ]

    while candidates:

        used = _route_total(route, walk)
        best = None

        for pavilion in candidates:

            position, extra_walk = _cheapest_insertion(route, pavilion, walk)

            if used + pavilion.recommended_duration + extra_walk > available_minutes:
                continue

            penalty = DISTANCE_PENALTY * min(
                extra_walk / DISTANCE_PENALTY_MINUTES, 1
            )
            value = scores.get(pavilion.id, 0) * (1 - penalty)

            if best is None or value > best[0]:
                best = (value, pavilion, position)

        if best is None:
            break

        _, pavilion, position = best

        route = _two_opt(
            route[:position] + [pavilion] + route[position:],
            walk
        )
        candidates.remove(pavilion)

    # ---- 3) تجهيز النتيجة ----
    items = []
    total_walking_time = 0
    previous = None

    for pavilion in route:

        travel = (
            walk(previous, pavilion)
            if previous is not None
            else {"distance": 0, "walking_time": 0}
        )

        total_walking_time += travel["walking_time"]

        is_chosen = pavilion.id in must_visit_ids

        items.append({
            "pavilion": pavilion,
            "is_favorite": is_chosen,
            "score": scores.get(pavilion.id, 0),
            "reason": (
                "اخترته ضمن الأجنحة التي تريد زيارتها"
                if is_chosen
                else reasons.get(pavilion.id, "")
            ),
            "distance": travel["distance"],
            "walking_time": travel["walking_time"],
            "visit_duration": pavilion.recommended_duration,
        })

        previous = pavilion

    total_visit_time = sum(p.recommended_duration for p in route)
    total_time = total_visit_time + total_walking_time

    return {
        "items": items,
        "skipped": skipped,
        "available_time": available_minutes,
        "visit_time": total_visit_time,
        "walking_time": total_walking_time,
        "total_time": total_time,
        "remaining_time": available_minutes - total_time,
    }
