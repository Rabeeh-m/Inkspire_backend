import redis
from django.shortcuts import render
from django.http import JsonResponse
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.db.models import Sum

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

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from datetime import datetime

# Others
import json
import random

# Custom Imports
from api import serializer as api_serializer
from api import models as api_models
from django.core.mail import send_mail
from django.conf import settings

# Create your views here.

redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)


class UserTokenObtainPairView(TokenObtainPairView):
    serializer_class = api_serializer.UserTokenObtainSerializer
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims (if needed)
        token["is_superuser"] = user.is_superuser
        token["is_staff"] = user.is_staff
        return token
    

# class RegisterView(generics.CreateAPIView):
#     queryset = api_models.User.objects.all()
#     permission_classes = (AllowAny,)
#     serializer_class = api_serializer.RegisterSerializer
    
    

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
        
        # try:
        #     subject="Your OTP for Registration",
        #     message=f"Your OTP is: {otp}",
        #     from_email=settings.EMAIL_HOST_USER,
        #     recipient_list=[email]
        #     send_mail(subject, message, from_email, recipient_list)
        # except Exception as e:
        #     print(f"Error sending email: {e}")

        return Response({"message": "OTP sent to your email."})
 
 
 
 
class VerifyOTPView(APIView):
    def post(self, request):
        email = request.data.get('email')
        otp = request.data.get('otp')

        # Retrieve OTP from Redis
        stored_otp = redis_client.get(f"otp:{email}")
        if stored_otp is None:
            return Response({'error': 'OTP expired. Please request a new one.'}, status=400)

        if stored_otp.decode() != otp:
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
    
 

class PasswordEmailVerify(generics.RetrieveAPIView):
    permission_classes = (AllowAny,)
    serializer_class = api_serializer.UserSerializer
    
    def get_object(self):
        email = self.kwargs['email']
        user = api_models.User.objects.get(email=email)
        
        if user:
            user.otp = generate_numeric_otp()
            uidb64 = user.pk
            
             # Generate a token and include it in the reset link sent via email
            refresh = RefreshToken.for_user(user)
            reset_token = str(refresh.access_token)

            # Store the reset_token in the user model for later verification
            user.reset_token = reset_token
            user.save()

            link = f"http://localhost:5173/create-new-password?otp={user.otp}&uidb64={uidb64}&reset_token={reset_token}"
            
            merge_data = {
                'link': link, 
                'username': user.username, 
            }
            subject = f"Password Reset Request"
            text_body = render_to_string("email/password_reset.txt", merge_data)
            html_body = render_to_string("email/password_reset.html", merge_data)
            
            msg = EmailMultiAlternatives(
                subject=subject, from_email=settings.FROM_EMAIL,
                to=[user.email], body=text_body
            )
            msg.attach_alternative(html_body, "text/html")
            msg.send()
        return user
    

class PasswordChangeView(generics.CreateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = api_serializer.UserSerializer
    
    def create(self, request, *args, **kwargs):
        payload = request.data
        
        otp = payload['otp']
        uidb64 = payload['uidb64']
        password = payload['password']

        

        user = api_models.User.objects.get(id=uidb64, otp=otp)
        if user:
            user.set_password(password)
            user.otp = ""
            user.save()
            
            return Response( {"message": "Password Changed Successfully"}, status=status.HTTP_201_CREATED)
        else:
            return Response( {"message": "An Error Occured"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        
           
class CategoryListAPIView(generics.ListAPIView):
    serializer_class = api_serializer.CategorySerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return api_models.Category.objects.all()
    

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
    permission_classes = [AllowAny]

    def get_queryset(self):
        user_id = self.kwargs['user_id']
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
    def post(self, request):
        # Get data from request.data (frontend)
        post_id = request.data['post_id']
        name = request.data['name']
        email = request.data['email']
        comment = request.data['comment']
        
        post = api_models.Post.objects.get(id=post_id)
        
        # Create Comment
        api_models.Comment.objects.create(
            post=post,
            name=name,
            email=email,
            comment=comment,
        )
        
        # Notification
        api_models.Notification.objects.create(
            user=post.user,
            post=post,
            type="Comment",
        )

        # Return response back to the frontend
        return Response({"message": "Commented Sent"}, status=status.HTTP_201_CREATED)
 
 

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
    

# class DashboardPostCreateAPIView(generics.CreateAPIView):
#     serializer_class = api_serializer.PostSerializer
#     permission_classes = [AllowAny]
    
#     def create(self, request, *args, **kwargs):
#         print(request.data)
#         user_id = request.data.get('user_id')
#         title = request.data.get('title')
#         image = request.data.get('image')
#         description = request.data.get('description')
#         tags = request.data.get('tags')
#         category_id = request.data.get('category')
#         post_status = request.data.get('post_status')
#         profile = request.data.get('profile')
        
#         user = api_models.User.objects.get(id=user_id)
#         category = api_models.Category.objects.get(id=category_id)
        
#         post = api_models.Post.objects.create(
#             user=user,
#             title=title,
#             thumbnail_image=image,
#             content=description,
#             tags=tags,
#             category=category,
#             status=post_status,
#             profile=profile
           
#         )
        
#         return Response({"message": "Post Created Successfully"}, status=status.HTTP_201_CREATED)
    

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