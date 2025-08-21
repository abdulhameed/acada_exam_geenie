from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0005_expertquestiondataset_enhancedcoursecontent_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='expertquestion',
            name='is_missing_source',
            field=models.BooleanField(default=False, help_text='Indicates if this question is missing source material'),
        ),
        migrations.AddField(
            model_name='expertquestion',
            name='source_recovery_attempted',
            field=models.BooleanField(default=False, help_text='Indicates if source recovery has been attempted for this question'),
        ),
        migrations.AddField(
            model_name='expertquestion',
            name='source_recovery_date',
            field=models.DateTimeField(blank=True, null=True, help_text='When source material was last recovered or attempted'),
        ),
    ]