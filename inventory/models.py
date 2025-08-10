import string
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser
# from .utils import generate_barcode # Assuming this is not strictly needed for model definition

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('tester', 'Tester'),
        ('service', 'Service'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='tester')

    def __str__(self):
        return f"{self.username} ({self.role})"

class SKU(models.Model):
    code = models.CharField(max_length=10, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.code

def increment_suffix(suffix: str) -> str:
    """
    Increment suffix like:
    A001 ... A999 -> B001 ... Z999 -> AA001 ... ZZ999 -> AAA001 ...
    """
    letters = suffix[:-3]
    number = int(suffix[-3:])

    if number < 999:
        return f"{letters}{str(number + 1).zfill(3)}"

    # Number reached 999, increment letters part
    letters_list = list(letters)
    i = len(letters_list) - 1
    while i >= 0:
        if letters_list[i] == 'Z':
            letters_list[i] = 'A'
            i -= 1
        else:
            letters_list[i] = chr(ord(letters_list[i]) + 1)
            break
    else:
        # All letters were 'Z', add another 'A' at the front
        letters_list.insert(0, 'A')

    new_letters = "".join(letters_list)
    return f"{new_letters}001"

class Batch(models.Model):
    sku = models.ForeignKey(SKU, on_delete=models.CASCADE)
    prefix = models.CharField(max_length=20)  # keep this field, auto-set to sku.code
    batch_date = models.DateField(default=timezone.now)
    quantity = models.PositiveIntegerField()
    device_name = models.CharField(max_length=100, blank=True)
    battery = models.CharField(max_length=100, blank=True)
    capacity = models.CharField(max_length=50, blank=True)
    mppt_cap = models.CharField(max_length=50, blank=True, null=True)
    voc_max = models.CharField(max_length=50, blank=True, null=True)
    feature_spec = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    ef = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return f"{self.prefix} - {self.batch_date}"

    def save(self, *args, **kwargs):
        # Auto-set prefix from SKU code before saving
        self.prefix = self.sku.code

        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new:
            last_barcode = (
                Barcode.objects
                .filter(sequence_number__startswith=self.prefix)
                .order_by('-sequence_number')
                .first()
            )
            if last_barcode:
                last_suffix = last_barcode.sequence_number.replace(self.prefix, '')
                if len(last_suffix) < 4:
                    last_suffix = None
            else:
                last_suffix = None

            next_suffix = "A001" if not last_suffix else increment_suffix(last_suffix)

            barcodes = []
            for _ in range(self.quantity):
                full_code = f"{self.prefix}{next_suffix}"
                barcodes.append(
                    Barcode(
                        batch=self,
                        sku=self.sku,
                        sequence_number=full_code,
                        #barcode_image=generate_barcode(full_code)
                    )
                )
                next_suffix = increment_suffix(next_suffix)

            Barcode.objects.bulk_create(barcodes)


class Barcode(models.Model):
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE)
    sku = models.ForeignKey(SKU, on_delete=models.CASCADE)
    sequence_number = models.CharField(max_length=30, unique=True)
    #barcode_image = models.ImageField(upload_to='barcodes/', blank=True, null=True)

    def __str__(self):
        return self.sequence_number

class TestTemplate(models.Model): # NEW MODEL
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class TestQuestion(models.Model):
    # Changed from batch to template
    template = models.ForeignKey(TestTemplate, on_delete=models.CASCADE, related_name='questions',null=True, blank=True)
    question_text = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        # Updated string representation to reflect the change
        return f"Template: {self.template.name} - {self.question_text}"

class Test(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('passed', 'Passed'),
        ('failed', 'Failed'),
    )
    sku = models.ForeignKey(SKU, on_delete=models.CASCADE)
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE)
    barcode = models.ForeignKey(Barcode, on_delete=models.CASCADE)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    template_used = models.ForeignKey(TestTemplate, on_delete=models.SET_NULL, null=True, blank=True) # NEW FIELD to record which template was used
    overall_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    test_date = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Test {self.id} - {self.barcode.sequence_number} ({self.overall_status})"

class TestAnswer(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(TestQuestion, on_delete=models.CASCADE)
    is_passed = models.BooleanField(default=False)
    remarks = models.TextField(blank=True)

    def __str__(self):
        return f"{self.test} - {self.question} ({'Passed' if self.is_passed else 'Failed'})"
