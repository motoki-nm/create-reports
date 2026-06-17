"""日報データのモデル定義。"""
from django.db import models


class WorkRecord(models.Model):
    """1件の作業記録。ドライバーが1仕事ごとに登録する。"""

    class JobType(models.TextChoices):
        DISPOSAL = "処分", "処分"
        PURCHASE = "買取", "買取"
        ESTIMATE = "見積", "見積"
        OTHER = "その他", "その他"

    date = models.DateField(verbose_name="日付")
    driver_name = models.CharField(max_length=50, verbose_name="ドライバー名")
    job_type = models.CharField(
        max_length=10,
        choices=JobType.choices,
        verbose_name="仕事種類",
    )
    customer_name = models.CharField(max_length=100, verbose_name="お客様名")
    place = models.CharField(max_length=100, blank=True, verbose_name="地名")
    amount = models.PositiveIntegerField(default=0, verbose_name="金額")
    time = models.CharField(max_length=20, blank=True, verbose_name="時間")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="登録日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    class Meta:
        verbose_name = "作業記録"
        verbose_name_plural = "作業記録"
        ordering = ["-date", "driver_name"]

    def __str__(self) -> str:
        return f"{self.date} {self.driver_name} {self.job_type} {self.customer_name}"
