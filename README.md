# Inkspire Backend

Inkspire is a online publication platform, built with Django and Django REST Framework. It powers a social media-enabled platform for publishing posts, managing user profiles, and enabling real-time chat via WebSockets. Key features include user authentication, post creation with rich text, comments, likes, bookmarks, notifications, and subscriptions, integrated with AWS S3 for media storage and Redis for caching and real-time functionality. The backend connects to a React frontend and is deployed on Render.

## Features

- User Authentication: JWT-based registration, login, OTP verification, and password reset.
- Post Management: Create, edit, delete, and view posts with rich text (CKEditor), categories, and tags.
- Social Features: Likes, comments, replies, bookmarks, and follow/unfollow functionality with notifications.
- Real-Time Chat: WebSocket-based chat system using Django Channels for private messaging with file uploads.
- Subscriptions: Premium plan management with PayPal integration and email notifications via Celery.
- Admin Dashboard: Manage users, posts, and subscriptions with stats and moderation tools.
- Media Storage: AWS S3 for file uploads (images, chat files).
- Caching & Async Tasks: Redis for caching and Celery for asynchronous tasks like email sending.

## Tech Stack

- Framework: Django, Django REST Framework
- WebSockets: Django Channels
- Database: PostgreSQL
- Storage: AWS S3
- Caching: Redis
- Async Tasks: Celery with Redis broker
- Authentication: JWT (SimpleJWT)
- Rich Text: CKEditor 5
- Deployment: Render

## Prerequisites

- Python 3.8+
- PostgreSQL
- Redis
- AWS S3 account
- PayPal Developer account
- Git, pip, virtualenv

 ## Setup Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/Rabeeh-m/Inkspire_backend.git
cd inkspire-backend
```

### 2. Create a Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a .env file in the project root with the following (example in .env file):
```bash
SECRET_KEY=your-django-secret-key
DEBUG=True
DATABASE_URL=your database url
REDIS_URL=redis://localhost:6379
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
AWS_STORAGE_BUCKET_NAME=your-bucket-name
AWS_S3_REGION_NAME=eu-north-1
EMAIL_HOST=smtp.gmail.com
EMAIL_HOST_USER=your-email
EMAIL_HOST_PASSWORD=your-email-password
PAYPAL_CLIENT_ID=your-paypal-client-id
PAYPAL_CLIENT_SECRET=your-paypal-client-secret
PAYPAL_WEBHOOK_ID=your-paypal-webhook-id
```

### 5. Run Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Create Superuser (Optional)
```bash
python manage.py createsuperuser
```

### 7. Start the Development Server
```bash
python manage.py runserver
```

### 8. Running Celery
For asynchronous tasks (e.g., email sending):

Start Redis server.
```bash
Run Celery worker:celery -A backend worker -l info
```
Run Celery Beat for scheduled tasks:celery -A backend beat -l info


## WebSocket Setup
The chat system uses Django Channels with Redis:

Ensure Redis is running locally or via a cloud provider.
Configure REDIS_URL in .env.
Test WebSocket connections at ws://localhost:8000/ws/chat/<room_name>/.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/user/token/` | Obtain JWT access and refresh tokens |
| POST | `/api/user/token/refresh/` | Refresh JWT token |
| POST | `/api/user/register/` | Register a new user and send OTP |
| POST | `/api/user/verify-otp/` | Verify OTP for registration |
| GET, PUT | `/api/user/profile/<user_id>/` | Retrieve or update user profile |
| GET | `/api/user/profiles/` | List all profiles except the user's and ID 2 |
| POST | `/api/user/forgot-password/` | Request password reset OTP |
| POST | `/api/user/verify-forgotpassword-otp/` | Verify password reset OTP |
| POST | `/api/user/reset-password/` | Reset password |
| POST | `/api/user/change-password/` | Change password |
| GET | `/api/post/category/list/` | List all categories |
| GET | `/api/post/category/posts/<category_slug>/` | List posts by category |
| GET | `/api/post/lists/` | List all published posts |
| GET | `/api/post/detail/<slug>/` | Retrieve post details and increment views |
| POST | `/api/post/like-post/` | Like or unlike a post |
| POST | `/api/post/comment-post/` | Add a comment or reply to a post |
| POST | `/api/post/reply-comment/` | Reply to a comment |
| POST | `/api/post/like-comment/` | Like or unlike a comment |
| POST | `/api/post/bookmark-post/` | Bookmark or unbookmark a post |
| GET | `/api/post/popular-post/` | List posts ordered by views |
| GET | `/api/author/dashboard/stats/<user_id>/` | Get author dashboard stats (views, posts, likes, bookmarks) |
| GET | `/api/author/dashboard/post-list/<user_id>/` | List author's posts |
| GET | `/api/author/dashboard/comment-list/<user_id>/` | List comments on author's posts |
| GET | `/api/author/dashboard/noti-list/<user_id>/` | List unseen notifications for author |
| POST | `/api/author/dashboard/noti-mark-seen/` | Mark notification as seen |
| POST | `/api/author/dashboard/reply-comment/` | Reply to a comment (dashboard) |
| POST | `/api/author/dashboard/post-create/` | Create a new post |
| GET, PUT, DELETE | `/api/author/dashboard/post-detail/<user_id>/<post_id>/` | Retrieve, update, or delete a post |
| DELETE | `/api/author/dashboard/post-delete/<post_id>/` | Delete a post |
| POST | `/api/admin/token/` | Obtain JWT token for admin |
| GET | `/api/admin/stats/` | Get admin dashboard stats (users, posts, comments) |
| GET | `/api/admin/users-list/` | List all users |
| DELETE | `/api/admin/user-delete/<user_id>/` | Delete a user |
| POST | `/api/admin/user-block-unblock/<user_id>/` | Block or unblock a user |
| GET | `/api/admin/posts-list/` | List all posts |
| DELETE | `/api/admin/post-delete/<post_id>/` | Delete a post |
| GET, PUT, DELETE | `/api/admin/posts/<post_id>/` | Retrieve, update, or delete a post |
| GET | `/api/admin/subscriptions/` | List all subscriptions |
| POST | `/api/admin/subscriptions/<subscription_id>/` | Update a subscription |
| GET | `/api/admin/subscriptions/<pk>/detail/` | Retrieve subscription details |
| POST | `/api/payment/paypal-success/` | Process PayPal payment and upgrade to premium |
| POST | `/api/profile/<profile_id>/follow/` | Follow or unfollow a profile |
| GET | `/api/test/` | Trigger a test Celery task |
| GET | `/api/get_token/` | Generate Agora RTC token for chat |
| POST | `/api/create_member/` | Create a chat room member |
| GET | `/api/get_member/` | Retrieve chat room member |
| POST | `/api/delete_member/` | Delete chat room member |
| GET | `/api/chat-room/<user1_id>/<user2_id>/` | Get or create a chat room |
| POST | `/api/send-message/` | Send a message with optional file |
| WS | `/ws/chat/<room_name>/` | WebSocket for real-time chat |

## Contributing

- Fork the repository.
- Create a feature branch (git checkout -b feature/your-feature).
- Commit changes (git commit -m "Add your feature").
- Push to the branch (git push origin feature/your-feature).
- Open a pull request.
