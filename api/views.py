import redis
import os
from django.shortcuts import render
from django.http import JsonResponse
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.db.models import Sum
from django.core.mail import send_mail
from django.contrib.auth.hashers import make_password
from django.contrib.auth.hashers import check_password
from django.shortcuts import get_object_or_404
# Restframework
from rest_framework import status
from rest_framework.decorators import api_view, APIView
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAdminUser
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from datetime import timedelta
from django.utils import timezone 
# Others
import json
import random
import uuid
from django.http import JsonResponse
# Custom Imports
from api import serializer as api_serializer
from api import models as api_models


# Create your views here.
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
redis_client = redis.StrictRedis.from_url(REDIS_URL, decode_responses=True)


class UserTokenObtainPairView(TokenObtainPairView):
    serializer_class = api_serializer.UserTokenObtainSerializer
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims (if needed)
        token["is_superuser"] = user.is_superuser
        token["is_staff"] = user.is_staff
        return token
    

def generate_numeric_otp(length=6):
        # Generate a random 6-digit OTP
        otp = ''.join([str(random.randint(0, 9)) for _ in range(length)])
        return otp
 

class RegisterView(APIView):
    def post(self, request):
        full_name = request.data.get('full_name')
        email = request.data.get('email')
        password = request.data.get('password')
        password2 = request.data.get('password2')

        if password != password2:
            return Response({'error': 'Passwords do not match'}, status=400)

        # Generate OTP
        otp = generate_numeric_otp()

        # Save OTP in Redis with a 2-minute expiration
        redis_client.setex(f"otp:{email}", 120, otp)

        # Send OTP email
        send_mail(
            subject="Your OTP for Registration",
            message=f"Your OTP is: {otp}",
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[email]
        )

        return Response({"message": "OTP sent to your email."})
 
 
class VerifyOTPView(APIView):
    def post(self, request):
        email = request.data.get('email')
        otp = request.data.get('otp')

        # Retrieve OTP from Redis
        stored_otp = redis_client.get(f"otp:{email}")
        if stored_otp is None:
            return Response({'error': 'OTP expired. Please request a new one.'}, status=400)

        if stored_otp != otp:  # if stored_otp.decode() != otp:
            return Response({'error': 'Invalid OTP'}, status=400)

        # Create the user after OTP is verified
        full_name = request.data.get('full_name')
        password = request.data.get('password')
        user = api_models.User.objects.create_user(username = email.split("@")[0], email=email, full_name=full_name, password=password)

        return Response({'message': 'Registration successful.'})
 
 
class ProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = api_serializer.ProfileSerializer
    
    def get_object(self):
        user_id = self.kwargs['user_id']
        user = api_models.User.objects.get(id = user_id)
        profile = api_models.Profile.objects.get(user = user)
        return profile
       
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
redis_instance = redis.StrictRedis.from_url(REDIS_URL, decode_responses=True)


class ForgotPasswordView(APIView):
    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({"error": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)

        user = api_models.User.objects.filter(email=email).first()
        if not user:
            return Response({"error": "User with this email does not exist."}, status=status.HTTP_404_NOT_FOUND)

        otp = random.randint(100000, 999999)
        redis_instance.setex(f"forgot-password-otp-{email}", 300, otp)  # OTP expires in 5 minutes

        send_mail(
            "Your Password Reset OTP",
            f"Your OTP for password reset is {otp}.",
            "noreply@yourdomain.com",
            [email],
        )

        return Response({"message": "OTP has been sent to your email."}, status=status.HTTP_200_OK)


class VerifyForgotPasswordOTPView(APIView):
    def post(self, request):
        email = request.data.get('email')
        otp = request.data.get('otp')

        if not email or not otp:
            return Response({"error": "Email and OTP are required."}, status=status.HTTP_400_BAD_REQUEST)

        stored_otp = redis_instance.get(f"forgot-password-otp-{email}")
        if not stored_otp or stored_otp != otp:  #if not stored_otp or stored_otp.decode() != otp:
            return Response({"error": "Invalid or expired OTP."}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"message": "OTP verified."}, status=status.HTTP_200_OK)


class ResetPasswordView(APIView):
    def post(self, request):
        email = request.data.get('email')
        new_password = request.data.get('new_password')

        if not email or not new_password:
            return Response({"error": "Email and new password are required."}, status=status.HTTP_400_BAD_REQUEST)

        user = api_models.User.objects.filter(email=email).first()
        if not user:
            return Response({"error": "User with this email does not exist."}, status=status.HTTP_404_NOT_FOUND)

        user.password = make_password(new_password)
        user.save()

        return Response({"message": "Password has been reset successfully."}, status=status.HTTP_200_OK)



class ChangePasswordView(APIView):
    permission_classes = [AllowAny]  # Allow unauthenticated users

    def post(self, request, *args, **kwargs):
        data = request.data
        email = data.get("email")
        old_password = data.get("old_password")
        new_password = data.get("new_password")
        confirm_password = data.get("confirm_password")

        if not email or not old_password or not new_password or not confirm_password:
            return Response({"detail": "All fields are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = api_models.User.objects.get(email=email)
        except api_models.User.DoesNotExist:
            return Response({"detail": "User with this email does not exist."}, status=status.HTTP_404_NOT_FOUND)

        if not check_password(old_password, user.password):
            return Response({"detail": "Old password is incorrect."}, status=status.HTTP_400_BAD_REQUEST)

        if new_password != confirm_password:
            return Response({"detail": "New passwords do not match."}, status=status.HTTP_400_BAD_REQUEST)


        user.set_password(new_password)
        user.save()

        return Response({"detail": "Password updated successfully."}, status=status.HTTP_200_OK)

      
           
class CategoryListAPIView(generics.ListAPIView):
    serializer_class = api_serializer.CategorySerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return api_models.Category.objects.all()


class CategoryCreateAPIView(generics.CreateAPIView):
    serializer_class = api_serializer.CategoryCreateUpdateSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response({"message": "Category created successfully.", "data": serializer.data}, status=status.HTTP_201_CREATED)

class CategoryDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = api_serializer.CategoryCreateUpdateSerializer
    permission_classes = [AllowAny]
    
    def get_object(self):
        category_id = self.kwargs['category_id']
        return get_object_or_404(api_models.Category, id=category_id)

    def update(self, request, *args, **kwargs):
        category = self.get_object()
        serializer = self.get_serializer(category, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({"message": "Category updated successfully.", "data": serializer.data}, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        category = self.get_object()
        category.delete()
        return Response({"message": "Category deleted successfully."}, status=status.HTTP_200_OK)
    

class PostCategoryListAPIView(generics.ListAPIView):
    serializer_class = api_serializer.PostSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        category_slug = self.kwargs['category_slug'] 
        category = api_models.Category.objects.get(slug=category_slug)
        return api_models.Post.objects.filter(category=category, status="Active")
    

class PostListAPIView(generics.ListAPIView):
    serializer_class = api_serializer.PostSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        # return api_models.Post.objects.all()
        return api_models.Post.objects.filter(status='Published')
        

class PopularPostListAPIView(generics.ListAPIView):
    serializer_class = api_serializer.PostSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        # return api_models.Post.objects.filter(status='Published')
        return api_models.Post.objects.all().order_by("-views")
    
    
class ProfilesListView(generics.ListAPIView):
    serializer_class = api_serializer.ProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # user_id = self.kwargs['user_id']
        user_id = self.request.user.id
        return api_models.Profile.objects.exclude(user_id__in=[2, user_id])

    

class PostDetailAPIView(generics.RetrieveAPIView):
    serializer_class = api_serializer.PostSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        slug = self.kwargs['slug']
        post = api_models.Post.objects.get(slug=slug, status="Published")
        post.views += 1
        post.save()
        return post
    


class LikePostAPIView(APIView):
    
    def post(self, request):
        user_id = request.data['user_id']
        post_id = request.data['post_id']
        
        user = api_models.User.objects.get(id=user_id)
        post = api_models.Post.objects.get(id=post_id)
        
        # Check if post has already been liked by this user
        if user in post.likes.all():
            # If liked, unlike post
            post.likes.remove(user)
            return Response({"message": "Post Disliked"}, status=status.HTTP_200_OK)
        else:
            # If post hasn't been liked, like the post by adding user to set of poeple who have liked the post
            post.likes.add(user)
            
            api_models.Notification.objects.create(
                user=post.user,
                post=post,
                type="Like",
            )
            return Response({"message": "Post Liked"}, status=status.HTTP_201_CREATED)
        

class PostCommentAPIView(APIView):
    def post(self, request, *args, **kwargs):
        user_id = request.data.get('user_id')  # Get user_id from the request
        if not user_id:
            return Response({"error": "The 'user_id' field is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch the User instance
        user = get_object_or_404(api_models.User, id=user_id)

        # Handle replies
        if "comment_id" in request.data:  # This indicates it's a reply
            try:
                parent_comment = api_models.Comment.objects.get(id=request.data['comment_id'])
                reply = api_models.Comment.objects.create(
                    user=user,
                    post=parent_comment.post,
                    comment=request.data.get('comment'),
                    parent=parent_comment
                )
                
                 # Notification for reply
                api_models.Notification.objects.create(
                    user=post.user,
                    post=post,
                    type="Comment"
                )
                return Response(
                    {"message": "Reply added successfully!", "reply": api_serializer.CommentSerializer(reply).data},
                    status=status.HTTP_201_CREATED
                )
            except api_models.Comment.DoesNotExist:
                return Response({"error": "Parent comment not found."}, status=status.HTTP_404_NOT_FOUND)

        # Handle top-level comments
        try:
            post = api_models.Post.objects.get(id=request.data['post_id'])
            comment = api_models.Comment.objects.create(
                user=user, post=post, comment=request.data.get('comment')
            )
            
            # Notification for comment
            api_models.Notification.objects.create(
                user=post.user,
                post=post,
                type="Comment"
            )
            return Response(
                {"message": "Comment added successfully!", "comment": api_serializer.CommentSerializer(comment).data},
                status=status.HTTP_201_CREATED
            )
        except api_models.Post.DoesNotExist:
            return Response({"error": "Post not found."}, status=status.HTTP_404_NOT_FOUND)
        


class PostCommentReplyAPIView(APIView):
    def post(self, request):
        comment_id = request.data.get("comment_id")
        user_id = request.data.get("user_id")
        comment = request.data.get("comment")

        if not comment_id or not comment:
            return Response({"error": "Comment ID and comment are required."}, status=400)

        try:
            parent_comment = api_models.Comment.objects.get(id=comment_id)
        except api_models.Comment.DoesNotExist:
            return Response({"error": "Invalid comment ID."}, status=400)

        user = api_models.User.objects.get(id=user_id)
        reply = api_models.Comment.objects.create(
            user=user,
            parent=parent_comment,
            comment=comment,
            post=parent_comment.post,
        )
        
        # Notification for reply
        api_models.Notification.objects.create(
            user=parent_comment.user,
            post=parent_comment.post,
            type="Comment"
        )
        
        return Response(
            {"message": "Reply posted successfully.", "reply": api_serializer.ReplySerializer(reply).data},
            status=201,
        )

        
        
class CommentLikeAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        comment_id = request.data.get('comment_id')
        
        user_id = request.data.get('user_id')  # Get user_id from the request
        if not user_id:
            return Response({"error": "The 'user_id' field is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch the User instance
        user = get_object_or_404(api_models.User, id=user_id)

        try:
            comment = api_models.Comment.objects.get(id=comment_id)
            if user in comment.likes.all():
                comment.likes.remove(user)
                return Response({'success': True, 'message': 'Unliked comment.'})
            else:
                comment.likes.add(user)
                return Response({'success': True, 'message': 'Liked comment.'})
        except api_models.Comment.DoesNotExist:
            return Response({'success': False, 'message': 'Comment not found!'}, status=404)




class BookmarkPostAPIView(APIView):

    def post(self, request):
        user_id = request.data['user_id']
        post_id = request.data['post_id']

        user = api_models.User.objects.get(id=user_id)
        post = api_models.Post.objects.get(id=post_id)

        bookmark = api_models.Bookmark.objects.filter(post=post, user=user).first()
        
        if bookmark:
            # Remove post from bookmark
            bookmark.delete()
            return Response({"message": "Post Bookmark deleted"}, status=status.HTTP_200_OK)
        else:
            api_models.Bookmark.objects.create(
                user=user,
                post=post
            )

            # Notification
            api_models.Notification.objects.create(
                user=post.user,
                post=post,
                type="Bookmark",
            )
            return Response({"message": "Post Bookmarked"}, status=status.HTTP_201_CREATED)





class DashboardStats(generics.ListAPIView):
    serializer_class = api_serializer.AuthorStats
    permission_classes = [AllowAny]

    def get_queryset(self):
        user_id = self.kwargs['user_id']
        user = api_models.User.objects.get(id=user_id)

        views = api_models.Post.objects.filter(user=user).aggregate(view=Sum("views"))['view']
        posts = api_models.Post.objects.filter(user=user).count()
        likes = api_models.Post.objects.filter(user=user).aggregate(total_likes=Sum("likes"))['total_likes']
        bookmarks = api_models.Bookmark.objects.filter(post__user=user).count()
        # bookmarks = api_models.Bookmark.objects.all().count()

        return [{
            "views": views,
            "posts": posts,
            "likes": likes,
            "bookmarks": bookmarks,
        }]
    
    def list(self, request, *args, **kwargs):
        querset = self.get_queryset()
        serializer = self.get_serializer(querset, many=True)
        return Response(serializer.data)
    

class DashboardPostLists(generics.ListAPIView):
    serializer_class = api_serializer.PostSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        user_id = self.kwargs['user_id']
        user = api_models.User.objects.get(id = user_id)
        return api_models.Post.objects.filter(user=user).order_by("-id")
    

class DashboardCommentLists(generics.ListAPIView):
    serializer_class = api_serializer.CommentSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        user_id = self.kwargs['user_id']
        user = api_models.User.objects.get(id = user_id)
        return api_models.Comment.objects.filter(post__user =user)
    
    
class DashboardNotificationLists(generics.ListAPIView):
    serializer_class = api_serializer.NotificationSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        user_id = self.kwargs['user_id']
        user = api_models.User.objects.get(id=user_id)

        return api_models.Notification.objects.filter(seen=False, user=user)
    

class DashboardMarkNotificationAsSeen(APIView):
    def post(self, request):
        noti_id = request.data['noti_id']
        noti = api_models.Notification.objects.get(id=noti_id)

        noti.seen = True
        noti.save()

        return Response({"message": "Notification Marked As Seen"}, status=status.HTTP_200_OK)
    
    
class DashboardReplyCommentAPIView(APIView):
    def post(self, request):
        comment_id = request.data['comment_id']
        reply = request.data['reply']
        
        comment = api_models.Comment.objects.get(id=comment_id)
        comment.reply = reply
        comment.save()
        return Response({"message": "Comment Response Sent"}, status=status.HTTP_201_CREATED)
    


class DashboardPostCreateAPIView(generics.CreateAPIView):
    serializer_class = api_serializer.PostSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        try:
            user_id = request.data.get('user_id')
            profile_id = request.data.get('profile')
            category_id = request.data.get('category')

            # Fetch user, profile, and category objects
            user = api_models.User.objects.get(id=user_id)
            profile = api_models.Profile.objects.get(id=profile_id)
            category = api_models.Category.objects.get(id=category_id)

            # Create Post
            post = api_models.Post.objects.create(
                user=user,
                profile=profile,
                title=request.data.get('title'),
                thumbnail_image=request.data.get('image'),
                content=request.data.get('description'),
                tags=request.data.get('tags'),
                category=category,
                status=request.data.get('post_status'),
            )

            return Response({"message": "Post Created Successfully"}, status=status.HTTP_201_CREATED)
        except api_models.User.DoesNotExist:
            return Response({"error": "Invalid User ID"}, status=status.HTTP_400_BAD_REQUEST)
        except api_models.Profile.DoesNotExist:
            return Response({"error": "Invalid Profile ID"}, status=status.HTTP_400_BAD_REQUEST)
        except api_models.Category.DoesNotExist:
            return Response({"error": "Invalid Category ID"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class DashboardPostEditAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = api_serializer.PostSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        user_id = self.kwargs['user_id']
        post_id = self.kwargs['post_id']
        user = api_models.User.objects.get(id=user_id)
        return api_models.Post.objects.get(user=user, id=post_id)

    def update(self, request, *args, **kwargs):
        post_instance = self.get_object()

        title = request.data.get('title')
        image = request.data.get('image')
        content = request.data.get('content')
        tags = request.data.get('tags')
        category_id = request.data.get('category')
        post_status = request.data.get('post_status')

        category = api_models.Category.objects.get(id=category_id)

        post_instance.title = title
        if image != "undefined":
            post_instance.thumbnail_image = image
        post_instance.content = content
        post_instance.tags = tags
        post_instance.category = category
        post_instance.status = post_status
        post_instance.save()

        return Response({"message": "Post Updated Successfully"}, status=status.HTTP_200_OK)


{
    "title": "New post",
    "image": "",
    "content": "lorem",
    "tags": "tags, here",
    "category_id": 1,
    "post_status": "Active"
}



class DashboardPostDeleteAPIView(generics.DestroyAPIView):
    serializer_class = api_serializer.PostSerializer
    permission_classes = [AllowAny]

    def delete(self, request, *args, **kwargs):
        post_id = self.kwargs.get('post_id')
        try:
            # Fetch the post
            post = api_models.Post.objects.get(id=post_id)
            
            # Delete the post
            post.delete()
            
            return Response({"message": "Post deleted successfully."}, status=status.HTTP_200_OK)
        except api_models.Post.DoesNotExist:
            return Response({"error": "Post not found or not authorized to delete."}, status=status.HTTP_404_NOT_FOUND)
        
        
        

class AdminTokenObtainPairView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)  # Validate input data
            user = serializer.user  # Get the user after validation

            # Check if the user is an admin
            if not user.is_superuser:
                return Response({"error": "Only admins can log in."}, status=status.HTTP_403_FORBIDDEN)

            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)



class AdminDashboardStatsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        user_count = api_models.User.objects.count()
        post_count = api_models.Post.objects.count()
        comment_count = api_models.Comment.objects.count()

        return Response({
            "user_count": user_count,
            "post_count": post_count,
            "comment_count": comment_count,
        })


class UserListView(generics.ListAPIView):
    serializer_class = api_serializer.UserSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return api_models.User.objects.all()




class AdminUserDeleteAPIView(generics.DestroyAPIView):
    serializer_class = api_serializer.UserSerializer
    permission_classes = [AllowAny]

    def delete(self, request, *args, **kwargs):
        user_id = self.kwargs.get('user_id')
        try:
            # Fetch the user
            user = api_models.User.objects.get(id=user_id)
            
            # Delete the post
            user.delete()
            
            return Response({"message": "User deleted successfully."}, status=status.HTTP_200_OK)
        except api_models.User.DoesNotExist:
            return Response({"error": "User not found or not authorized to delete."}, status=status.HTTP_404_NOT_FOUND)
        
        
        

class BlockUnblockUserAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, user_id):
        try:
            user = api_models.User.objects.get(pk=user_id)
            user.is_active = not user.is_active  # Toggle the is_active status
            user.save()

            return Response(
                {"message": f"User {'blocked' if not user.is_active else 'unblocked'} successfully."},
                status=status.HTTP_200_OK,
            )
        except api_models.User.DoesNotExist:
            return Response(
                {"error": "User not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
            
            
class AdminPostsListAPIView(generics.ListAPIView):
    serializer_class = api_serializer.PostSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        return api_models.Post.objects.all()
    


class AdminPostDeleteAPIView(generics.DestroyAPIView):
    serializer_class = api_serializer.PostSerializer
    permission_classes = [AllowAny]

    def delete(self, request, *args, **kwargs):
        post_id = self.kwargs.get('post_id')
        try:
            # Fetch the post
            post = api_models.Post.objects.get(id=post_id)
            
            # Delete the post
            post.delete()
            
            return Response({"message": "Post deleted successfully."}, status=status.HTTP_200_OK)
        except api_models.Post.DoesNotExist:
            return Response({"error": "Post not found or not authorized to delete."}, status=status.HTTP_404_NOT_FOUND)
        
        
        
class AdminPostEditAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = api_serializer.PostSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        post_id = self.kwargs['post_id']
        return api_models.Post.objects.get(id=post_id)



class PaypalSuccessAPIView(APIView):
    permission_classes = [AllowAny]  # Allow any user to access this view (no authentication required)

    def post(self, request):
        try:
            # Get the PayPal order ID from the frontend
            order_id = request.data.get("orderID")
            
            # If no order ID is provided, return an error response
            if not order_id:
                return Response(
                    {"success": False, "message": "Invalid order ID"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Simulate verifying the PayPal order (this should involve calling PayPal's API)
            # For the sake of this example, we'll assume payment verification is successful
            user_id = request.data.get("userId") 
            user = api_models.User.objects.get(pk=user_id)

            if user.is_premium:
                return Response(
                    {"success": False, "message": "User is already premium"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Update the user's premium status
            user.is_premium = True
            user.save()

            # Create a new Subscription record for the user
            subscription = api_models.Subscription.objects.create(
                user=user,
                plan="premium",
                status="active",
                end_date=timezone.now() + timedelta(days=30)
            )
        
            # Generate Invoice Data
            invoice_id = str(uuid.uuid4())[:8]
            invoice_data = {
                "invoice_id": invoice_id,
                "user_email": user.email,
                "plan": "Premium",
                "amount": 9.99,
                "date": timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            
            # Trigger the Celery task to send the payment success email
            send_payment_success_email.delay(
                email=user.email,
                invoice_id=invoice_id,
                amount=invoice_data["amount"],
                plan=invoice_data["plan"],
                date=invoice_data["date"]
            )


            # Return invoice details in the response
            return JsonResponse({
                "success": True,
                "message": "Payment successful, user upgraded!",
                "subscription_id": subscription.id,
                "invoice": invoice_data,
            })

        except Exception as e:
            return Response(
                {"success": False, "message": "Error processing payment", "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
            
            
            

class AdminSubscriptionListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        subscriptions = api_models.Subscription.objects.select_related("user").all()
        serializer = api_serializer.SubscriptionSerializer(subscriptions, many=True)
        return Response(serializer.data)


class AdminSubscriptionUpdateView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, subscription_id):
        try:
            subscription = api_models.Subscription.objects.get(id=subscription_id)
            serializer = api_serializer.SubscriptionSerializer(
                subscription, data=request.data, partial=True
            )
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except api_models.Subscription.DoesNotExist:
            return Response({"error": "Subscription not found"}, status=status.HTTP_404_NOT_FOUND)
        
        
class AdminSubscriptionDetailView(generics.RetrieveAPIView):
    queryset = api_models.Subscription.objects.select_related("user")
    serializer_class = api_serializer.SubscriptionSerializer
    permission_classes = [AllowAny]
    

class FollowUnfollowUserView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, profile_id):
        try:
            target_profile = api_models.Profile.objects.get(id=profile_id)
            user_profile = request.user.profile

            if target_profile == user_profile:
                return Response(
                    {"detail": "You cannot follow/unfollow yourself."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if user_profile in target_profile.followers.all():
                # Unfollow
                target_profile.followers.remove(user_profile)
                return Response(
                    {"detail": "Unfollowed successfully."},
                    status=status.HTTP_200_OK,
                )
            else:
                # Follow
                target_profile.followers.add(user_profile)
                
                # Create notification for follow action
                api_models.Notification.objects.create(
                    user=target_profile.user,
                    post=None,  # No post in this case
                    type="Follow",  # This represents the follow action
                )
                 
                return Response(
                    {"detail": "Followed successfully."},
                    status=status.HTTP_200_OK,
                )

        except api_models.Profile.DoesNotExist:
            return Response(
                {"detail": "Profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )


from .tasks import test_func, send_payment_success_email

class Test(APIView):
    def get(self, request):
        test_func.delay()
        return Response({"detail": "CELERY TEST DONE"},status=status.HTTP_200_OK,)
    



from agora_token_builder import RtcTokenBuilder
# from .models import RoomMember
# from .serializers import RoomMemberSerializer
import time

class GetTokenAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        app_id = "1be2678b4f7b4c34831b89781a29ef2f"
        app_certificate = "862c7f5e96cb486a8c8c3d18b54266af"
        channel_name = request.GET.get('channel')
        uid = random.randint(1, 230)
        expiration_time_in_seconds = 3600 * 24
        current_timestamp = int(time.time())
        privilege_expired_ts = current_timestamp + expiration_time_in_seconds
        role = 1

        token = RtcTokenBuilder.buildTokenWithUid(app_id, app_certificate, channel_name, uid, role, privilege_expired_ts)
        return Response({'token': token, 'uid': uid}, status=status.HTTP_200_OK)




class RoomMemberCreateView(APIView):

    def post(self, request):
        serializer = api_serializer.RoomMemberSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class RoomMemberRetrieveView(APIView):

    def get(self, request):
        uid = request.GET.get('UID')
        room_name = request.GET.get('room_name')

        if not uid or not room_name:
            return Response({'error': 'UID and room_name are required'}, status=status.HTTP_400_BAD_REQUEST)

        member = get_object_or_404(api_models.RoomMember, uid=uid, room_name=room_name)
        serializer = api_serializer.RoomMemberSerializer(member)
        return Response(serializer.data, status=status.HTTP_200_OK)



class RoomMemberDeleteView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            member = api_models.RoomMember.objects.get(
                name=data['name'],
                uid=data['UID'],
                room_name=data['room_name']
            )
            member.delete()
            return Response({'message': 'Member deleted'}, status=status.HTTP_204_NO_CONTENT)
        except api_models.RoomMember.DoesNotExist:
            return Response({'error': 'Member not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        

class ChatRoomView(APIView):
    def get(self, request, user1_id, user2_id):
        try:
            room = api_models.Room.get_or_create_room(user1_id, user2_id)
            serializer = api_serializer.RoomSerializer(room)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MessageView(APIView):
    parser_classes = [MultiPartParser, FormParser]  # Add this to handle file uploads

    def post(self, request):
        room_id = request.data.get('room_id')
        sender_id = request.data.get('sender_id')
        text = request.data.get('text')
        file = request.FILES.get('file')  # Get the uploaded file

        if not all([room_id, sender_id]) and not (text or file):
            return Response({"error": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST)

        message = api_models.Message.objects.create(
            room_id=room_id,
            sender_id=sender_id,
            text=text,
            file=file,  # Save the file
        )
        serializer = api_serializer.MessageSerializer(message, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)