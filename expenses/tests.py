"""経費アプリのテスト。"""
from datetime import date

from django.test import Client, TestCase
from django.urls import reverse

from .models import Expense, ProcessingSite


class ProcessingSiteModelTest(TestCase):
    def test_create_site(self):
        site = ProcessingSite.objects.create(name="〇〇処理センター")
        self.assertEqual(str(site), "〇〇処理センター")

    def test_unique_name(self):
        ProcessingSite.objects.create(name="重複テスト処理場")
        with self.assertRaises(Exception):
            ProcessingSite.objects.create(name="重複テスト処理場")


class ExpenseModelTest(TestCase):
    def test_create_expense(self):
        e = Expense.objects.create(
            date=date.today(),
            expense_type="処理場",
            site_name="△△処理場",
            amount=5000,
        )
        self.assertEqual(e.amount, 5000)
        self.assertIn("△△処理場", str(e))

    def test_default_expense_type(self):
        e = Expense.objects.create(
            date=date.today(), site_name="テスト処理場", amount=1000
        )
        self.assertEqual(e.expense_type, "処理場")


class ExpenseViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        ProcessingSite.objects.create(name="テスト処理場A")
        Expense.objects.create(
            date=date.today(), expense_type="処理場", site_name="テスト処理場A", amount=3000
        )

    def test_list_view(self):
        res = self.client.get(reverse("expenses:list"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "テスト処理場A")

    def test_add_expense(self):
        res = self.client.post(reverse("expenses:add"), {
            "date": date.today().isoformat(),
            "expense_type": "処理場",
            "site_name": "新しい処理場",
            "amount": 8000,
            "note": "",
        })
        self.assertEqual(res.status_code, 302)
        self.assertTrue(Expense.objects.filter(site_name="新しい処理場").exists())

    def test_delete_expense(self):
        e = Expense.objects.first()
        res = self.client.post(reverse("expenses:delete", args=[e.pk]))
        self.assertEqual(res.status_code, 302)
        self.assertFalse(Expense.objects.filter(pk=e.pk).exists())

    def test_date_filter(self):
        res = self.client.get(reverse("expenses:list") + f"?date={date.today().isoformat()}")
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "テスト処理場A")

    def test_invalid_date_filter(self):
        res = self.client.get(reverse("expenses:list") + "?date=invalid")
        self.assertEqual(res.status_code, 200)

    def test_api_sites(self):
        res = self.client.get(reverse("expenses:api_sites"))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("sites", data)
        self.assertEqual(data["sites"][0]["name"], "テスト処理場A")


class ProcessingSiteViewTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_site_list_view(self):
        res = self.client.get(reverse("expenses:sites"))
        self.assertEqual(res.status_code, 200)

    def test_add_site(self):
        res = self.client.post(reverse("expenses:sites"), {"name": "新処理場", "note": ""})
        self.assertEqual(res.status_code, 302)
        self.assertTrue(ProcessingSite.objects.filter(name="新処理場").exists())

    def test_delete_site(self):
        site = ProcessingSite.objects.create(name="削除用処理場")
        res = self.client.post(reverse("expenses:site_delete", args=[site.pk]))
        self.assertEqual(res.status_code, 302)
        self.assertFalse(ProcessingSite.objects.filter(pk=site.pk).exists())
