"""経費アプリのモデル定義。"""
import logging

from django.db import models

logger = logging.getLogger(__name__)


class ProcessingSite(models.Model):
    """処理場マスター。よく使う処理場を登録しておく。"""

    name = models.CharField(max_length=100, unique=True, verbose_name="処理場名")
    note = models.CharField(max_length=200, blank=True, verbose_name="備考")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="登録日時")

    class Meta:
        verbose_name = "処理場"
        verbose_name_plural = "処理場"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Expense(models.Model):
    """1日の経費記録。処理場費・その他費用を登録する。"""

    class ExpenseType(models.TextChoices):
        PROCESSING   = "処理場",   "処理場"
        OUTSOURCING  = "外注費",   "外注費"
        TRANSPORT    = "交通費",   "交通費"
        POSTAGE      = "切手・郵便", "切手・郵便"
        SUPPLIES     = "消耗品費", "消耗品費"
        OTHER        = "その他",   "その他（自由入力）"

    date = models.DateField(verbose_name="日付")
    expense_type = models.CharField(
        max_length=10,
        choices=ExpenseType.choices,
        default=ExpenseType.PROCESSING,
        verbose_name="種別",
    )
    site_name = models.CharField(max_length=100, verbose_name="処理場名・内容")
    amount = models.PositiveIntegerField(default=0, verbose_name="金額")
    note = models.CharField(max_length=200, blank=True, verbose_name="備考")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="登録日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    class Meta:
        verbose_name = "経費"
        verbose_name_plural = "経費"
        ordering = ["-date", "expense_type"]

    def __str__(self) -> str:
        return f"{self.date} {self.expense_type} {self.site_name} ¥{self.amount:,}"
