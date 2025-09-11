from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('traffic_app', '0001_initial'),
    ]

    operations = [
        # Remove legacy model if it exists from 0001
        migrations.DeleteModel(
            name='TrafficData',
        ),

        migrations.CreateModel(
            name='TrafficTask',
            fields=[
                ('task_id', models.UUIDField(primary_key=True, editable=False, serialize=False)),
                ('user_id', models.CharField(max_length=100, db_index=True)),
                ('status', models.CharField(max_length=20, choices=[('processing', 'Processing'), ('completed', 'Completed'), ('failed', 'Failed')])),
                ('video_filename', models.CharField(max_length=255, blank=True)),
                ('output_video_path', models.TextField(blank=True)),
                ('report_file_path', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(null=True, blank=True)),
                ('error_message', models.TextField(blank=True, null=True)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='traffictask',
            index=models.Index(fields=['user_id', '-created_at'], name='traffic_app_user_id_created_idx'),
        ),
        migrations.AddIndex(
            model_name='traffictask',
            index=models.Index(fields=['status', '-created_at'], name='traffic_app_status_created_idx'),
        ),

        migrations.CreateModel(
            name='DirectionStatistics',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_direction', models.IntegerField()),
                ('start_lane', models.IntegerField()),
                ('end_zone', models.IntegerField()),
                ('start_delay', models.FloatField(null=True, help_text='Average start delay in seconds')),
                ('travel_time', models.FloatField(null=True, help_text='Average travel time in seconds')),
                ('vehicle_count', models.IntegerField(default=0, help_text='Number of vehicles')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('task', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='direction_stats', to='traffic_app.traffictask')),
            ],
        ),
        migrations.AddIndex(
            model_name='directionstatistics',
            index=models.Index(fields=['task', 'end_zone'], name='traffic_app_task_id_73f255_idx'),
        ),
        migrations.AddIndex(
            model_name='directionstatistics',
            index=models.Index(fields=['task', 'start_direction', 'start_lane'], name='traffic_app_task_id_de19a0_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='directionstatistics',
            unique_together={('task', 'start_direction', 'start_lane', 'end_zone')},
        ),

        migrations.CreateModel(
            name='VehicleMovement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('vehicle_class', models.CharField(max_length=50, blank=True)),
                ('start_delay', models.FloatField()),
                ('travel_time', models.FloatField()),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('direction_stat', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='movements', to='traffic_app.directionstatistics')),
                ('task', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='vehicle_movements', to='traffic_app.traffictask')),
            ],
            options={
                'ordering': ['-timestamp'],
            },
        ),
    ]


