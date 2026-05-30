from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views

app_name = "api"

urlpatterns = [
    # Auth (JWT)
    path("auth/token/", TokenObtainPairView.as_view(), name="token_obtain"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # Profile
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("profile/spouse/", views.SpouseView.as_view(), name="spouse"),

    # Investments — Accounts
    path("investments/accounts/", views.InvestmentAccountListCreateView.as_view(), name="account_list"),
    path("investments/accounts/<int:pk>/", views.InvestmentAccountDetailView.as_view(), name="account_detail"),

    # Investments — Income Sources
    path("investments/income/", views.IncomeSourceListCreateView.as_view(), name="income_list"),
    path("investments/income/<int:pk>/", views.IncomeSourceDetailView.as_view(), name="income_detail"),

    # Simulations
    path("simulations/scenarios/", views.ScenarioListCreateView.as_view(), name="scenario_list"),
    path("simulations/scenarios/<int:pk>/", views.ScenarioDetailView.as_view(), name="scenario_detail"),
    path("simulations/scenarios/<int:pk>/run/", views.run_scenario, name="scenario_run"),
    path("simulations/results/<int:pk>/", views.SimulationResultDetailView.as_view(), name="result_detail"),
    path("simulations/results/<int:pk>/status/", views.result_status, name="result_status"),
]
