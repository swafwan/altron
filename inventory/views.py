# your_app/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.conf import settings # Import settings for MEDIA_URL
from django.views.decorators.cache import never_cache # Import never_cache decorator
from .forms import BatchForm, TestForm, TestOverallStatusForm
from .models import Batch, Barcode, SKU, Test, TestQuestion, TestAnswer, CustomUser, TestTemplate
import logging
from django.core.paginator import Paginator
from django.template.loader import get_template
from django.http import HttpResponse
from django.template.loader import render_to_string

# Import HTML from weasyprint
try:
    from weasyprint import HTML
    # Configure WeasyPrint logging to be more verbose
    logging.getLogger('weasyprint').setLevel(logging.DEBUG) # Set WeasyPrint logger to DEBUG
except ImportError as e:
    import logging
    logging.error("WeasyPrint failed to import: %s", e)
    HTML = None


# Setup logging for debugging
logger = logging.getLogger(__name__)

def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            return render(request, 'inventory/login.html', {'error': 'Invalid credentials'})
    return render(request, 'inventory/login.html')

def user_logout(request):
    logout(request)
    return redirect('login')

@login_required
@never_cache # Added never_cache decorator
def dashboard(request):
    return render(request, 'inventory/dashboard.html')

@login_required
@never_cache # Added never_cache decorator
def barcode_module(request):
    if request.user.role not in ['admin', 'tester']:
        return redirect('dashboard')
    return render(request, 'inventory/barcode_module.html')

@login_required
@never_cache # Added never_cache decorator
def create_batch(request):
    if request.method == 'POST':
        form = BatchForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('batch_list')
    else:
        form = BatchForm()
    return render(request, 'inventory/create_batch.html', {'form': form})

@login_required
@never_cache # Added never_cache decorator
def batch_list(request):
    batches = Batch.objects.all()

    sku_code = request.GET.get('sku_code')
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')

    if sku_code:
        batches = batches.filter(sku__code__icontains=sku_code)

    if from_date:
        batches = batches.filter(batch_date__gte=from_date)

    if to_date:
        batches = batches.filter(batch_date__lte=to_date)

    batches = batches.order_by('-batch_date')

    context = {
        'batches': batches,
        'sku_code': sku_code,
        'from_date': from_date,
        'to_date': to_date,
    }
    return render(request, 'inventory/batch_list.html', context)

@login_required
@never_cache # Added never_cache decorator
def barcode_list(request, batch_id):
    batch = get_object_or_404(Batch, id=batch_id)
    barcode_queryset = Barcode.objects.filter(batch=batch).order_by('sequence_number')

    barcode_number = request.GET.get('barcode_number')

    if barcode_number:
        barcode_queryset = barcode_queryset.filter(sequence_number__icontains=barcode_number)

    paginator = Paginator(barcode_queryset, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'batch': batch,
        'page_obj': page_obj,
        'barcode_number': barcode_number,
    }
    return render(request, 'inventory/barcode_list.html', context)

@login_required
@never_cache # Added never_cache decorator
def print_barcodes(request, batch_id, barcode_id=None):
    if request.user.role not in ['admin', 'tester']:
        return redirect('dashboard')
    batch = get_object_or_404(Batch, id=batch_id)
    if barcode_id:
        barcodes = [get_object_or_404(Barcode, id=barcode_id, batch=batch)]
    else:
        barcodes = Barcode.objects.filter(batch=batch)
    return render(request, 'inventory/print_barcodes.html', {'batch': batch, 'barcodes': barcodes})

@login_required
@never_cache # Added never_cache decorator
def testing_module(request):
    if request.user.role not in ['admin', 'tester']:
        return redirect('dashboard')
    return render(request, 'inventory/testing_module.html')


@login_required
@never_cache # Added never_cache decorator
def new_test(request):
    if request.user.role not in ['admin', 'tester']:
        return redirect('dashboard')

    if request.method == 'POST':
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        selected_sku_id = request.POST.get('sku')
        selected_batch_id = request.POST.get('batch')
        selected_template_id = request.POST.get('template')

        form = TestForm(request.POST,
                        selected_sku_id=selected_sku_id,
                        selected_batch_id=selected_batch_id,
                        selected_template_id=selected_template_id)

        if form.is_valid():
            if is_ajax:
                return render(request, 'inventory/new_test.html', {'form': form})
            else:
                logger.debug("Form cleaned data: %s", form.cleaned_data)
                
                sku_instance = form.cleaned_data['sku']
                batch_instance = form.cleaned_data['batch']
                barcode_instance = form.cleaned_data['barcode']
                template_instance = form.cleaned_data['template']

                test = Test.objects.create(
                    sku=sku_instance,
                    batch=batch_instance,
                    barcode=barcode_instance,
                    user=request.user,
                    template_used=template_instance,
                    overall_status=form.cleaned_data['overall_status']
                )
                
                questions = TestQuestion.objects.filter(template=template_instance)
                for question in questions:
                    status_field_name = f'question_{question.id}_status'
                    remarks_field_name = f'question_{question.id}_remarks'

                    status = form.cleaned_data.get(status_field_name, 'fail')
                    is_passed = (status == 'pass')
                    remarks = form.cleaned_data.get(remarks_field_name, '')

                    logger.debug("Saving answer for question %s: status=%s, remarks=%s",
                                 question.id, status, remarks)
                    TestAnswer.objects.create(
                        test=test,
                        question=question,
                        is_passed=is_passed,
                        remarks=remarks
                    )
                return redirect('test_detail', test_id=test.id)
        else:
            logger.error("Form validation failed: %s", form.errors)
            return render(request, 'inventory/new_test.html', {'form': form})

    else:
        form = TestForm()

    return render(request, 'inventory/new_test.html', {'form': form})

@login_required
@never_cache # Added never_cache decorator
def test_results(request):
    if request.user.role not in ['admin', 'tester']:
        return redirect('dashboard')
    
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    sku = request.GET.get('sku')
    batch = request.GET.get('batch')
    barcode = request.GET.get('barcode')
    template_used = request.GET.get('template_used')

    tests = Test.objects.all()

    if from_date:
        tests = tests.filter(test_date__gte=from_date)
    if to_date:
        tests = tests.filter(test_date__lte=to_date)
    if sku:
        tests = tests.filter(sku__code=sku)
    if batch:
        tests = tests.filter(batch__id=batch)
    if barcode:
        tests = tests.filter(barcode__sequence_number__icontains=barcode)
    if template_used:
        tests = tests.filter(template_used__id=template_used)

    counts = tests.aggregate(
        total=Count('id'),
        passed=Count('id', filter=Q(overall_status='passed')),
        failed=Count('id', filter=Q(overall_status='failed')),
        pending=Count('id', filter=Q(overall_status='pending'))
    )

    context = {
        'tests': tests,
        'counts': counts,
        'skus': SKU.objects.all(),
        'batches': Batch.objects.all(),
        'templates': TestTemplate.objects.all(),
        'from_date': from_date,
        'to_date': to_date,
        'sku': sku,
        'batch': batch,
        'barcode': barcode,
        'template_used': template_used,
    }
    return render(request, 'inventory/test_results.html', context)


@login_required
@never_cache # Added never_cache decorator
def test_detail(request, test_id):
    if request.user.role not in ['admin', 'tester']:
        return redirect('dashboard')
    
    test = get_object_or_404(Test.objects.select_related('sku', 'batch', 'barcode', 'user', 'template_used'), id=test_id)
    
    if request.method == 'POST':
        form = TestOverallStatusForm(request.POST, instance=test)
        if form.is_valid():
            form.save()
            return redirect('test_detail', test_id=test.id)
        else:
            logger.error("Overall status form validation failed: %s", form.errors)
    else:
        form = TestOverallStatusForm(instance=test)
    
    test_answers = test.answers.select_related('question').all() 

    context = {
        'test': test,
        'form': form,
        'test_answers': test_answers,
    }
    return render(request, 'inventory/test_detail.html', context)

@login_required
@never_cache # Added never_cache decorator
def print_test_report(request, test_id):
    # Ensure user has permission
    if request.user.role not in ['admin', 'tester', 'service']:
        return redirect('dashboard')
    
    # Fetch test and related answers
    test = get_object_or_404(Test.objects.select_related('sku', 'batch', 'barcode', 'user', 'template_used'), id=test_id)
    test_answers = test.answers.select_related('question').all()

    # Build absolute URLs for images using settings.MEDIA_URL
    # This is the most reliable way to get absolute URLs for media files
    header_url = request.build_absolute_uri(settings.MEDIA_URL + 'reports/header.png')
    footer_url = request.build_absolute_uri(settings.MEDIA_URL + 'reports/footer.png')

    context = {
        'test': test,
        'test_answers': test_answers,
        'header_url': header_url, # Pass absolute header URL to template
        'footer_url': footer_url, # Pass absolute footer URL to template
    }
    
    # Render the HTML template for the report
    template = get_template('inventory/print_test_report.html')
    html_content = template.render(context)

    # Convert HTML to PDF using WeasyPrint
    if HTML: # Check if WeasyPrint was successfully imported
        # Log the base_url to help debug if images are not found
        base_url = request.build_absolute_uri() # This is the base URL for relative paths in HTML
        logger.info(f"WeasyPrint base_url for PDF: {base_url}")
        
        try: # Added try-except block for more specific error logging
            pdf_file = HTML(string=html_content, base_url=base_url).write_pdf()
            response = HttpResponse(pdf_file, content_type='application/pdf')
            response['Content-Disposition'] = f'filename="test_report_{test.barcode.sequence_number}.pdf"'
            return response
        except Exception as e:
            logger.error(f"WeasyPrint PDF generation failed: {e}", exc_info=True) # Log full traceback
            return HttpResponse(f"Error generating PDF: {e}", status=500)
    else:
        return HttpResponse("Weasyprint is not installed. Please install it to generate PDF reports.", status=500)


@never_cache # Added never_cache decorator
def print_barcodes_pdf(request, batch_id):
    if HTML:
        batch = Batch.objects.get(id=batch_id)
        barcodes = Barcode.objects.filter(batch=batch)
        template = get_template('inventory/print_barcodes_pdf.html')
        html_content = template.render({'barcodes': barcodes, 'batch': batch})

        pdf_file = HTML(string=html_content, base_url=request.build_absolute_uri()).write_pdf()

        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'filename="barcodes_batch_{batch.prefix}.pdf"'
        return response
    else:
        return HttpResponse("Weasyprint is not installed. Please install it to generate PDF reports.", status=500)


import io
import barcode
from barcode.writer import ImageWriter

@never_cache
def barcode_image_view(request, sequence_number):
    buffer = io.BytesIO()
    code128 = barcode.get_barcode_class('code128')

    # Improved writer options for better scanning
    writer = ImageWriter()
    options = {
        'module_width': 0.4,    # Thicker bars for easier scanning
        'module_height': 18.0,  # Taller bars
        'quiet_zone': 6.5,      # Extra whitespace on sides (mm)
        'font_size': 10,        # Text size under barcode
        'text_distance': 2.0,   # Space between bars and text
        'dpi': 300,             # High print quality
        'write_text': False,    # We'll print text in template
        'background': 'white',
        'foreground': 'black'
    }

    code128(sequence_number, writer=writer).write(buffer, options)
    return HttpResponse(buffer.getvalue(), content_type='image/png')
