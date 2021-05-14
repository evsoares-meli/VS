from django.utils.text import slugify

from dcim.choices import *
from dcim.models import Cable, Device, DeviceRole, DeviceType, Platform, Rack, RackRole, Site
#from dcim.models.device_components import FrontPort, Interface, RearPort
from tenancy.models import TenantGroup, Tenant
from ipam.choices import *
from ipam.models import IPAddress, Prefix, Role, VLAN, VLANGroup

from extras.scripts import *
##TESTE##

class ProvisionBackbonePOP (Script):
	class Meta:
		name = "Provision Backbone POP"
		description = "Provision a new backbone POP"
		field_order = ['site', 'site_no']
		commit_default = False

	# Drop down for sites
	site = ObjectVar (
		description = "Site to be deployed",
		queryset = Site.objects.all ()
	)

	# Site No.
	site_no = IntegerVar (description = "Site number (for Mgmt VLAN + prefix)")

	vlan_name = StringVar(
	   # label="teste",
	   description="Vlan name whitout number"
	   )
	vlan_group = ObjectVar(
        required=False,
		model= VLANGroup,
		query_params={
			'Site_id': '$site'
		}
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
################################################################################
#                                 Methods                                      #
################################################################################

	def run(self, data, commit):

		site = data['site']
		site_no = data['site_no']
		name = data['vlan_name']
		sitetenant = data['site_tenant']
		vlangroup = data['vlan_group']
		# Set up POP Mgmt VLAN
		for i in range(1,10):
			vlan_id = i
			try:
				vlan = VLAN.objects.get (site = site, vid = vlan_id)
				self.log_info ("Mgmt vlan %s already present, carrying on." % vlan)

				return vlan
			except VLAN.DoesNotExist:
				pass

			i_str = str(i)
			V = str(i_str.zfill(3))
			vlan = VLAN (
				site = site,
				name = f"{name}{V}",
				vid = vlan_id,
				tenant = sitetenant,
				vgroup = vlangroup
			)
		vlan.save ()
		self.log_success ("Created mgmt VLAN %s" % vlan)

		
################################################################################
#                                 Falta Inserir GP e Dsc                       #
################################################################################

