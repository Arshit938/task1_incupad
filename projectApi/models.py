from django.db import models

class docTable(models.Model):
    id=models.IntegerField(primary_key=True)
    label=models.CharField(max_length=100,default='')#file name
    doc_file=models.FileField(upload_to='doc_templates/')

    def __str__(self) -> str:
        return str(self.id)
    
class formLabels(models.Model):
    id=models.IntegerField(primary_key=True)
    doc_fields=models.JSONField(default=dict)

    def __str__(self) -> str:
        return str(self.id)
