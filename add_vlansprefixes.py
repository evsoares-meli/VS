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
desc = ['VLAN_MGMT','VLAN_IS','VLAN_CLOCK','VLAN_WIFI','VLAN_PRINTERS','VLAN_HANDHELD','VLAN_OPERATOR','VLAN_CAMERAS','VLAN_CORP','PRI_LINK','SEC_LINK']
vlan_range = ['100','10','150','20','40','70','80','30','50','300','310']

#vlan_range = ['10','20','30','40','50','70','80','100','150','300','310']
#vdescription = ['Vlan-IS','Vlan-Aruba','Vlan-Cameras','Vlan-Printers','Vlan-Corp','Vlan-HandHeld','Vlan-Operators','Vlan-Mgmt','Vlan-AccessControl', 'Vlan-Enlace1', 'Vlan-Enlace2']

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
			ch3 = [oct3,oct3,oct3,oct3,oct3,oct3,oct3+1,oct3+2,oct3+2]
			ch4 = [0,16,24,32,64,128,0,0,128]
			nmask = [28,29,29,27,26,25,24,25,25]
			count_m = len(nmask)
			for x in range(0, count_m):
				#printIps(nmask[x], oct1, oct2, ch3[x], ch4[x], desc[x])
				gen_ips_addr = gen_ips_addr + [[('{}.{}.{}.{}/{}'.format(oct1,oct2,ch3[x],ch4[x],nmask[x])),desc[x],vlan[x]]]
		else:
			print ('mascara ainda nao programada ' + a)
	return gen_ips_addr


class ProvisionVlans (Script):
	class Meta:
		name = "Provision Vlans and Prefixes"
		description = "Provision multiples Vlans and Prefixes to a Site"
		field_order = ['site', 'site_no']
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

	def create_prefix (self, prefix_name, site, vlan, tenant, status, c_preffix):
		prefix_cidr = prefix_name
		try:
			#prefix = Prefix.objects.get (prefix = prefix_cidr)
			#self.log_info ("Mgmt prefix %s already present, carrying on." % prefix)
			prefix = VLAN.objects.get (site = site.name, vid = c_preffix[1][2])
			self.log_info ("Mgmt prefix %s already present, carrying on." % prefix)

			return prefix
		except Prefix.DoesNotExist:
			pass
		
		c = len(c_preffix)
		for d in range(1, c):
			prefix = Prefix (
				site = site,
				prefix = c_preffix[d][0],
				#vlan = c_preffix[d][2],
				status = status,
				tenant = tenant,
				role = Role.objects.get (name = 'Production'),
				description = c_preffix[d][1]
			)

			prefix.save ()
			self.log_success ("Created mgmt prefix %s" % prefix)

		return prefix	

#Run	
	def run (self, data, commit): #prefix
		site = data['site']
		prefix_name = data['prefix_name']
		prefix_status = data['prefix_status']
		vlan_name = data['vlan_name']
		vlangroup = data['vlan_group']
		vlan_status = data['vlan_status']
		tenant = data['site_tenant']
		
		#desc = 'Prefix ' + site.name #? atrapalhando o vlan
		vlan = ''
		
		#VLAN CREATE
		j = len(vlan_range)
		for i in range(0, j):
			vlanrange = vlan_range[i]
			desc = desc[i]
			vlan = self.create_mgmt_vlan (site, vlanrange, vlan_name, vlan_status, tenant, vlangroup, desc)
		
	"""
		#PREFIX CREATE
		c_preffix = childprefix(prefix_name, desc)
		self.log_info (c_preffix)
		prefix = self.create_prefix (prefix_name, site, vlan, tenant, prefix_status, c_preffix)
	"""

		




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

	return '\n'.join(output) """