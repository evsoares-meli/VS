from django.utils.text import slugify

from dcim.choices import *
from dcim.models import Cable, Device, DeviceRole, DeviceType, Platform, Rack, RackRole, Site, Manufacturer
from dcim.models.device_components import FrontPort, Interface, RearPort
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
		default='23',	#change to production id
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
	def create_rack (self, site):
		rname = '{} - CPD'.format(site)
		try:
			rack = Rack.objects.get (name = rname)
			self.log_info ("Rack %s already present, carrying on." % rack)
			return rack
		except Rack.DoesNotExist:
			pass

		rack = Rack (
			role = RackRole.objects.get (name = 'CPD'),
			width = RackWidthChoices.WIDTH_19IN,
			u_height = 42,
			status = RackStatusChoices.STATUS_PLANNED,
			name = rname,
			site = site
		)

		rack.save ()
		self.log_success ("Created rack {}".format (rack))
		return rack


	def setup_firewall(self, site, sitetenant, devicesname, firewallmodel, devicestatus):
			pfx = Prefix.objects.get(site = site, vlan__vid=100) 
			fwip = pfx.prefix[10]
			fw_name = devicesname + 'FWP001-1' 

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
				device_type = firewallmodel,
				status = devicestatus,
				device_role = DeviceRole.objects.get (name = 'Firewall')
				
			)
			fw.save()
			self.log_success('Created device %s' % fw)
			
			#set up mgmt IP
			fw_iface = Interface.objects.get (device = fw, name = 'dmz')
			
			try:
				fw_mgmt_ip = IPAddress.objects.get (address = fwip)
				self.log_info("Ip %s already present, carryng on" % fwip)
			
			except IPAddress.DoesNotExist:
				
				fw_mgmt_ip = IPAddress (address = fwip)
				fw_mgmt_ip.save ()
			
			finally:
				if fw_mgmt_ip.assigned_object is None:
					fw_mgmt_ip.assigned_object = fw_iface
					fw_mgmt_ip.save ()
					fw.primary_ip4 = fw_mgmt_ip
					fw.save()
					self.log_success ("Configured %s on interface %s of %s" % (fw_mgmt_ip, fw_iface, fw))
				else:
					self.log_info ("Ip %s is already in use for another interface" % (fw_mgmt_ip))

				return fw



	def setup_switch(self, site, sitetenant, devicesname, coremodel, devicestatus):
			pfx = Prefix.objects.get(site = site, vlan__vid=100) 
			swip = pfx.prefix[2]
			sw_name = devicesname + 'CRP001-1'

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
				device_role = DeviceRole.objects.get (name = 'Core Switch')
				
			)
			sw.save()
			self.log_success('Created device %s' % sw)

			#set up mgmt IP
			sw_iface = Interface.objects.get (device = sw, name = 'vlan100')
			sw_mgmt_ip = IPAddress (address = swip)
			sw_mgmt_ip.save ()
			sw_mgmt_ip.assigned_object = sw_iface
			sw_mgmt_ip.save ()
			sw.primary_ip4 = sw_mgmt_ip
			sw.save()
			self.log_success ("Configured %s on interface %s of %s" % (sw_mgmt_ip, sw_iface, sw))
			return sw



	def setup_cam(self, site, sitetenant, devicesname, cammodel, devicestatus):
			pfx = Prefix.objects.get(site = site, vlan__vid=100) 
			camip = pfx.prefix[5]
			cam_name = devicesname + 'CCAM001-1'

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
				device_role = DeviceRole.objects.get (name = 'Core Cameras')
				
			)
			cam.save()
			self.log_success('Created device %s' % cam)

			#set up mgmt IP
			cam_iface = Interface.objects.get (device = cam, name = 'vlan100')
			cam_mgmt_ip = IPAddress (address = camip)
			cam_mgmt_ip.save ()
			cam_mgmt_ip.assigned_object = cam_iface
			cam_mgmt_ip.save ()
			cam.primary_ip4 = cam_mgmt_ip
			cam.save()
			self.log_success ("Configured %s on interface %s of %s" % (cam_mgmt_ip, cam_iface, cam))
			return cam



	def setup_iap(self, site, sitetenant, devicesname, iapmodel, devicestatus):
			pfx = Prefix.objects.get(site = site, vlan__vid=20) 
			iapip = pfx.prefix[2]
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
				device_role = DeviceRole.objects.get (name = 'Controller')
				
			)
			iap.save()
			self.log_success('Created device %s' % iap)
			#set up mgmt IP
			iap_iface = Interface.objects.get (device = iap, name = 'vlan20')
			iap_mgmt_ip = IPAddress (address = iapip)
			iap_mgmt_ip.save ()
			iap_mgmt_ip.assigned_object = iap_iface
			iap_mgmt_ip.save ()
			iap.primary_ip4 = iap_mgmt_ip
			iap.save()
			self.log_success ("Configured %s on interface %s of %s" % (iap_mgmt_ip, iap_iface, iap))
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
		rack = self.create_rack(site)
		fw = self.setup_firewall( site, sitetenant, devicesname, firewallmodel, devicestatus)
		sw = self.setup_switch( site, sitetenant, devicesname, coremodel, devicestatus)
		cam = self.setup_cam( site, sitetenant, devicesname, cammodel, devicestatus)
		iap = self.setup_iap( site, sitetenant, devicesname, iapmodel, devicestatus)




# criar devices OK
# 		criar devices secundarios
# inserir ip nos devices OK
# criar rack
#	inserir devices no rack
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