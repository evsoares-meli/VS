from math import floor
from django.utils.text import slugify
from dcim.choices import *
from dcim.models import Cable, Device, DeviceRole, DeviceType, Platform, Rack, RackRole, Site
#from dcim.models.device_components import FrontPort, Interface, RearPort
from tenancy.models import TenantGroup, Tenant
from ipam.choices import *
from ipam.models import IPAddress, Prefix, Role, VLAN, VLANGroup

from extras.scripts import *

#Functions and Vars
desc = ['VLAN_MGMT','VLAN_CCTV_MON','VLAN_WIFI','VLAN_PRINTERS','VLAN_HANDHELD','VLAN_OPERATOR','VLAN_CLOCK','VLAN_IS','VLAN_ACCESSCONTROL','VLAN_CORP','VLAN_CAMERAS','PRIMARY_LINK','SECONDARY_LINK']
vlan_range = ['1','100','280','20','40','70','80','160','10','150','50','30','300','310']

def validaOct(num):
	''' adjusts to /22 range '''
	b = int(num)/4
	numf = 4 * floor(b)
	return numf

def validaIp(addr, ipaddr):
	''' checks if a number is between 0 to 255 '''
	addr = int(addr)
	if addr > 255:
		print('invalid ip address {}'.format(ipaddr))
		quit()
	else:
		return addr

def childprefix (a, gen_ips_addr):
	gen_ips_addr = [[a, gen_ips_addr]]

	if '/' in a:
		ips = a.split('/')
		ip = ips[0]
		mask = ips[1]
		if '.' in ip:
			ipr = ip.split('.')

		if mask == '22':
			oct1 = int(ipr[0])
			oct1 = validaIp(oct1, a)
			oct2 = int(ipr[1])
			oct2 = validaIp(oct2, a)
			oct3 = int(ipr[2])
			oct3 = validaOct(oct3)
			oct3 = validaIp(oct3, a)
			ch3 = [oct3,oct3,oct3,oct3,oct3,oct3,oct3+1,oct3+1,oct3+1,oct3+1,oct3+2]
			ch4 = [0,16,32,64,128,0,0,8,16,128,0]
			nmask = [28,28,27,26,25,24,29,29,28,25,25]
			count_m = len(nmask)
			for x in range(0, count_m):
				gen_ips_addr = gen_ips_addr + [[('{}.{}.{}.{}/{}'.format(oct1,oct2,ch3[x],ch4[x],nmask[x])),desc[x]]]
		else:
			print ('Netmask not acceptable yet ' + a)
	return gen_ips_addr


class ProvisionVlans (Script):
	class Meta:
		name = "Provision Vlans and Prefixes"
		description = "Provision multiples Vlans and Prefixes to a Site"
		field_order = ['site', 'prefix_name','prefix_status','vlan_name','vlan_group','vlan_status','tenant_group','site_tenant']
		#commit_default = False
	
	#Front End Form
	site = ObjectVar (description = "Site to be deployed", queryset = Site.objects.all ())

	prefix_name = StringVar ( label="Prefix", description="i.e: 10.0.0.0/22" )

	prefix_status = ChoiceVar ( PrefixStatusChoices, default=PrefixStatusChoices.STATUS_RESERVED, label='Prefix Status' )

	vlan_name = StringVar ( label="Vlan Name", description="Vlan name whitout number i.e: VXXYYZZ" )

	vlan_group = ObjectVar ( required=False, model= VLANGroup, query_params={'Site_id': '$site'} )
	
	vlan_status = ChoiceVar ( VLANStatusChoices, default=VLANStatusChoices.STATUS_RESERVED, label='Vlan Status' )
	
	tenant_group = ObjectVar( model=TenantGroup )

	site_tenant = ObjectVar( label='Tenant', model=Tenant, display_field='model', query_params={'group_id': '$tenant_group'} )

	#Methods

	def create_mgmt_vlan (self, site, vlanrange, vlan_name, status, tenant, vlangroup, desc):
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
				name = f"{vlan_name}{V}",
				vid = vlan_id,
				group = vlangroup,
				status = status,
				tenant = tenant,
				role = Role.objects.get (name = 'Production'),
				description = desc
			)
			vlan.save ()
			self.log_success ("Created VLAN %s" % vlan)

			return vlan

	def create_prefix (self, prefix_name, site, vlan, tenant, status, prefix_range, desc_prefix):
		try:
			prefix = Prefix.objects.get (prefix = prefix_range)
			self.log_info ("Prefix %s already present, carrying on." % prefix)

			return prefix
		except Prefix.DoesNotExist:
			pass
			if vlan != '1':
				prefix = Prefix (
					site = site,
					prefix = prefix_range,
					vlan = vlan,
					status = status,
					tenant = tenant,
					role = Role.objects.get (name = 'Production'),
					description = desc_prefix
				)
			else:
				prefix = Prefix (
					site = site,
					prefix = prefix_range,
					status = status,
					tenant = tenant,
					role = Role.objects.get (name = 'Production'),
					description = desc_prefix
				)
			prefix.save ()
			self.log_success ("Created Prefix %s" % prefix)

		return prefix	

	#Run	
	def run (self, data, commit): #prefix
		site = data['site']
		prefix_name = data['prefix_name']
		prefix_status = data['prefix_status']
		prefix_desc = 'Prefix ' + site.name
		vlan_name = data['vlan_name']
		vlangroup = data['vlan_group']
		vlan_status = data['vlan_status']
		tenant = data['site_tenant']

		c_prefix = childprefix(prefix_name, prefix_desc)
		c = len(c_prefix)
		vlan = '1'
		#Creates parent prefix
		prefix = self.create_prefix (prefix_name, site, vlan, tenant, prefix_status, c_prefix[0][0], c_prefix[0][1])
		
		#Creates prefix with vlan
		for d in range(1, c):
		
			#VLAN CREATE
			vlanrange = vlan_range[d]
			desc_vlan = c_prefix[d][1]
			vlan = self.create_mgmt_vlan (site, vlanrange, vlan_name, vlan_status, tenant, vlangroup, desc_vlan)
		
			#PREFIX CREATE
			prefix_range = c_prefix[d][0]
			desc_prefix = c_prefix[d][1]
			prefix = self.create_prefix (prefix_name, site, vlan, tenant, prefix_status, prefix_range, desc_prefix)

		#Creates Wan Vlans
		vlan = self.create_mgmt_vlan (site, vlan_range[12], vlan_name, vlan_status, tenant, vlangroup, desc[11])
		vlan = self.create_mgmt_vlan (site, vlan_range[13], vlan_name, vlan_status, tenant, vlangroup, desc[12])
	
		







		#SAIDA
	""" output = [
		'vlan_name,tenant,status,description'
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
	use to log	self.log_info (c_prefix)
	"""