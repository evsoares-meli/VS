from django.utils.text import slugify

from dcim.choices import *
from dcim.models import Cable, Device, DeviceRole, DeviceType, Platform, Rack, RackRole, Site
#from dcim.models.device_components import FrontPort, Interface, RearPort
from tenancy.models import TenantGroup, Tenant
from ipam.choices import *
from ipam.models import IPAddress, Prefix, Role, VLAN, VLANGroup

from extras.scripts import *

class ProvisionPrefixes (Script):
	class Meta:
		name = "Provision Prefixes"
		description = "Provision multiples Prefixes to a Site"
		field_order = ['site']
		#commit_default = False

	prefix_name = StringVar(
		label="Prefixo",
		description="Vlan name whitout number"
	)
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
	status = ChoiceVar(
		PrefixStatusChoices,
		default=PrefixStatusChoices.STATUS_RESERVED,
		label='Status'
	)



################################################################################			 
#				  Methods													#
################################################################################

	def create_prefix (self, prefix_name, site, vlan, tenant, status):
		prefix_cidr = prefix_name
		try:
			prefix = Prefix.objects.get (prefix = prefix_cidr)
			self.log_info ("Mgmt prefix %s already present, carrying on." % prefix)

			return prefix
		except Prefix.DoesNotExist:
			pass

		desc1 = "Prefixo "
		desc2 = str(site)
		prefix = Prefix (
			site = site,
			prefix = prefix_cidr,
			#vlan = vlan,
            status = status,
			role = Role.objects.get (name = 'Production'),
            description = desc1 + desc2
		)

		prefix.save ()
		self.log_success ("Created mgmt prefix %s" % prefix)

		return prefix
	
	
	def run (self, data, commit):
		prefix_name = data['prefix_name']
		site = data['site']
		tenant = data['site_tenant']
		status = data['status']
		vlan = ''

		# site = data['site']
		# name = data['vlan_name']
		# sitetenant = data['site_tenant']
		# status=data['vlan_status']
		# vlangroup = data['vlan_group']
		# vlan_range = ['10','20','30','40','50','70','80','100','150','300','310']
		# vdescription = ['Vlan-IS','Vlan-Aruba','Vlan-Cameras','Vlan-Printers','Vlan-Corp','Vlan-HandHeld','Vlan-Operators','Vlan-Mgmt','Vlan-AccessControl', 'Vlan-Enlace1', 'Vlan-Enlace2']

		# Set up POP Mgmt VLAN
		#for i in range(0, 11):
		#	vlanrange = vlan_range[i]
		#	desc = vdescription[i]
		prefix = self.create_prefix (prefix_name, site, vlan, tenant, status)