"""
API pagination (Phase 4, API-07).

- ?page_size=N (max 500): lists like "all predictions on Saturday" or
  "all leagues" fit in one response. The fixed 20 silently truncated them.
- next/previous links keep the API Gateway stage (/prod). Django sees paths
  without it, so the links pointed at .../api/v1/... and returned 404.
"""
from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 500

    def _with_stage(self, url):
        if not url:
            return url
        ctx = self.request.META.get('apig_wsgi.request_context') or {}
        stage = ctx.get('stage')
        if not stage:
            return url
        scheme, sep, rest = url.partition('://')
        host, slash, path = rest.partition('/')
        if path.startswith(f'{stage}/'):
            return url
        return f'{scheme}{sep}{host}/{stage}/{path}'

    def get_next_link(self):
        return self._with_stage(super().get_next_link())

    def get_previous_link(self):
        return self._with_stage(super().get_previous_link())
