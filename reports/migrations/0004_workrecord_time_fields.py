"""
WorkRecord の time CharField を start_time / end_time TimeField に置き換える。
既存データは "09:00 ~ 17:00" 形式でパースして移行する。
driver_name フィールドに db_index を追加してクエリを高速化する。
"""
from datetime import time as time_type

from django.db import migrations, models


def migrate_time_to_fields(apps, schema_editor):
    WorkRecord = apps.get_model("reports", "WorkRecord")
    for record in WorkRecord.objects.exclude(time=""):
        if "~" not in record.time:
            continue
        parts = [p.strip() for p in record.time.split("~")]
        try:
            h, m = parts[0].split(":")
            record.start_time = time_type(int(h), int(m))
        except (ValueError, IndexError):
            continue
        if len(parts) > 1:
            try:
                h, m = parts[1].split(":")
                record.end_time = time_type(int(h), int(m))
            except (ValueError, IndexError):
                pass
        record.save(update_fields=["start_time", "end_time"])


def reverse_migrate(apps, schema_editor):
    WorkRecord = apps.get_model("reports", "WorkRecord")
    for record in WorkRecord.objects.all():
        if record.start_time and record.end_time:
            record.time = (
                f"{record.start_time.strftime('%H:%M')} ~ {record.end_time.strftime('%H:%M')}"
            )
        elif record.start_time:
            record.time = record.start_time.strftime("%H:%M")
        else:
            continue
        record.save(update_fields=["time"])


class Migration(migrations.Migration):

    dependencies = [
        ("reports", "0003_driverdailylog"),
    ]

    operations = [
        # 1. 新フィールドを追加
        migrations.AddField(
            model_name="workrecord",
            name="start_time",
            field=models.TimeField(blank=True, null=True, verbose_name="開始時刻"),
        ),
        migrations.AddField(
            model_name="workrecord",
            name="end_time",
            field=models.TimeField(blank=True, null=True, verbose_name="終了時刻"),
        ),
        # 2. 既存データを移行
        migrations.RunPython(migrate_time_to_fields, reverse_code=reverse_migrate),
        # 3. 旧フィールドを削除
        migrations.RemoveField(
            model_name="workrecord",
            name="time",
        ),
        # 4. driver_name に db_index を追加（WorkRecord / DriverDailyLog）
        migrations.AlterField(
            model_name="workrecord",
            name="driver_name",
            field=models.CharField(
                db_index=True, max_length=50, verbose_name="ドライバー名"
            ),
        ),
        migrations.AlterField(
            model_name="driverdailylog",
            name="driver_name",
            field=models.CharField(
                db_index=True, max_length=50, verbose_name="ドライバー名"
            ),
        ),
    ]
