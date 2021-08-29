from typing_extensions import final
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


	def setup_firewall(self, site, rack, sitetenant, devicesname, firewallmodel, devicestatus):
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
				device_role = DeviceRole.objects.get (name = 'Firewall'),
				rack = rack,
				position = rack.u_height - 5,
				face = DeviceFaceChoices.FACE_FRONT
				
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



	def setup_device(self, site, rack, sitetenant, devicesname, devicemodel, devicestatus, manufacturer, primary):
			if primary == 1:
				box = '1'
			else:
				box = '2'
			if manufacturer.name != 'Aruba':
				pfx = Prefix.objects.get(site = site, vlan__vid=100) 
				vlanid = 'vlan100'
				if manufacturer.name == 'Cisco':
					swip = pfx.prefix[2]
					sw_name = devicesname + 'CRP001-' + box
					role = DeviceRole.objects.get (name = 'Core Switch')
					if primary == 1:
						rack_u = rack.u_height - 7
					else:
						rack_u = rack.u_height - 9
				elif manufacturer.name == 'Ruckus':
					swip = pfx.prefix[5]
					sw_name = devicesname + 'CCAM001-' + box
					role = DeviceRole.objects.get (name = 'Core Cameras')
					if primary == 1:
						rack_u = rack.u_height - 11
					else:
						rack_u = rack.u_height - 13
				elif manufacturer.name == 'Fortinet':
					swip = pfx.prefix[10]
					sw_name = devicesname + 'FWP001-' + box
					role = DeviceRole.objects.get (name = 'Firewall')
					if primary == 1:
						rack_u = rack.u_height - 5
			elif manufacturer.name == 'Aruba': 
				pfx = Prefix.objects.get(site = site, vlan__vid=20) 
				vlanid = 'vlan20'
				swip = pfx.prefix[2]
				sw_name = devicesname + 'CTP001'
				role = DeviceRole.objects.get (name = 'Controller')

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
				device_type = devicemodel,
				status = devicestatus,
				device_role = role,
				rack = rack,
				face = DeviceFaceChoices.FACE_FRONT
				
			)
			sw.save()
			self.log_success('Created device %s' % sw)
			if manufacturer.name != 'Aruba' or manufacturer.name == 'Fortinet' and primary != '2' :
				sw.position = rack_u
				sw.save()
			
			#set up mgmt IP
				if primary == 1:
					sw_iface = Interface.objects.get (device = sw, name = vlanid)
					try:
						sw_iface = IPAddress.objects.get (address = swip)
						self.log_info("Ip %s already present, carryng on" % swip)

					except IPAddress.DoesNotExist:
						sw_mgmt_ip = IPAddress (address = swip)
						sw_mgmt_ip.save ()
					finally:
						if sw_mgmt_ip.assigned_object is None: 
							sw_mgmt_ip.assigned_object = sw_iface
							sw_mgmt_ip.save ()
							sw.primary_ip4 = sw_mgmt_ip
							sw.save()
							self.log_success ("Configured %s on interface %s of %s" % (sw_mgmt_ip, sw_iface, sw))
						else:
							self.log_info ("Ip %s is already in use for another interface" % (sw_mgmt_ip))

				return sw



	def setup_cam(self, site, rack, sitetenant, devicesname, cammodel, devicestatus):
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
				device_role = DeviceRole.objects.get (name = 'Core Cameras'),
				rack = rack,
				position = rack.u_height - 9,
				face = DeviceFaceChoices.FACE_FRONT
				
			)
			cam.save()
			self.log_success('Created device %s' % cam)

			#set up mgmt IP
			cam_iface = Interface.objects.get (device = cam, name = 'vlan100')

			try:
				cam_mgmt_ip = IPAddress.objects.get (address = camip)
				self.log_info("Ip %s already present, carryng on" % camip)
			except IPAddress.DoesNotExist:
				cam_mgmt_ip = IPAddress (address = camip)
				cam_mgmt_ip.save ()
			finally:
				if cam_mgmt_ip.assigned_object is None:
					cam_mgmt_ip.assigned_object = cam_iface
					cam_mgmt_ip.save ()
					cam.primary_ip4 = cam_mgmt_ip
					cam.save()
					self.log_success ("Configured %s on interface %s of %s" % (cam_mgmt_ip, cam_iface, cam))
				else:
					self.log_info ("Ip %s is already in use for another interface" % (cam_mgmt_ip))
									
				return cam



	def setup_iap(self, site, rack, sitetenant, devicesname, iapmodel, devicestatus, sw):
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
				device_role = DeviceRole.objects.get (name = 'Controller'),
				rack = rack,
				#position = rack.u_height - 5,
				face = DeviceFaceChoices.FACE_FRONT
				
			)
			iap.save()
			self.log_success('Created device %s' % iap)
			
			#set up mgmt IP
			iap_iface = Interface.objects.get (device = iap, name = 'vlan20')
			
			try:
				iap_mgmt_ip = IPAddress.objects.get (address = iapip)
				self.log_info("Ip %s already present, carryng on" % iapip)

			except IPAddress.DoesNotExist:
				iap_mgmt_ip = IPAddress (address = iapip)
				iap_mgmt_ip.save ()

			finally:
				if iap_mgmt_ip.assigned_object is None:
					iap_mgmt_ip.assigned_object = iap_iface
					iap_mgmt_ip.save ()
					iap.primary_ip4 = iap_mgmt_ip
					iap.save()
					self.log_success ("Configured %s on interface %s of %s" % (iap_mgmt_ip, iap_iface, iap))
				else:
					self.log_info ("Ip %s is already in use for another interface" % (iap_mgmt_ip))
				cable = Cable (
					termination_a = Interface.objects.get (device = sw, name = 'G1/0/3'),
					termination_b = Interface.objects.get (device = iap, name = 'G1/0/1'),
					color = '3f51b5',
					status = CableStatusChoices.STATUS_PLANNED
				)
				cable.save ()


				return iap

	
	
	def run (self, data, commit):
		site = data['site']
		sitetenant = data['site_tenant']
		devicesname = data['devices_name']
		firewallmodel = data['firewall_model']
		coremanufacturer = data['core_manufacturer']
		coremodel = data['core_model']
		cammodel = data['cam_model']
		iapmodel = data['iap_model']
		devicestatus = data['device_status']

		rack = self.create_rack(site)
		fw = self.setup_firewall( site, rack, sitetenant, devicesname, firewallmodel, devicestatus)
		sw = self.setup_device( site, rack, sitetenant, devicesname, coremodel, devicestatus, coremanufacturer, 1)
		sw2 = self.setup_device( site, rack, sitetenant, devicesname, coremodel, devicestatus, coremanufacturer, 2)
		cam = self.setup_cam( site, rack, sitetenant, devicesname, cammodel, devicestatus)
		iap = self.setup_iap( site, rack, sitetenant, devicesname, iapmodel, devicestatus, sw)




# criar devices OK
# 		criar devices secundarios
#			criar chassis
#				cabear devices

# inserir ip nos devices OK

# criar rack ok
#	inserir devices no rack ok

# 
# 
#

# Gerar output para criar arquivos????
# SCRIPT PARA WAN?????
#SCRIPT PARA POR EM ACTIVE!!



#cables - precisa colocar type e label? era  bao kkk
#colors
# UTP - Indigo - 3f51b5