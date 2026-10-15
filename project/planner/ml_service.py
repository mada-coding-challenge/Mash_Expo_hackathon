"""
ربط موديل الاهتمامات (interest_model.joblib) بقاعدة البيانات.

الموديل يعمل على 7 أبعاد اهتمام ثابتة:
    tech, heritage, sustainability, family, food, entertainment, global

بينما قاعدة البيانات فيها اهتمامات عربية (التقنية، الفضاء، الطعام ...).
هذا الملف يترجم بين العالمين:

1. كل Interest في القاعدة له حقل model_weights يحدد وزنه على الأبعاد السبعة
   (يُعدَّل من لوحة الإدارة).
2. كل Pavilion يُحسب له "متجه وسوم" من اهتماماته المرتبطة به في القاعدة.
3. نبني مدخلات الموديل (20 رقمًا) من اختيارات المستخدم، فيُرجع الموديل
   ملف اهتمامات الزائر المتوقع (7 أرقام).
4. درجة كل جناح = تطابق متجه الجناح مع ملف الزائر + تطابق مباشر مع
   الاهتمامات العربية التي اختارها.

مدخلات الموديل (بنفس ترتيب التدريب):
    [0:7]   الاستبيان: 1 لأقوى 3 أبعاد اختارها المستخدم
    [7]     الفئة العمرية (0..4)
    [8]     عدد ساعات الزيارة (2..8)
    [9:13]  نوع المجموعة: solo, couple, family, friends
    [13:20] متوسط وسوم الأجنحة التي اختارها المستخدم

الملف يحوي 3 موديلات: 0 = بدون أجنحة مختارة، 1 = جناح واحد، 2 = جناحان فأكثر.
"""

from functools import lru_cache
import logging

from django.conf import settings

logger = logging.getLogger(__name__)

MODEL_DIMENSIONS = [
    "tech",
    "heritage",
    "sustainability",
    "family",
    "food",
    "entertainment",
    "global",
]

DIMENSION_LABELS_AR = {
    "tech": "التقنية والابتكار",
    "heritage": "الثقافة والتراث",
    "sustainability": "الاستدامة",
    "family": "العائلة",
    "food": "الطعام",
    "entertainment": "الترفيه",
    "global": "الثقافات العالمية",
}

GROUP_TYPES = ["solo", "couple", "family", "friends"]

# الوزن الافتراضي لكل اهتمام في القاعدة (يُستخدم في الـ migration،
# وكاحتياط إذا كان حقل model_weights فارغًا)
DEFAULT_INTEREST_WEIGHTS = {
    "التقنية": {"tech": 1.0},
    "الذكاء الاصطناعي": {"tech": 1.0},
    "الابتكار": {"tech": 0.8, "global": 0.3},
    "الفضاء": {"tech": 1.0, "entertainment": 0.3},
    "الاستدامة": {"sustainability": 1.0},
    "الطاقة": {"sustainability": 0.8, "tech": 0.4},
    "البيئة": {"sustainability": 1.0},
    "الثقافة": {"heritage": 0.7, "global": 0.8},
    "التاريخ والتراث": {"heritage": 1.0},
    "الفنون": {"heritage": 0.7, "entertainment": 0.4},
    "الصحة": {"family": 0.5, "sustainability": 0.4},
    "الترفيه": {"entertainment": 1.0, "family": 0.5},
    "الألعاب": {"entertainment": 1.0, "family": 0.6},
    "الطعام": {"food": 1.0, "global": 0.3},
    "التسوق": {"entertainment": 0.5, "global": 0.5},
}

# وزن درجة الموديل مقابل التطابق المباشر مع الاهتمامات العربية
MODEL_SCORE_WEIGHT = 0.7
DIRECT_MATCH_WEIGHT = 0.3

DEFAULT_AGE_GROUP = 2


# ==========================================
# تحميل الموديل
# ==========================================

@lru_cache(maxsize=1)
def load_interest_model():
    """يحمّل الموديل مرة واحدة فقط ويبقيه في الذاكرة. يُرجع None عند الفشل."""

    path = getattr(settings, "INTEREST_MODEL_PATH", None)

    try:
        import joblib

        bundle = joblib.load(path)

        if bundle.get("interests") != MODEL_DIMENSIONS:
            logger.error(
                "Interest model dimensions mismatch: %s",
                bundle.get("interests")
            )
            return None

        return bundle

    except Exception as error:
        logger.warning("Interest model unavailable (%s): %s", path, error)
        return None


# ==========================================
# تحويل بيانات القاعدة إلى متجهات
# ==========================================

def interest_vector(interest):
    """متجه Interest واحد على الأبعاد السبعة."""

    weights = interest.model_weights or DEFAULT_INTEREST_WEIGHTS.get(
        interest.name, {}
    )

    return [float(weights.get(dim, 0)) for dim in MODEL_DIMENSIONS]


def combine_vectors(vectors):
    """يدمج عدة متجهات بأخذ أعلى قيمة لكل بُعد (بين 0 و1)."""

    result = [0.0] * len(MODEL_DIMENSIONS)

    for vector in vectors:
        result = [max(a, b) for a, b in zip(result, vector)]

    return [min(value, 1.0) for value in result]


def pavilion_vector(pavilion):
    """وسوم الجناح على الأبعاد السبعة، محسوبة من اهتماماته في القاعدة."""

    return combine_vectors(
        interest_vector(interest)
        for interest in pavilion.interests.all()
    )


def build_features(selected_interests, chosen_pavilions,
                   available_minutes, group_type, age_group):
    """يبني صف المدخلات (20 رقمًا) بنفس ترتيب التدريب."""

    user_vector = combine_vectors(
        interest_vector(interest) for interest in selected_interests
    )

    # الموديل تدرّب على استبيان من 3 اختيارات (0/1)
    top_dims = sorted(
        (i for i, value in enumerate(user_vector) if value > 0),
        key=lambda i: -user_vector[i]
    )[:3]

    quiz = [1.0 if i in top_dims else 0.0 for i in range(len(MODEL_DIMENSIONS))]

    hours = min(max(round(available_minutes / 60), 2), 8)

    group = [float(group_type == g) for g in GROUP_TYPES]

    if chosen_pavilions:
        vectors = [pavilion_vector(p) for p in chosen_pavilions]
        history = [sum(column) / len(vectors) for column in zip(*vectors)]
    else:
        history = [0.0] * len(MODEL_DIMENSIONS)

    return quiz + [float(age_group), float(hours)] + group + history


# ==========================================
# الدرجات
# ==========================================

def predict_visitor_profile(selected_interests, chosen_pavilions,
                            available_minutes, group_type="solo",
                            age_group=DEFAULT_AGE_GROUP):
    """
    يُرجع ملف الزائر المتوقع {بُعد: قيمة} أو None إن لم يتوفر الموديل.
    """

    bundle = load_interest_model()

    if bundle is None:
        return None

    features = build_features(
        selected_interests,
        chosen_pavilions,
        available_minutes,
        group_type,
        age_group,
    )

    stage = min(len(chosen_pavilions), 2)

    models = bundle["models"]
    model = models.get(stage) or models[max(models)]

    prediction = model.predict([features])[0]

    return dict(zip(MODEL_DIMENSIONS, (float(v) for v in prediction)))


def score_pavilions(pavilions, selected_interests, chosen_pavilions,
                    available_minutes, group_type="solo",
                    age_group=DEFAULT_AGE_GROUP):
    """
    يحسب درجة (0..1) وسببًا عربيًا لكل جناح.

    يُرجع:
        scores:   {pavilion_id: درجة}
        reasons:  {pavilion_id: سبب}
        profile:  ملف الزائر المتوقع (أو None عند استخدام الطريقة الاحتياطية)
    """

    selected_interests = list(selected_interests)
    chosen_pavilions = list(chosen_pavilions)

    selected_ids = {interest.id for interest in selected_interests}

    profile = predict_visitor_profile(
        selected_interests,
        chosen_pavilions,
        available_minutes,
        group_type,
        age_group,
    )

    profile_vector = (
        [profile[dim] for dim in MODEL_DIMENSIONS] if profile else None
    )

    scores = {}
    reasons = {}

    for pavilion in pavilions:

        pavilion_interests = list(pavilion.interests.all())

        matched = [i for i in pavilion_interests if i.id in selected_ids]

        direct = (
            len(matched) / len(selected_ids) if selected_ids else 0.0
        )

        if profile_vector is None:
            score = direct
        else:
            tags = pavilion_vector(pavilion)
            tag_total = sum(tags) or 1.0

            # متوسط مرجّح لملف الزائر على وسوم الجناح (بين 0 و1)
            model_score = sum(
                t * p for t, p in zip(tags, profile_vector)
            ) / tag_total

            score = (
                MODEL_SCORE_WEIGHT * model_score
                + DIRECT_MATCH_WEIGHT * direct
            )

        scores[pavilion.id] = round(score, 4)

        if matched:
            reasons[pavilion.id] = (
                "يتوافق مع اهتمامك: "
                + "، ".join(i.name for i in matched)
            )
        elif profile_vector is not None:
            tags = pavilion_vector(pavilion)
            best = max(
                range(len(MODEL_DIMENSIONS)),
                key=lambda i: tags[i] * profile_vector[i]
            )
            reasons[pavilion.id] = (
                "يقترحه الموديل لميولك نحو "
                + DIMENSION_LABELS_AR[MODEL_DIMENSIONS[best]]
            )
        else:
            reasons[pavilion.id] = "اقتراح إضافي ضمن وقتك"

    return scores, reasons, profile
