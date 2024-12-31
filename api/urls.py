from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from api import views as api_views


urlpatterns = [
    # Userauths API Endpoints
    path('user/token/', api_views.UserTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('user/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('user/register/', api_views.RegisterView.as_view(), name='auth_register'),
    path('user/verify-otp/', api_views.VerifyOTPView.as_view(), name='verify_otp'),

    
    path('user/profile/<user_id>/', api_views.ProfileView.as_view(), name='user_profile'),
    path('user/profiles/<user_id>/', api_views.ProfilesListView.as_view(), name='user_profile'),
    path('user/password-reset/<email>/', api_views.PasswordEmailVerify.as_view(), name='password_reset'),
    path('user/password-change/', api_views.PasswordChangeView.as_view(), name='password_reset'),
    
    # Post Endpoints
    path('post/category/list/', api_views.CategoryListAPIView.as_view()),
    path('post/category/posts/<category_slug>/', api_views.PostCategoryListAPIView.as_view()),
    path('post/lists/', api_views.PostListAPIView.as_view()),
    path('post/detail/<slug>/', api_views.PostDetailAPIView.as_view()),
    path('post/like-post/', api_views.LikePostAPIView.as_view()),
    path('post/comment-post/', api_views.PostCommentAPIView.as_view()),
    path('post/bookmark-post/', api_views.BookmarkPostAPIView.as_view()),
    path('post/popular-post/', api_views.PopularPostListAPIView.as_view()),
    
    # Dashboard Endpoints
    path('author/dashboard/stats/<user_id>/', api_views.DashboardStats.as_view()),
    path('author/dashboard/post-list/<user_id>/', api_views.DashboardPostLists.as_view()),
    path('author/dashboard/comment-list/<user_id>/', api_views.DashboardCommentLists.as_view()),
    path('author/dashboard/noti-list/<user_id>/', api_views.DashboardNotificationLists.as_view()),
    path('author/dashboard/noti-mark-seen/', api_views.DashboardMarkNotificationAsSeen.as_view()),
    path('author/dashboard/reply-comment/', api_views.DashboardReplyCommentAPIView.as_view()),
    path('author/dashboard/post-create/', api_views.DashboardPostCreateAPIView.as_view()),
    path('author/dashboard/post-detail/<user_id>/<post_id>/', api_views.DashboardPostEditAPIView.as_view()),
    path('author/dashboard/post-delete/<int:post_id>/', api_views.DashboardPostDeleteAPIView.as_view()),

    
    path('admin/token/', api_views.AdminTokenObtainPairView.as_view(), name='admin_token_obtain_pair'),
    path('admin/stats/', api_views.AdminDashboardStatsView.as_view(), name='admin_dashboard_stats'),
    path('admin/users-list/', api_views.UserListView.as_view(), name='user-list'),
    path('admin/user-delete/<user_id>/', api_views.AdminUserDeleteAPIView.as_view()),
    path('admin/user-block-unblock/<int:user_id>/', api_views.BlockUnblockUserAPIView.as_view(), name='block-unblock-user'),
    path('admin/posts-list/', api_views.AdminPostsListAPIView.as_view(), name='admin_posts_list'),
    path('admin/post-delete/<int:post_id>/', api_views.AdminPostDeleteAPIView.as_view()),
    path('admin/posts/<int:post_id>/', api_views.AdminPostEditAPIView.as_view()),

]