from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenRefreshView as BaseTokenRefreshView
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import User
from .serializers import UserSerializer, TokenResponseSerializer


@extend_schema(tags=['인증'])
class GoogleLoginView(APIView):
    """Google OAuth 로그인 시작"""
    permission_classes = [AllowAny]

    @extend_schema(
        summary='Google OAuth 로그인 시작',
        description='Google OAuth2 인증 페이지로 리다이렉트합니다.',
    )
    def get(self, request):
        # TODO: Google OAuth URL 생성 및 리다이렉트
        return Response({
            'status': 'error',
            'message': 'Not implemented yet'
        }, status=status.HTTP_501_NOT_IMPLEMENTED)


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
        # TODO: OAuth 콜백 처리 및 JWT 발급
        return Response({
            'status': 'error',
            'message': 'Not implemented yet'
        }, status=status.HTTP_501_NOT_IMPLEMENTED)


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
