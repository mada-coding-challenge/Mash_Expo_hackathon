from django import template

register = template.Library()

# اسم الاهتمام -> نوع الأيقونة/اللون في الواجهة
INTEREST_GROUPS = {
    "tech": ["التقنية", "الذكاء الاصطناعي", "الابتكار"],
    "culture": ["الثقافة", "التاريخ والتراث"],
    "art": ["الفنون"],
    "nature": ["الاستدامة", "الطاقة", "البيئة"],
    "science": ["الفضاء"],
    "health": ["الصحة"],
    "fun": ["الترفيه", "الألعاب", "الطعام", "التسوق"],
}


@register.filter
def interest_slug(name):
    """يرجع نوع الاهتمام: tech / culture / art ... (للأيقونة واللون)."""
    for slug, names in INTEREST_GROUPS.items():
        if name in names:
            return slug
    return "fun"


@register.filter
def tile(pavilion_id):
    """يوزع 6 ألوان على صور الأجنحة حسب رقم الجناح."""
    try:
        return f"tile-{int(pavilion_id) % 6}"
    except (TypeError, ValueError):
        return "tile-0"


@register.filter
def crowd_class(level):
    return {"LOW": "low", "MEDIUM": "mid", "HIGH": "high"}.get(level, "low")


@register.filter
def interests_line(pavilion):
    """أول اهتمامين للجناح مفصولين بنقطة: تقنية · ثقافة"""
    names = [i.name for i in pavilion.interests.all()[:2]]
    return " · ".join(names)


@register.filter
def interest_names(pavilion):
    """كل اهتمامات الجناح مفصولة بفاصلة (تستخدمها JS للاقتراحات)."""
    return ",".join(i.name for i in pavilion.interests.all())


INTEREST_ICONS = {
    "tech": "chip",
    "culture": "crown",
    "art": "palette",
    "nature": "leaf",
    "science": "flask",
    "health": "heart",
    "fun": "smile",
}


@register.filter
def interest_icon(name):
    """اسم أيقونة الاهتمام داخل ملف _icons.html"""
    return INTEREST_ICONS[interest_slug(name)]
