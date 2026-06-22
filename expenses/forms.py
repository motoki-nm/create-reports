"""経費アプリのフォーム定義。"""
from django import forms

from .models import Expense, ProcessingSite


class ExpenseForm(forms.ModelForm):
    """経費入力フォーム。処理場はドロップダウン＋自由入力の両対応。"""

    use_preset = forms.ModelChoiceField(
        queryset=ProcessingSite.objects.all(),
        required=False,
        empty_label="--- 登録済みから選ぶ ---",
        label="処理場を選ぶ（任意）",
        widget=forms.Select(attrs={"class": "form-select", "id": "id_use_preset"}),
    )

    class Meta:
        model = Expense
        fields = ["date", "expense_type", "site_name", "amount", "note"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date", "class": "form-input"}),
            "expense_type": forms.Select(attrs={"class": "form-select"}),
            "site_name": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "処理場名または詳細内容を入力", "id": "id_site_name"}
            ),
            "amount": forms.NumberInput(attrs={"class": "form-input", "placeholder": "0"}),
            "note": forms.TextInput(attrs={"class": "form-input", "placeholder": "備考（任意）"}),
        }
        labels = {
            "date": "日付",
            "expense_type": "種別",
            "site_name": "処理場名・内容",
            "amount": "金額（円）",
            "note": "備考",
        }


class ProcessingSiteForm(forms.ModelForm):
    """処理場マスター登録フォーム。"""

    class Meta:
        model = ProcessingSite
        fields = ["name", "note"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-input", "placeholder": "例: 〇〇処理センター"}),
            "note": forms.TextInput(attrs={"class": "form-input", "placeholder": "備考（任意）"}),
        }
        labels = {"name": "処理場名", "note": "備考"}
