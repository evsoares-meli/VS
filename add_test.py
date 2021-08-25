from django.utils.text import slugify

from dcim.choices import *
from dcim.models import Cable, Device, DeviceRole, DeviceType, Platform, Rack, RackRole, Site, Manufacturer
#from dcim.models.device_components import FrontPort, Interface, RearPort
from tenancy.models import TenantGroup, Tenant
from ipam.choices import *
from ipam.models import IPAddress, Prefix, Role, VLAN, VLANGroup

from extras.scripts import *
##TESTE##

class ProvisionMDevices (Script):
	class Meta:
		name = "Provision Devices"
		description = "Provision multiples Devices to a Site"
		field_order = ['site']
		#commit_default = False

	# Drop down for sites
	site = ObjectVar (
		description = "Site to be deployed",
		queryset = Site.objects.all ()
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
	devices_name = StringVar( 
		description="Devices name prefix whitout numbers, ej UYSCMV"
	)
	firewall_manufacturer = ObjectVar(
		model=Manufacturer,
		required=False 
	)

	firewall_model = ObjectVar(
		description="Device model",
		model=DeviceType, 
		display_field='model', 
		query_params={'manufacturer_id': '$firewall_manufacturer'} 
	)
	core_manufacturer = ObjectVar(
		model=Manufacturer,
		required=False 
	)

	core_model = ObjectVar(
		description="Device model",
		model=DeviceType, 
		display_field='model', 
		query_params={'manufacturer_id': '$core_manufacturer'} 
	)
	cam_manufacturer = ObjectVar(
		model=Manufacturer,
		required=False 
	)

	cam_model = ObjectVar(
		description="Device model",
		model=DeviceType, 
		display_field='model', 
		query_params={'manufacturer_id': '$cam_manufacturer'} 
	)
	iap_manufacturer = ObjectVar(
		model=Manufacturer,
		default='Aruba',
		required=False 
	)

	iap_model = ObjectVar(
		description="Device model",
		model=DeviceType, 
		display_field='model', 
		query_params={'manufacturer_id': '$iap_manufacturer'} 
	)
	device_status = ChoiceVar (
		DeviceStatusChoices, 
		default=DeviceStatusChoices.STATUS_PLANNED, 
		label='Device Status'
	)
	'''devices_role = ObjectVar(
		model=DeviceRole,
		required=False 
	)''' #fazer fixa
################################################################################             
#                  Methods                                                    #
################################################################################

	def create_mgmt_vlan (self, site, sitetenant):
		try:
			vlan = VLAN.objects.get (site = site, vid = 100)
				
			pfx = Prefix.objects.get(site = site, vlan__vid=100) 
			#pfx.prefix[2] #sw 


			self.log_info ("Vlan %s already present, carrying on." % pfx.prefix[2])


			return vlan
		except VLAN.DoesNotExist:
			pass
		
		self.log_success ("Created VLAN %s" % vlan)

		return vlan

	def run (self, data, commit):
		site = data['site']
		sitetenant = data['site_tenant']

		# Set up POP Mgmt VLAN
		#for i in range(0, 11):
		#	vlanrange = vlan_range[i]
		#	desc = vdescription[i]
		vlan = self.create_mgmt_vlan (site, sitetenant)
		






'''addr = addr.split('/')
ip = addr[0]
mask = addr[1]
octet = ip.split('.')
ipsw = '{}.{}.{}.2/{}'.format(octet[0],octet[1],octet[2],mask)
'''