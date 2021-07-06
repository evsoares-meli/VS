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

    site_name = ObjectVar( label='Site', model=Site )

    tenant_group = ObjectVar( model=TenantGroup, )

    site_tenant = ObjectVar( label='Tenant', model=Tenant, display_field='model', query_params={'group_id': '$tenant_group'} )
    
    device_name = StringVar( description="Device name whitout number" )

    device_count = IntegerVar( description="Number of devices to create" )

    device_status = ChoiceVar( DeviceStatusChoices, default=DeviceStatusChoices.STATUS_PLANNED )

    manufacturer = ObjectVar( model=Manufacturer, required=False )
    
    device_model = ObjectVar( description="Device model", model=DeviceType, display_field='model', query_params={'manufacturer_id': '$manufacturer'} )
    
    Device_role = ObjectVar( model=DeviceRole, required=False )

    def run(self, data, commit):


        for i in range(1, data['device_count'] + 1):
            i_str = str(i)
            I = i_str.zfill(3)
            device = Device(
                device_type=data['device_model'],
                name=f"{data['device_name']}{I}",
                site=data['site_name'],
                tenant=data['site_tenant'],
                status=data['device_status'],
                device_role=data['Device_role']
            )
            device.save()
            self.log_success(f"Created new Device: {device}")

        # Generate a CSV table of new devices
        output = [
            'name,make,model'
        ]
        for device in Device.objects.filter(site=device.site):
            attrs = [
                device.name,
                device.device_type.manufacturer.name,
                device.device_type.model
            ]
            output.append(','.join(attrs))

        return '\n'.join(output)