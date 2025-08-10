import string
from django import forms
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser
# from .utils import generate_barcode # Assuming this is not strictly needed for form logic
from .models import CustomUser, SKU, Batch, Barcode, Test, TestQuestion, TestAnswer, TestTemplate # Import TestTemplate

class BatchForm(forms.ModelForm):
    class Meta:
        model = Batch
        fields = '__all__'
        widgets = {
            'sku': forms.Select(attrs={'class': 'w-full p-2 border rounded-lg'}),
            'batch_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full p-2 border rounded-lg'}),
            'quantity': forms.NumberInput(attrs={'class': 'w-full p-2 border rounded-lg'}),
            'device_name': forms.TextInput(attrs={'class': 'w-full p-2 border rounded-lg'}),
            'battery': forms.TextInput(attrs={'class': 'w-full p-2 border rounded-lg'}),
            'capacity': forms.TextInput(attrs={'class': 'w-full p-2 border rounded-lg'}),
            'mppt_cap': forms.TextInput(attrs={'class': 'w-full p-2 border rounded-lg'}),
            'voc_max': forms.TextInput(attrs={'class': 'w-full p-2 border rounded-lg'}),
            'feature_spec': forms.TextInput(attrs={'class': 'w-full p-2 border rounded-lg'}),
            'ef': forms.TextInput(attrs={'class': 'w-full p-2 border rounded-lg'}),
        }

class TestForm(forms.Form):
    sku = forms.ModelChoiceField(
        queryset=SKU.objects.all(),
        widget=forms.Select(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm py-2.5 px-3 text-gray-900 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm'})
    )
    batch = forms.ModelChoiceField(
        queryset=Batch.objects.all(), # Initial queryset, will be filtered in __init__
        widget=forms.Select(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm py-2.5 px-3 text-gray-900 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm'})
    )
    barcode = forms.ModelChoiceField(
        queryset=Barcode.objects.all(), # Initial queryset, will be filtered in __init__
        required=False, # Barcode is optional
        widget=forms.Select(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm py-2.5 px-3 text-gray-900 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm'})
    )
    template = forms.ModelChoiceField(
        queryset=TestTemplate.objects.all(),
        widget=forms.Select(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm py-2.5 px-3 text-gray-900 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm'})
    )
    overall_status = forms.ChoiceField(
        choices=[('pending', 'Pending'), ('passed', 'Passed'), ('failed', 'Failed')],
        widget=forms.Select(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm py-2.5 px-3 text-gray-900 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm'})
    )

    def __init__(self, *args, **kwargs):
        # Pop custom arguments before calling super().__init__
        selected_sku_id = kwargs.pop('selected_sku_id', None)
        selected_batch_id = kwargs.pop('selected_batch_id', None)
        selected_template_id = kwargs.pop('selected_template_id', None)
        
        super().__init__(*args, **kwargs)

        # Filter Batch choices based on selected SKU
        if selected_sku_id:
            self.fields['batch'].queryset = Batch.objects.filter(sku_id=selected_sku_id)
        else:
            self.fields['batch'].queryset = Batch.objects.none()

        # Filter Barcode choices based on selected Batch
        if selected_batch_id:
            self.fields['barcode'].queryset = Barcode.objects.filter(batch_id=selected_batch_id)
        else:
            self.fields['barcode'].queryset = Barcode.objects.none()

        # Dynamically add TestQuestion fields if a Template is selected
        current_template_id = selected_template_id or (self.data.get('template') if 'template' in self.data else None)

        if current_template_id:
            try:
                template_instance = TestTemplate.objects.get(pk=current_template_id)
                questions = TestQuestion.objects.filter(template=template_instance).order_by('id')
                for question in questions:
                    self.fields[f'question_{question.id}_status'] = forms.ChoiceField(
                        choices=[('pass', 'Pass'), ('fail', 'Fail')],
                        label=question.question_text,
                        widget=forms.Select(attrs={
                            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm py-2.5 px-3 text-gray-900 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm'
                        })
                    )
                    self.fields[f'question_{question.id}_remarks'] = forms.CharField(
                        required=False,
                        label='',
                        widget=forms.Textarea(attrs={
                            'rows': 3,
                            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm py-2.5 px-3 text-gray-900 placeholder-gray-400 focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
                            'placeholder': 'Add remarks here...'
                        })
                    )
            except TestTemplate.DoesNotExist:
                pass
        
        # Ensure initial values are set correctly for dropdowns if they exist in initial data
        if self.initial.get('sku'):
            self.fields['batch'].queryset = Batch.objects.filter(sku_id=self.initial['sku'])
        
        if self.initial.get('batch'):
            self.fields['barcode'].queryset = Barcode.objects.filter(batch_id=self.initial['batch'])


# This is the dedicated form for updating overall status on the test_detail page
class TestOverallStatusForm(forms.ModelForm):
    class Meta:
        model = Test
        fields = ['overall_status']
        widgets = {
            'overall_status': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm py-2.5 px-3 text-gray-900 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm'
            }),
        }
