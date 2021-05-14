from django.utils.text import slugify

from dcim.choices import DeviceStatusChoices, SiteStatusChoices
from tenancy.models import Tenant, TenantGroup
from dcim.models import Device, DeviceRole, DeviceType, Manufacturer, Site
from extras.scripts import *


class NewBranchScript(Script):

    class Meta:
        name = "Add devices to a site"
        description = "Provision a devices to a site"
        field_order = ['device_name', 'device_count', 'Device_role', 'manufacturer', 'device_model','site_name','tenant_group', 'stie_tenant']

    device_name = StringVar(
       # label="teste",
        description="Device name whitout number"
    )
    device_count = IntegerVar(
        description="Number of devices to create"
    )
    manufacturer = ObjectVar(
        model=Manufacturer,
        required=False
    )
    device_model = ObjectVar(
        label="Device Type",
        model=DeviceType,
        display_field='model',
        query_params={
            'manufacturer_id': '$manufacturer'
        }
    )
    Device_role = ObjectVar(
        model=DeviceRole,
        required=False
    )
    device_status = ChoiceVar(
        DeviceStatusChoices, default=DeviceStatusChoices.STATUS_PLANNED,label='Status'
    )
    site_name = ObjectVar(
        label='Site',
        model=Site
    )
    tenant_group = ObjectVar(
        model=TenantGroup
    )
    site_tenant = ObjectVar(
        label='Tenant',
        model=Tenant,
        display_field='model',
        query_params={
            'group_id': '$tenant_group'
        }
    )


    def run(self, data, commit):


        for i in range(1, data['device_count'] + 1):
            switch = Device(
                device_type=data['device_model'],
                name=f"{data['device_name']}{i}",
                site=data['site_name'],
                tenant=data['site_tenant'],
                status=data['device_status'],
                device_role=data['Device_role']
            )
            switch.save()
            self.log_success(f"Created New Device: {switch}")

        # Generate a CSV table of new devices
        output = [
            'name,make,modeli,tenant'
        ]
        for switch in Device.objects.filter(site=switch.site):
            attrs = [
                switch.name,
                switch.device_type.manufacturer.name,
                switch.device_type.model,
                switch.tenant.name
            ]
            output.append(','.join(attrs))

        return '\n'.join(output)
