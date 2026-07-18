"""Reports API views."""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from core.permissions import IsOrgAdmin
from .services import personal_summary, org_summary


class PersonalReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(personal_summary(request.user))


class OrgReportView(APIView):
    permission_classes = [IsAuthenticated, IsOrgAdmin]

    def get(self, request):
        return Response(org_summary(request.user.organization))
