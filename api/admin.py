from django.contrib import admin
from api import models as api_models

# Register your models here.

class PostAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ["title"]}
    
class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ["title"]}
    
admin.site.register(api_models.User)
admin.site.register(api_models.Profile)
admin.site.register(api_models.Category,CategoryAdmin)
admin.site.register(api_models.Post, PostAdmin)
admin.site.register(api_models.Comment)
admin.site.register(api_models.Bookmark)
admin.site.register(api_models.Notification)
admin.site.register(api_models.Subscription)
admin.site.register(api_models.Follow)

admin.site.register(api_models.RoomMember)

admin.site.register(api_models.Room)
admin.site.register(api_models.Message)