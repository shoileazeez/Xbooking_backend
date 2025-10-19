from django.urls import path
from workspace.views.workspace import (
    CreateWorkspaceView, ListWorkspacesView, WorkspaceDetailView
)
from workspace.views.branch import (
    CreateBranchView, ListBranchesView, BranchDetailView
)
from workspace.views.space import (
    CreateSpaceView, ListSpacesView, SpaceDetailView
)
from workspace.views.members import (
    AdminRegisterView, AdminProfileView, AdminLoginView, AdminOnboardingView,
    AdminOnboardingStatusView, InviteMemberView,
    ListWorkspaceMembersView, WorkspaceMemberDetailView, SelfSignUpInviteView
)

app_name = 'workspace'

urlpatterns = [
    # Authentication & Profile URLs (Admin registration)
    path('admin/register/', AdminRegisterView.as_view(), name='admin_register'),
    path('admin/login/', AdminLoginView.as_view(), name='admin_login'),
    path('admin/profile/', AdminProfileView.as_view(), name='admin_profile'),
    path('admin/onboarding/', AdminOnboardingView.as_view(), name='admin_onboarding'),
    path('admin/onboarding-status/', AdminOnboardingStatusView.as_view(), name='onboarding_status'),
    
    # Workspace URLs
    path('workspaces/create/', CreateWorkspaceView.as_view(), name='create_workspace'),
    path('workspaces/', ListWorkspacesView.as_view(), name='list_workspaces'),
    path('workspaces/<uuid:workspace_id>/', WorkspaceDetailView.as_view(), name='workspace_detail'),

    # Branch URLs
    path('workspaces/<uuid:workspace_id>/branches/create/', CreateBranchView.as_view(), name='create_branch'),
    path('workspaces/<uuid:workspace_id>/branches/', ListBranchesView.as_view(), name='list_branches'),
    path('branches/<uuid:branch_id>/', BranchDetailView.as_view(), name='branch_detail'),

    # Space URLs
    path('branches/<uuid:branch_id>/spaces/create/', CreateSpaceView.as_view(), name='create_space'),
    path('branches/<uuid:branch_id>/spaces/', ListSpacesView.as_view(), name='list_spaces'),
    path('spaces/<uuid:space_id>/', SpaceDetailView.as_view(), name='space_detail'),
    
    # Workspace Member Management URLs
    path('workspaces/<uuid:workspace_id>/members/invite/', InviteMemberView.as_view(), name='invite_member'),
    path('workspaces/<uuid:workspace_id>/members/', ListWorkspaceMembersView.as_view(), name='list_members'),
    path('workspaces/<uuid:workspace_id>/members/<uuid:member_id>/', WorkspaceMemberDetailView.as_view(), name='member_detail'),
    
    # Self Sign Up with Invite URL (allows any email for members joining)
    path('invite/<uuid:invite_token>/signup/', SelfSignUpInviteView.as_view(), name='self_signup_invite'),
]
