from django.db import models

class docTable(models.Model):
    label=models.CharField(max_length=100,default='')#file name
    doc_file=models.FileField(upload_to='doc_templates/')
    doc_fields=models.JSONField(default=dict)

    def __str__(self) -> str:
        return str(self.id)
    
class newPdfUpload(models.Model):
    name=models.TextField()
    doc_file=models.FileField(upload_to='filled_pdfs/')

    def __str__(self) -> str:
        return str(self.id)
    

