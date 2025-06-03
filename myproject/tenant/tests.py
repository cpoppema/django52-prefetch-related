import pytest
from django.test import TestCase
from django.db.models import Prefetch
from django.test.utils import CaptureQueriesContext
from django.db import connection

from myproject.tenant.models import Client, Partner


class MyTenantTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.root = Partner.objects.create(name="root", owner=None, partner_field="123")
        cls.subpartner = Partner.objects.create(name="subpartner", owner=cls.root, partner_field="456")
        cls.client_1 = Client.objects.create(name="client", owner=cls.subpartner, client_field="abc")
        cls.client_2 = Client.objects.create(name="client", owner=cls.subpartner, client_field="def")

    @pytest.mark.xfail(strict=True)
    def test_client_owner(self):
        """
        This test will always fail:

        type(item.owner)=<class 'myproject.tenant.models.Tenant'>
        E
        ======================================================================
        ERROR: test_client_owner (myproject.tenant.tests.MyTenantTestCase.test_client_owner)
        ----------------------------------------------------------------------
        Traceback (most recent call last):
          File "/local/sandbox/django52-prefetch-related/myproject/tenant/tests.py", line 21, in test_client_owner
            self.assertEqual(item.owner.partner_field, "456")
                             ^^^^^^^^^^^^^^^^^^^^^^^^
        AttributeError: 'Tenant' object has no attribute 'partner_field
        """
        qs = Client.objects.all()
        self.assertEqual(qs.count(), 2)

        for item in qs:
            self.assertEqual(item.owner.partner_field, "456")

    def test_client_owner_with_prefetch(self):
        """
        Django 4.2 produces these queries:

        SELECT "tenant_tenant"."id",
               "tenant_tenant"."name",
               "tenant_tenant"."owner_id",
               "tenant_client"."tenant_ptr_id",
               "tenant_client"."client_field"
        FROM "tenant_client"
        INNER JOIN "tenant_tenant" ON ("tenant_client"."tenant_ptr_id" = "tenant_tenant"."id");

        SELECT "tenant_tenant"."id",
               "tenant_tenant"."name",
               "tenant_tenant"."owner_id",
               "tenant_partner"."tenant_ptr_id",
               "tenant_partner"."partner_field"
        FROM "tenant_partner"
        INNER JOIN "tenant_tenant" ON ("tenant_partner"."tenant_ptr_id" = "tenant_tenant"."id") LIMIT 21;

        SELECT "tenant_tenant"."id",
               "tenant_tenant"."name",
               "tenant_tenant"."owner_id",
               "tenant_partner"."tenant_ptr_id",
               "tenant_partner"."partner_field"
        FROM "tenant_partner"
        INNER JOIN "tenant_tenant" ON ("tenant_partner"."tenant_ptr_id" = "tenant_tenant"."id")
        WHERE "tenant_partner"."`tenant_ptr_id" IN (2);

        Note the last WHERE clause: `tenant_ptr_id` IN (2). This fails in
        Django 5.2:

        sqlite3.OperationalError: no such column: tenant_partner.id
        """
        qs = Client.objects.all()
        self.assertEqual(qs.count(), 2)

        with CaptureQueriesContext(connection) as ctx:
            try:
                prefetch_owner_as_partners = Prefetch("owner", Partner.objects.all())
                qs = qs.prefetch_related(prefetch_owner_as_partners)

                for item in qs:
                    print(f"{type(item.owner)=}")
                    self.assertEqual(item.owner.partner_field, "456")
            finally:
                for query in ctx.captured_queries:
                    print(f"{query['sql']=}")
