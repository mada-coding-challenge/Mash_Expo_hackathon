
from django.contrib import admin
from .models import (
    Interest,
    Pavilion,
    Challenge,
    ChallengeVisit,
    FreePass,
)




@admin.register(Interest)
class InterestAdmin(admin.ModelAdmin):
    list_display = ("name", "model_weights")
admin.site.register(Pavilion)
admin.site.register(Challenge)
admin.site.register(ChallengeVisit)
admin.site.register(FreePass)