from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, SKU, Batch, Barcode, TestQuestion, Test, TestAnswer, TestTemplate # Import TestTemplate

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ['username', 'email', 'role', 'is_staff']
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('role',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('role',)}),
    )

class TestQuestionAdmin(admin.ModelAdmin):
    # Display the template and question text
    list_display = ['template', 'question_text', 'created_at']
    # Filter by template
    list_filter = ['template']
    # Search by question text and template name
    search_fields = ['question_text', 'template__name']

    # Removed get_template_name as 'template' itself displays the object's __str__ which is its name.
    # If you need to explicitly show just the name as a separate column, you can re-add it.

class TestAnswerInline(admin.TabularInline):
    model = TestAnswer
    extra = 0

class TestAdmin(admin.ModelAdmin):
    list_display = ['barcode', 'sku', 'batch', 'template_used', 'overall_status', 'test_date', 'user'] # Added template_used
    list_filter = ['overall_status', 'test_date', 'sku', 'batch', 'template_used'] # Added template_used
    search_fields = ['barcode__sequence_number']
    inlines = [TestAnswerInline]

class BatchAdmin(admin.ModelAdmin):
    list_display = ['sku', 'prefix', 'batch_date', 'quantity', 'created_at']
    list_filter = ['sku', 'batch_date']
    search_fields = ['prefix']
    ordering = ['-created_at']

class BarcodeAdmin(admin.ModelAdmin):
    list_display = ['sequence_number', 'batch']
    list_filter = ['batch__sku']
    search_fields = ['sequence_number']

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(SKU)
admin.site.register(Batch, BatchAdmin)
admin.site.register(Barcode, BarcodeAdmin)
admin.site.register(TestTemplate) # Register the new TestTemplate model
admin.site.register(TestQuestion, TestQuestionAdmin)
admin.site.register(Test, TestAdmin)
admin.site.register(TestAnswer)
