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
		field_order = ['site', 'site_no']
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
	status = ChoiceVar(
		PrefixStatusChoices,
		default=PrefixStatusChoices.STATUS_RESERVED,
		label='Status'
	)
	role = models.ForeignKey(
		to='ipam.Role',
		on_delete=models.SET_NULL,
		related_name='prefixes',
		blank=True,
		null=True,
		help_text='The primary function of this prefix'
	)
	is_pool = models.BooleanField(
		verbose_name='Is a pool',
		default=False,
		help_text='All IP addresses within this prefix are considered usable'
	)


################################################################################             
#                  Methods                                                    #
################################################################################

	def create_preffix (self, site, vlanrange, name, status, sitetenant, vlangroup, desc):
		vlan_id = vlanrange
		try:
			vlan = VLAN.objects.get (site = site, vid = vlan_id)
			self.log_info ("Vlan %s already present, carrying on." % vlan)

			return vlan
		except VLAN.DoesNotExist:
			pass

		i_str = str(vlanrange)
		V = str(i_str.zfill(3))
		vlan = VLAN (
			site = site,
			name = f"{name}{V}",
			vid = vlan_id,
			group = vlangroup,
			status = status,
			tenant = sitetenant,
			role = Role.objects.get (name = 'Production'),
			description = desc
		)
		vlan.save ()
		self.log_success ("Created VLAN %s" % vlan)

		return vlan

	def run (self, data, commit):
		site = data['site']
		name = data['vlan_name']
		sitetenant = data['site_tenant']
		status=data['vlan_status']
		vlangroup = data['vlan_group']
		vlan_range = ['10','20','30','40','50','70','80','100','150','300','310']
		vdescription = ['Vlan-IS','Vlan-Aruba','Vlan-Cameras','Vlan-Printers','Vlan-Corp','Vlan-HandHeld','Vlan-Operators','Vlan-Mgmt','Vlan-AccessControl', 'Vlan-Enlace1', 'Vlan-Enlace2']

		# Set up POP Mgmt VLAN
		for i in range(0, 11):
			vlanrange = vlan_range[i]
			desc = vdescription[i]
			vlan = self.create_preffix (site, vlanrange, name, status, sitetenant, vlangroup, desc)
		output = [
			'name,tenant,status,description'
		]
		for vlan in VLAN.objects.filter(site=vlan.site):

			attrs = [
				vlan.name,
				vlan.status,
				vlan.description,
				vlan.tenant.name
			]
			output.append(','.join(attrs))

		return '\n'.join(output)
#adicionar escolha de role