from math import floor
from django.utils.text import slugify
from dcim.choices import *
from dcim.models import Cable, Device, DeviceRole, DeviceType, Platform, Rack, RackRole, Site
#from dcim.models.device_components import FrontPort, Interface, RearPort
from tenancy.models import TenantGroup, Tenant
from ipam.choices import *
from ipam.models import IPAddress, Prefix, Role, VLAN, VLANGroup

from extras.scripts import *

def validaOct(num):
	'''
	altera octeto para o octeto de rede /22
	'''
	b = int(num)/4
	numf = 4 * floor(b)
	return numf

def validaIp(addr, ipaddr):
	'''
	valida se ip esta dentro da faixa 0 a 255
	'''
	addr = int(addr)
	if addr > 255:
		print('invalid ip address {}'.format(ipaddr))
		quit()
	else:
		return addr

def childprefix (a, gen_ips_addr):
	gen_ips_addr = [[a, gen_ips_addr]]
	desc = ['VLAN_MGMT','VLAN_IS','VLAN_CLOCK','VLAN_WIFI','VLAN_PRINTERS','VLAN_HANDHELD','VLAN_OPERATOR','VLAN_CAMERAS','VLAN_CORP']
	vlan = [100,10,150,20,40,70,80,30,50]

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
			nmask = [28,28,28,27,26,25,24,25,25]
			count_m = len(nmask)
			for x in range(0, count_m):
				#printIps(nmask[x], oct1, oct2, ch3[x], ch4[x], desc[x])
				gen_ips_addr = gen_ips_addr + [[('{}.{}.{}.{}/{}'.format(oct1,oct2,ch3[x],ch4[x],nmask[x])),desc[x],vlan[x]]]
		else:
			print ('mascara ainda nao programada ' + a)
	return gen_ips_addr

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

	def create_prefix (self, prefix_name, site, vlan, tenant, status, c_preffix):
		prefix_cidr = prefix_name
		try:
			prefix = Prefix.objects.get (prefix = prefix_cidr)
			self.log_info ("Mgmt prefix %s already present, carrying on." % prefix)

			return prefix
		except Prefix.DoesNotExist:
			pass
		
		c = len(c_preffix)
		for d in range(0, c):
			prefix = Prefix (
				site = site,
				prefix = c_preffix[d][0],
				status = status,
				tenant = tenant,
				role = Role.objects.get (name = 'Production'),
				description = c_preffix[d][1]
			)
		
			prefix.save ()
			self.log_success ("Created mgmt prefix %s" % prefix)

		return prefix	
	
	def run (self, data, commit):
		prefix_name = data['prefix_name']
		site_name = data['site']
		desc = 'Prefix ' + site_name.name
		tenant = data['site_tenant']
		status = data['status']
		vlan = ''
		c_preffix = childprefix(prefix_name, desc)
		self.log_info (c_preffix)
		prefix = self.create_prefix (prefix_name, site_name, vlan, tenant, status, c_preffix)








#  X.Y.Z.0   / 28   -   mgmt 	#  X.Y.Z.16  / 28   -   is			#  X.Y.Z.24  / 28   -   REP 
#  X.Y.Z.32  / 27   -   Aruba 	#  X.Y.Z.64  / 26   -   Printers 	#  X.Y.Z.128 / 25   -   HH
#  X.Y.Z+1.0 / 24   -   OP 		#  X.Y.Z+2.0 /	25   -   Cam  		#  X.Y.Z+2.128 / 25   -   corp

