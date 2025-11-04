"""
Public space serializers with limited fields for unauthenticated users
"""
from rest_framework import serializers
from workspace.models import Space, Branch, Workspace


class PublicWorkspaceSerializer(serializers.ModelSerializer):
    """Minimal workspace info for public space listing"""
    class Meta:
        model = Workspace
        fields = ['id', 'name', 'logo_url']


class PublicBranchSerializer(serializers.ModelSerializer):
    """Minimal branch info for public space listing"""
    workspace = PublicWorkspaceSerializer(read_only=True)

    class Meta:
        model = Branch
        fields = ['id', 'name', 'address', 'workspace']


class SpacePublicListSerializer(serializers.ModelSerializer):
    """
    Space serializer for public listing with limited fields and 
    nested workspace/branch information
    """
    branch = PublicBranchSerializer(read_only=True)
    avg_rating = serializers.FloatField(read_only=True)
    total_reviews = serializers.IntegerField(read_only=True)
    main_photo_url = serializers.SerializerMethodField()

    class Meta:
        model = Space
        fields = [
            'id', 'name', 'description', 'space_type',
            'capacity', 'price_per_hour', 'main_photo_url',
            'branch', 'avg_rating', 'total_reviews'
        ]

    def get_main_photo_url(self, obj):
        """Get the first photo URL or default placeholder"""
        photos = obj.photos.all()
        if photos.exists():
            return photos.first().photo_url
        return None  # Frontend will show placeholder