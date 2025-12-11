from datetime import datetime, timedelta

from django.shortcuts import redirect
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView as BaseTokenRefreshView

from .models import User
from .serializers import TokenResponseSerializer, UserSerializer
from .services import GoogleOAuthService


@extend_schema(tags=['인증'])
class GoogleLoginView(APIView):
    """Google OAuth 로그인 시작"""
    permission_classes = [AllowAny]

    @extend_schema(
        summary='Google OAuth 로그인 시작',
        description='Google OAuth2 인증 페이지로 리다이렉트합니다.',
    )
    def get(self, request):
        """Google OAuth 인증 페이지로 리다이렉트"""
        try:
            # Google OAuth 서비스 초기화
            oauth_service = GoogleOAuthService()

            # CSRF 방지를 위한 state 값 생성
            state = oauth_service.generate_state()

            # 세션에 state 저장 (콜백에서 검증)
            request.session['oauth_state'] = state

            # Google OAuth URL 생성
            auth_url = oauth_service.get_authorization_url(state)

            # Google 로그인 페이지로 리다이렉트
            return redirect(auth_url)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(tags=['인증'])
class GoogleCallbackView(APIView):
    """Google OAuth 콜백"""
    permission_classes = [AllowAny]

    @extend_schema(
        summary='Google OAuth 콜백',
        description='Google 로그인 완료 후 콜백을 처리하고 JWT 토큰을 발급합니다.',
        responses={200: TokenResponseSerializer}
    )
    def get(self, request):
        """Google OAuth 콜백 처리 및 JWT 토큰 발급"""
        try:
            # 1. 파라미터 추출
            code = request.GET.get('code')
            state = request.GET.get('state')
            error = request.GET.get('error')

            # 에러 체크
            if error:
                return Response({
                    'status': 'error',
                    'message': f'Google 인증 실패: {error}'
                }, status=status.HTTP_400_BAD_REQUEST)

            if not code:
                return Response({
                    'status': 'error',
                    'message': '인증 코드가 없습니다.'
                }, status=status.HTTP_400_BAD_REQUEST)

            # 2. State 검증 (CSRF 방지)
            saved_state = request.session.get('oauth_state')
            if not saved_state or saved_state != state:
                return Response({
                    'status': 'error',
                    'message': 'Invalid state parameter. CSRF 검증 실패.'
                }, status=status.HTTP_400_BAD_REQUEST)

            # State 사용 후 삭제
            del request.session['oauth_state']

            # 3. Google OAuth 서비스 초기화
            oauth_service = GoogleOAuthService()

            # 4. 인증 코드를 토큰으로 교환
            token_data = oauth_service.exchange_code(code)
            access_token = token_data.get('access_token')
            refresh_token = token_data.get('refresh_token')
            expires_in = token_data.get('expires_in', 3600)

            if not access_token:
                return Response({
                    'status': 'error',
                    'message': 'Access token을 받지 못했습니다.'
                }, status=status.HTTP_400_BAD_REQUEST)

            # 5. 사용자 정보 조회
            user_info = oauth_service.get_user_info(access_token)
            email = user_info.get('email')
            name = user_info.get('name', '')
            picture = user_info.get('picture', '')

            if not email:
                return Response({
                    'status': 'error',
                    'message': '이메일 정보를 받지 못했습니다.'
                }, status=status.HTTP_400_BAD_REQUEST)

            # 6. User 생성 또는 조회
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': email.split('@')[0],  # 이메일 앞부분을 username으로
                    'name': name,
                    'picture': picture,
                }
            )

            # 기존 사용자의 경우 정보 업데이트
            if not created:
                user.name = name
                user.picture = picture

            # 7. Gmail 토큰 암호화 저장
            user.gmail_access_token = access_token
            if refresh_token:  # refresh_token이 있는 경우만 저장
                user.gmail_refresh_token = refresh_token

            # 토큰 만료 시간 저장
            user.gmail_token_expires_at = datetime.now() + timedelta(seconds=expires_in)
            user.save()

            # 8. JWT 토큰 발급
            refresh = RefreshToken.for_user(user)
            jwt_access_token = str(refresh.access_token)
            jwt_refresh_token = str(refresh)

            # 9. FE callback으로 리다이렉트 (토큰 포함)
            import urllib.parse
            fe_callback_url = 'http://localhost:3000/callback'
            params = urllib.parse.urlencode({
                'access_token': jwt_access_token,
                'refresh_token': jwt_refresh_token,
                'expires_in': int(refresh.access_token.lifetime.total_seconds()),
            })
            return redirect(f'{fe_callback_url}?{params}')

        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(tags=['인증'])
class TokenRefreshView(BaseTokenRefreshView):
    """JWT 토큰 갱신"""
    pass


@extend_schema(tags=['인증'])
class LogoutView(APIView):
    """로그아웃"""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='로그아웃',
        description='현재 세션을 로그아웃합니다.',
    )
    def post(self, request):
        return Response({
            'status': 'success',
            'message': '로그아웃 되었습니다.'
        })


@extend_schema(tags=['사용자'])
class UserMeView(APIView):
    """내 정보 조회"""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='내 정보 조회',
        description='현재 로그인한 사용자의 정보를 조회합니다.',
        responses={200: UserSerializer}
    )
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response({
            'status': 'success',
            'data': serializer.data
        })
