from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import Token

from api import models as api_models


class UserTokenObtainSerializer(TokenObtainPairSerializer):
    
    @classmethod
    # Define a custom method to get the token for a user
    def get_token(cls, user):
        token = super().get_token(user)
        
        # Add custom claims to the token
        token['username'] = user.username
        token['full_name'] = user.full_name
        token['email'] = user.email
        token['is_admin'] = user.is_superuser
        
        return token
    

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = api_models.User
        fields = ['full_name', 'email', 'password', 'password2']
        
    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password2')
        user = api_models.User.objects.create(
            full_name = validated_data['full_name'],
            email = validated_data['email'],
        )
        email_username = user.email.split('@')[0]
        user.username = email_username
        
        user.set_password(validated_data['password'])
        user.save()
        
        return user
    

class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = api_models.User
        fields = '__all__'


class ProfileSerializer(serializers.ModelSerializer):

    class Meta:
        model = api_models.Profile
        fields = '__all__'
        

class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()
        
        

class BaseDepthSerializer(serializers.ModelSerializer):

    # Base serializer to handle dynamic depth based on request method.
    
    def __init__(self, *args, **kwargs):
        super(BaseDepthSerializer, self).__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and request.method == "POST":
            self.Meta.depth = 0
        else:
            self.Meta.depth = getattr(self.Meta, "default_depth", 1)


class CategorySerializer(BaseDepthSerializer):
    post_count = serializers.SerializerMethodField()

    class Meta:
        model = api_models.Category
        fields = ["id", "title", "category_image", "slug", "post_count"]
        default_depth = 3

    def get_post_count(self, category):
        return category.posts.count()


# class CommentSerializer(BaseDepthSerializer):
#     class Meta:
#         model = api_models.Comment
#         fields = "__all__"
#         default_depth = 1

class ReplySerializer(serializers.ModelSerializer):
    class Meta:
        model = api_models.Comment
        fields = ['id', 'user', 'comment', 'created_at', 'likes', 'replies']
        
class CommentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    replies = serializers.SerializerMethodField()
    like_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = api_models.Comment
        fields = ['id', 'post', 'user', 'comment', 'likes', 'parent', 'created_at', 'replies', 'like_count']

    def get_replies(self, obj):
        replies = obj.replies.all()
        return CommentSerializer(replies, many=True).data
    
    

class PostSerializer(BaseDepthSerializer):
    comments = CommentSerializer(many=True, read_only=True)

    class Meta:
        model = api_models.Post
        fields = "__all__"
        default_depth = 3


class BookmarkSerializer(BaseDepthSerializer):
    class Meta:
        model = api_models.Bookmark
        fields = "__all__"
        default_depth = 3


class NotificationSerializer(BaseDepthSerializer):
    class Meta:
        model = api_models.Notification
        fields = "__all__"
        default_depth = 3


class AuthorStats(serializers.Serializer):
    views = serializers.IntegerField(default=0)
    posts = serializers.IntegerField(default=0)
    likes = serializers.IntegerField(default=0)
    bookmarks = serializers.IntegerField(default=0)
    
    
class SubscriptionSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model = api_models.Subscription
        fields = ['id', 'user', 'plan', 'status', 'start_date', 'end_date']
        read_only_fields = ['start_date'] 