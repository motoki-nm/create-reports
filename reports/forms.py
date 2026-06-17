"""日報入力・修正フォーム。"""
from django import forms

from .models import WorkRecord


class WorkRecordForm(forms.ModelForm):
    """作業記録の入力・修正フォーム。"""

    class Meta:
        model = WorkRecord
        fields = ["date", "driver_name", "job_type", "customer_name", "place", "amount", "time"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "driver_name": forms.TextInput(attrs={"placeholder": "例：田中"}),
            "customer_name": forms.TextInput(attrs={"placeholder": "例：山田様"}),
            "place": forms.TextInput(attrs={"placeholder": "例：新宿区"}),
            "amount": forms.NumberInput(attrs={"placeholder": "例：15000"}),
            "time": forms.TextInput(attrs={"placeholder": "例：18:00"}),
        }
        labels = {
            "date": "日付",
            "driver_name": "ドライバー名",
            "job_type": "仕事種類",
            "customer_name": "お客様名",
            "place": "地名",
            "amount": "金額（円）",
            "time": "時間",
        }


class FilterForm(forms.Form):
    """一覧画面の絞り込みフォーム。"""

    date = forms.DateField(
        required=False,
        label="日付で絞り込み",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    driver_name = forms.CharField(
        required=False,
        label="ドライバー名で絞り込み",
        widget=forms.TextInput(attrs={"placeholder": "ドライバー名"}),
    )
