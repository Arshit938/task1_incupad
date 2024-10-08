# Generated by Django 3.2 on 2024-08-29 14:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projectApi', '0002_alter_doctable_doc_file'),
    ]

    operations = [
        migrations.CreateModel(
            name='newPdfUpload',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.TextField()),
                ('doc_file', models.FileField(upload_to='filled_pdfs/')),
            ],
        ),
        migrations.AddField(
            model_name='doctable',
            name='doc_fields',
            field=models.JSONField(default=dict),
        ),
    ]
