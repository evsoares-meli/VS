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
		model=TenantGroup,
		default='25'	#change to production id
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
		default='22',	#change to production id
		required=False 
	)

	firewall_model = ObjectVar(
		model=DeviceType, 
		display_field='model', 
		query_params={'manufacturer_id': '$firewall_manufacturer'} 
	)
	core_manufacturer = ObjectVar(
		model=Manufacturer,
		default='2',	#change to production id
		required=False 
	)

	core_model = ObjectVar(
		model=DeviceType, 
		display_field='model', 
		query_params={'manufacturer_id': '$core_manufacturer'} 
	)
	cam_manufacturer = ObjectVar(
		model=Manufacturer,
		default='2',	#change to production id
		required=False 
	)

	cam_model = ObjectVar(
		model=DeviceType, 
		display_field='model', 
		query_params={'manufacturer_id': '$cam_manufacturer'} 
	)
	iap_manufacturer = ObjectVar(
		model=Manufacturer,
		default='10',	#change to production id
		required=False 
	)

	iap_model = ObjectVar(
		model=DeviceType, 
		display_field='model', 
		query_params={'manufacturer_id': '$iap_manufacturer'} 
	)
	device_status = ChoiceVar (
		DeviceStatusChoices, 
		default=DeviceStatusChoices.STATUS_PLANNED, 
		label='Device Status'
	)
	'''devices_role = ObjectVar(		model=DeviceRole,		required=False 	) '''   #FAZER FIXO !!!!!!


################################################################################             
#                  Methods                                                    #
################################################################################

	def setup_firewall(self, site, sitetenant, devicesname, firewallmodel, devicestatus):
			pfx = Prefix.objects.get(site = site, vlan__vid=100) 
			fw_name = devicesname + 'FWP00' 

			try: 
				fw = Device.objects.get (name = fw_name)
				self.log_info ("Device %s already present, carryng on." % fw_name)

				return fw
			except Device.DoesNotExist:
				pass
			
			fw = Device(
				site = site,
				tenant = sitetenant,
				name = fw_name,
				device_type = fwmodel,
				status = devicestatus,
				device_role = 'firewall'
				
			)
			fw.save()
			self.log_success('Created device %s' % fw)
			return fw



	def setup_switch(self, site, sitetenant, devicesname, coremodel, devicestatus):
			pfx = Prefix.objects.get(site = site, vlan__vid=100) 
			sw_name = devicesname + 'CRP00'

			try: 
				sw = Device.objects.get (name = sw_name)
				self.log_info ("Device %s already present, carryng on." % sw_name)

				return sw
			except Device.DoesNotExist:
				pass
			
			sw = Device(
				site = site,
				tenant = sitetenant,
				name = sw_name,
				device_type = coremodel,
				status = devicestatus,
				device_role = 'core-switch'
				
			)
			sw.save()
			self.log_success('Created device %s' % sw)
			return sw



	def setup_cam(self, site, sitetenant, devicesname, cammodel, devicestatus):
			pfx = Prefix.objects.get(site = site, vlan__vid=100) 
			cam_name = devicesname + 'CCAM00'

			try: 
				cam = Device.objects.get (name = cam_name)
				self.log_info ("Device %s already present, carryng on." % cam_name)

				return cam
			except Device.DoesNotExist:
				pass 
			
			cam = Device(
				site = site,
				tenant = sitetenant,
				name = cam_name,
				device_type = cammodel,
				status = devicestatus,
				device_role = 'core-switch'
				
			)
			cam.save()
			self.log_success('Created device %s' % cam)
			return cam



	def setup_iap(self, site, sitetenant, devicesname, iapmodel, devicestatus):
			pfx = Prefix.objects.get(site = site, vlan__vid=20) 
			iap_name = devicesname + 'CTP001'

			try: 
				iap = Device.objects.get (name = iap_name)
				self.log_info ("Device %s already present, carryng on." % iap_name)

				return iap
			except Device.DoesNotExist:
				pass
			
			iap = Device(
				site = site,
				tenant = sitetenant,
				name = iap_name,
				device_type = iapmodel,
				status = devicestatus,
				device_role = 'controller'
				
			)
			iap.save()
			self.log_success('Created device %s' % iap)
			return iap

	
	
	def run (self, data, commit):
		site = data['site']
		sitetenant = data['site_tenant']
		devicesname = data['devices_name']
		firewallmodel = data['firewall_model']
		coremodel = data['core_model']
		cammodel = data['cam_model']
		iapmodel = data['iap_model']
		devicestatus = data['device_status']
		# Set up POP Mgmt VLAN
		#for i in range(0, 11):
		#	vlanrange = vlan_range[i]
		#	desc = vdescription[i]
		fw = self.setup_firewall( site, sitetenant, devicesname, firewallmodel, devicestatus)
		sw = self.setup_switch( site, sitetenant, devicesname, coremodel, devicestatus)
		cam = self.setup_cam( site, sitetenant, devicesname, cammodel, devicestatus)
		iap = self.setup_iap( site, sitetenant, devicesname, iapmodel, devicestatus)




# criar devices
# inserir ip nos devices
# cabear devices
# criar chassis
#

# Gerar output para criar arquivos????
# SCRIPT PARA WAN?????


'''addr = addr.split('/')
ip = addr[0]
mask = addr[1]
octet = ip.split('.')
ipsw = '{}.{}.{}.2/{}'.format(octet[0],octet[1],octet[2],mask)
'''