"""
커스텀 페이지네이션
"""
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class CustomPagination(PageNumberPagination):
    """
    커스텀 페이지네이션
    - 페이지 크기: 20 (기본값)
    - 최대 페이지 크기: 100
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            'mails': data,
            'pagination': {
                'page': self.page.number,
                'page_size': self.page_size,
                'total_count': self.page.paginator.count,
                'total_pages': self.page.paginator.num_pages,
                'has_next': self.page.has_next(),
                'has_prev': self.page.has_previous(),
            }
        })
