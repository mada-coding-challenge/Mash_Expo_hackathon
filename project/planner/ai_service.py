# from google import genai
# from pydantic import BaseModel

# from django.conf import settings


# class PavilionRecommendation(BaseModel):
#     pavilion_id: int
#     reason: str


# class AIRecommendations(BaseModel):
#     recommendations: list[PavilionRecommendation]


# def get_ai_recommendations(
#     interests,
#     favorite_ids,
#     pavilions
# ):

#     client = genai.Client(
#         api_key=settings.GEMINI_API_KEY
#     )

#     pavilion_data = []

#     for pavilion in pavilions:

#         pavilion_data.append({
#             "id": pavilion.id,

#             "name": pavilion.name,

#             "country": pavilion.country,

#             "description":
#                 pavilion.description,

#             "highlights":
#                 pavilion.highlights,

#             "recommended_duration":
#                 pavilion.recommended_duration,

#             "interests": [
#                 interest.name
#                 for interest
#                 in pavilion.interests.all()
#             ]
#         })

#     prompt = f"""
# أنت مساعد ذكي لتخطيط زيارة إكسبو 2030 الرياض.

# اهتمامات المستخدم:
# {interests}

# معرفات الأجنحة المفضلة للمستخدم:
# {favorite_ids}

# الأجنحة المتاحة:
# {pavilion_data}

# مهمتك ترتيب الأجنحة من الأكثر مناسبة
# إلى الأقل مناسبة لهذا المستخدم.

# قواعد مهمة:

# 1. استخدم فقط الأجنحة الموجودة في البيانات.

# 2. لا تخترع أي جناح جديد.

# 3. أعطِ الأجنحة المفضلة أولوية عالية.

# 4. بعد ذلك اعتمد على اهتمامات المستخدم
# ووصف الجناح وأبرز تجاربه.

# 5. أعد pavilion_id الموجود في البيانات فقط.

# 6. اكتب سببًا عربيًا قصيرًا وواضحًا
# لكل توصية.

# 7. لا تحسب المسافات.

# 8. لا تحسب وقت المشي.

# 9. لا تغير مدة زيارة الجناح.

# Django سيتولى حساب الوقت والمسافات.
# """

#     response = client.models.generate_content(
#         model=settings.GEMINI_MODEL,
#         contents=prompt,
#         config={
#             "response_mime_type":
#                 "application/json",

#             "response_schema":
#                 AIRecommendations,
#         }
#     )

#     return AIRecommendations.model_validate_json(
#         response.text
#     )

from google import genai
from pydantic import BaseModel
from django.conf import settings


class PavilionRecommendation(BaseModel):
    pavilion_id: int
    reason: str


class AIRecommendations(BaseModel):
    recommendations: list[PavilionRecommendation]


def get_ai_recommendations(
    interests,
    favorite_ids,
    pavilions
):

    client = genai.Client(
        api_key=settings.GEMINI_API_KEY
    )

    # Send only information AI actually needs
    pavilion_data = []

    for pavilion in pavilions:

        pavilion_data.append({
            "id": pavilion.id,
            "name": pavilion.name,
            "interests": [
                interest.name
                for interest
                in pavilion.interests.all()
            ]
        })

    prompt = f"""
أنت مساعد لتخطيط زيارة إكسبو 2030.

اهتمامات المستخدم:
{interests}

الأجنحة المفضلة:
{favorite_ids}

الأجنحة:
{pavilion_data}

المطلوب:
رتب الأجنحة من الأكثر مناسبة إلى الأقل.

القواعد:
- استخدم IDs الموجودة فقط.
- لا تخترع أجنحة.
- أعط الأجنحة المفضلة أولوية.
- اعتمد على اهتمامات المستخدم.
- أعط سبباً عربياً قصيراً جداً.
"""

    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": AIRecommendations,
        }
    )

    return AIRecommendations.model_validate_json(
        response.text
    )