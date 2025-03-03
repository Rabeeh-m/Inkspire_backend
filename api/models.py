from django.db import models
from django_ckeditor_5.fields import CKEditor5Field
# Create your models here.
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save
from django.utils.text import slugify

from shortuuid.django_fields import ShortUUIDField
import shortuuid
from django.conf import settings
from django.utils.timezone import now, timedelta
from django.utils import timezone


        

class User(AbstractUser):
    username = models.CharField(unique=True, max_length=100)
    full_name = models.CharField(max_length=100, null=True, blank=True)
    email = models.EmailField(unique=True) 
    otp = models.CharField(max_length=10, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    is_premium = models.BooleanField(default=False)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email
    
    def save(self, *args, **kwargs):
        # Auto-fill full_name and username if they are empty
        email_username = self.email.split("@")[0]
        if not self.full_name:
            self.full_name = email_username
        if not self.username:
            self.username = email_username
        super().save(*args, **kwargs)




class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100, null=True, blank=True)
    profile_image = models.FileField(upload_to="image", default="default/default-user.jpg", null=True, blank=True)
    bio = models.TextField(null=True, blank=True)
    about = models.TextField(null=True, blank=True)
    is_author = models.BooleanField(default=False)
    is_premium = models.BooleanField(default=False)
    followers = models.ManyToManyField("self", symmetrical=False, related_name="following", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def follower_count(self):
        return self.followers.count()

    def following_count(self):
        # return self.user.profile.following.count()
        return self.following.count()
        

    def __str__(self):
        return self.full_name if self.full_name else self.user.email
    

    def save(self, *args, **kwargs):
        # Auto-fill full_name if it is empty
        if not self.full_name:
            self.full_name = self.user.full_name
        super().save(*args, **kwargs)


def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

post_save.connect(create_user_profile, sender=User)
post_save.connect(save_user_profile, sender=User)



class Category(models.Model):
    title = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, null=True, blank=True)
    category_image = models.FileField(upload_to="image", null=True, blank=True)
    

    def __str__(self):
        return self.title
    
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['title']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
        
    def post_count(self):
        return Post.objects.filter(category=self).count()
    
        
        
class Post(models.Model):
    STATUS = ( 
                ("Draft", "Draft"),
                ("Published", "Published"), 
                ("Disabled", "Disabled"),
            )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, null=True, blank=True)
    thumbnail_image = models.FileField(upload_to="image", null=True, blank=True)
    content = CKEditor5Field(null=True, blank=True, config_name='extends')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='posts')
    tags = models.CharField(max_length=100)
    status = models.CharField(max_length=100, choices=STATUS, default="Draft")
    views = models.IntegerField(default=0)
    likes = models.ManyToManyField(User, blank=True, related_name="likes_user")  
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.title
    
    class Meta:
        verbose_name_plural = "Posts"
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            # Generate slug if it doesn't exist
            self.slug = slugify(self.title) + "-" + shortuuid.uuid()[:2]
        super().save(*args, **kwargs)
        
    
    def comments(self):
        return Comment.objects.filter(post=self)
        
        
class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    comment = models.TextField()
    likes = models.ManyToManyField(User, related_name='comment_likes', blank=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, related_name='replies', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.comment[:20]
    
    def like_count(self):
        return self.likes.count()

    def reply_count(self):
        return self.replies.count()
    
    class Meta:
        verbose_name_plural = "Comments"
        ordering = ['-created_at']
          
        
class Bookmark(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.post.title} - {self.user.username}"
    
    class Meta:
        verbose_name_plural = "Bookmarks"
        ordering = ['-created_at']
        
        

class Notification(models.Model):
    NOTIFICATION_TYPE = ( 
                         ("Like", "Like"), 
                         ("Comment", "Comment"), 
                         ("Bookmark", "Bookmark"),
                         ("Follow", "Follow"),
                        )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, null=True, blank=True)
    type = models.CharField(max_length=100, choices=NOTIFICATION_TYPE)
    seen = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Notifications"
        ordering = ['-created_at']
    
    def __str__(self):
        if self.post:
            return f"{self.type} - {self.post.title}"
        else:
            return "Notification"
        
        
        
class Subscription(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    plan = models.CharField(max_length=50, default='Free')
    status = models.CharField(max_length=50, choices=[("active", "Active"), ("expired", "Expired")], default="")
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.email} - {self.plan}"    
         

class Follow(models.Model):
    follower = models.ForeignKey(User, related_name='following', on_delete=models.CASCADE)
    followed = models.ForeignKey(User, related_name='followers', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'followed')  # Prevents duplicate follows

    def __str__(self):
        return f"{self.follower} follows {self.followed}"
    

class Room(models.Model):
    participants = models.ManyToManyField(User, related_name="chat_rooms")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Room {self.id}"

    def get_participant_ids(self):
        return list(self.participants.values_list('id', flat=True))

    @classmethod
    def get_or_create_room(cls, user1_id, user2_id):
        # Sort user IDs to ensure consistency
        user_ids = sorted([user1_id, user2_id])
        room_name = f"chat_{user_ids[0]}-{user_ids[1]}"

        # Find a room where both participants exist
        rooms = cls.objects.filter(participants__id__in=user_ids).distinct()
        for room in rooms:
            if set(room.get_participant_ids()) == set(user_ids):
                return room

        # If no room exists, create a new one
        room = cls.objects.create()
        room.participants.add(*user_ids)
        return room
    
    
class Message(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_messages")
    text = models.TextField(null=True, blank=True)
    file = models.FileField(upload_to='chat_files/', null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.sender} in Room {self.room.id}"



class RoomMember(models.Model):
    name = models.CharField(max_length=200)
    uid = models.CharField(max_length=1000)
    room_name = models.CharField(max_length=200)
    insession = models.BooleanField(default=True)

    def __str__(self):
        return self.name