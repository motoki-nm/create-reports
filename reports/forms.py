"""日報入力・修正フォーム。"""
from django import forms

from .models import Driver, WorkRecord


class WorkRecordForm(forms.ModelForm):
    """作業記録の入力・修正フォーム。"""

    driver_name = forms.ChoiceField(
        choices=[],
        label="ドライバー名",
        widget=forms.Select(),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get("instance")
        drivers = list(Driver.objects.values_list("name", flat=True))

        # 編集時に削除済みドライバー名が既存レコードにある場合も選択肢に残す
        if instance and instance.driver_name and instance.driver_name not in drivers:
            drivers = sorted(drivers + [instance.driver_name])

        self.fields["driver_name"].choices = [("", "--- 選択してください ---")] + [
            (name, name) for name in drivers
        ]

    class Meta:
        model = WorkRecord
        fields = ["date", "driver_name", "job_type", "customer_name", "place", "amount", "time"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "customer_name": forms.TextInput(attrs={"placeholder": "例：山田様"}),
            "place": forms.TextInput(attrs={"placeholder": "例：新宿区"}),
            "amount": forms.NumberInput(attrs={"placeholder": "例：15000", "min": "0"}),
            "time": forms.HiddenInput(),
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
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        input_formats=["%Y-%m-%d"],
    )
    driver_name = forms.ChoiceField(
        required=False,
        label="ドライバー名で絞り込み",
        choices=[],
        widget=forms.Select(),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        drivers = list(Driver.objects.values_list("name", flat=True))
        self.fields["driver_name"].choices = [("", "すべてのドライバー")] + [
            (name, name) for name in drivers
        ]


class DriverForm(forms.ModelForm):
    """ドライバー登録フォーム。"""

    class Meta:
        model = Driver
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "例：田中"}),
        }
        labels = {
            "name": "ドライバー名",
        }
