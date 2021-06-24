import .ipsplit
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

		prefix = Prefix (
			site = site,
			prefix = prefix_cidr,
			status = status,
			tenant = tenant,
			role = Role.objects.get (name = 'Production'),
			description = "Prefixo" + str(site)
		)
		
		prefix.save ()
		self.log_success ("Created mgmt prefix %s" % prefix)
		
		prefix = Prefix (
			site = site,
			prefix = '10.198.196.0/28',
			status = status,
			tenant = tenant,
			role = Role.objects.get (name = 'Production'),
			description = "Prefixo" + str(site)
		)
		
		prefix.save ()
		self.log_success ("Created mgmt prefix %s" % prefix)

		return prefix	
	
	def run (self, data, commit):
		prefix_name = data['prefix_name']
		site = data['site']
		desc = ('Prefix ' + site)
		tenant = data['site_tenant']
		status = data['status']
		vlan = ''
		childpref = childprefix(preffix_name, desc)

		prefix = self.create_prefix (prefix_name, site, vlan, tenant, status)