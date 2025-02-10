from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views 

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),
    path('register/employer/', views.employer_register, name='employer_register'),
    path('register/employee/', views.employee_register, name='employee_register'),
    path('upload-csv/', views.upload_csv, name='upload_csv'),
    path('add-job/', views.add_job, name='add_job'),
    path('edit-job/<int:job_id>/', views.edit_job, name='edit_job'),
    path('delete-job/<int:job_id>/', views.delete_job, name='delete_job'),
    path('employer-dashboard/', views.employer_dashboard, name='employer_dashboard'),
    path('employee-dashboard/', views.employee_dashboard, name='employee_dashboard'),
    path('view-recommendations/', views.view_recommendations, name='view_recommendations'),
    path('update-profile/', views.update_employee_profile, name='update_profile'),
    path('update-employer-profile/', views.update_employer_profile, name='update_employer_profile'),
    path('view-jobs/', views.view_all_jobs, name='view_jobs'),
    path('job-detail/<int:job_id>/', views.job_detail, name='job_detail'),
    path('apply-job/<int:job_id>/', views.apply_for_job, name='apply_for_job'),
    path('my-applications/', views.view_employee_applications, name='view_employee_applications'),
    path('view-applications/<int:job_id>/', views.view_applications, name='view_applications'),  # Specific job
    path('view-applications/', views.view_all_applications, name='view_all_applications'),  # All applications
    path('delete-application/employer/<int:application_id>/', views.delete_application_employer, name='delete_application_employer'),
    path('delete-application/employee/<int:application_id>/', views.delete_application_employee, name='delete_application_employee'),
    path('view-resume/', views.view_resume, name='view_resume'),
    path('download-resume/<int:application_id>/', views.download_resume, name='download_resume'),
    # Employer compatibility view (you can use this for individual job compatibility details)
    path('compatibility-report/<str:company>/<int:user_id>/', views.view_employer_compatibility, name='view_employer_compatibility'),
    
    # For generating the compatibility report page (filtered results, tables, etc.)
    path('compatibility-report/', views.compatibility_report_view, name='generate_compatibility_report'),
    path('view-compatibility-scores/', views.view_compatibility_scores, name='view_compatibility_scores'),
    path('download-compatibility-scores/', views.download_compatibility_scores, name='download_compatibility_scores'),
    path('compatibility-report/<str:job_name>/', views.view_employee_compatibility_report, name='view_employee_compatibility_report'),


    #openai
    path('employer-compatibility-scores/', views.employer_side_openaiCS, name='employer_side_openaiCS'),
    path(
        'employer-compatibility-report/<str:job>/<str:employee>/',
        views.employer_side_openaiCR,
        name='employer_side_openaiCR'
    ),
    #  path('test-openai-key/', views.test_openai_key, name='test_openai_key'),

    # openai - employee side
    path('employee-ai-compatibility-scores/', views.employee_side_openaiCS, name='employee_side_openaiCS'),
    path('employee-ai-compatibility-report/<str:job>/<str:employee>/', views.employee_side_openaiCR, name='employee_side_openaiCR'),
 
]   

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    